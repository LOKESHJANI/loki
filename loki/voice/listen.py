"""Speech-to-text.

1. Record from the microphone until you stop talking (simple energy-based
   voice activity detection: RMS loudness above a threshold = speech).
2. Transcribe locally with Whisper (via faster-whisper). Runs offline.

macOS notes:
- The mic is opened ONCE and kept open for the whole session. A callback
  receives audio continuously; we only keep it while `record()` is
  listening. Reopening the mic between turns fails on some Macs
  (CoreAudio "Unspecified Audio Hardware Error", PortAudio -9986),
  especially with Bluetooth headsets after `say` has used them.
- Mics usually run at 44.1/48 kHz. We record at the device's native rate
  and resample to the 16 kHz Whisper expects.
"""
from __future__ import annotations

import queue

import numpy as np

WHISPER_RATE = 16_000  # Whisper expects 16 kHz mono audio
BLOCK_SECS = 0.1


def resample(audio: np.ndarray, from_rate: int, to_rate: int = WHISPER_RATE) -> np.ndarray:
    """Linear-interpolation resampling. Good enough for speech recognition."""
    if from_rate == to_rate or audio.size == 0:
        return audio.astype(np.float32)
    duration = audio.size / from_rate
    n_out = int(round(duration * to_rate))
    x_old = np.linspace(0.0, duration, num=audio.size, endpoint=False)
    x_new = np.linspace(0.0, duration, num=n_out, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


class Listener:
    def __init__(self, model_size: str = "base.en", device: str = "cpu", threshold: float = 0.01):
        from faster_whisper import WhisperModel

        # int8 quantization keeps it fast on a laptop CPU
        self.model = WhisperModel(model_size, device=device, compute_type="int8")
        self.threshold = threshold
        self._queue: queue.Queue[np.ndarray] = queue.Queue()
        self._recording = False
        self._stream = None
        self.rate = WHISPER_RATE

    def _callback(self, indata, frames, time_info, status):  # runs on an audio thread
        if self._recording:
            self._queue.put(indata[:, 0].copy())

    def _ensure_stream(self) -> None:
        if self._stream is not None:
            return
        import sounddevice as sd

        self.rate = int(sd.query_devices(kind="input")["default_samplerate"])
        self._stream = sd.InputStream(
            samplerate=self.rate,
            channels=1,
            dtype="float32",
            blocksize=int(self.rate * BLOCK_SECS),
            callback=self._callback,
        )
        self._stream.start()

    def record(self, silence_secs: float = 1.2, max_secs: float = 20.0) -> np.ndarray:
        self._ensure_stream()
        while not self._queue.empty():  # drop anything left from before
            self._queue.get_nowait()

        chunks, silent, heard, elapsed = [], 0.0, False, 0.0
        self._recording = True
        try:
            while elapsed < max_secs:
                try:
                    data = self._queue.get(timeout=2.0)
                except queue.Empty:
                    raise RuntimeError("no audio from the microphone")
                chunks.append(data)
                secs = data.size / self.rate
                elapsed += secs
                if float(np.sqrt(np.mean(data**2))) > self.threshold:
                    heard, silent = True, 0.0
                elif heard:
                    silent += secs
                if heard and silent >= silence_secs:
                    break
        finally:
            self._recording = False
        return resample(np.concatenate(chunks), self.rate)

    def listen(self) -> str:
        audio = self.record()
        segments, _ = self.model.transcribe(audio, language="en", vad_filter=True)
        return " ".join(s.text for s in segments).strip()

    def close(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
