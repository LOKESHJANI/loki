"""Speech-to-text.

1. Record from the microphone until you stop talking (simple energy-based
   voice activity detection: RMS loudness above a threshold = speech).
2. Transcribe locally with Whisper (via faster-whisper). Runs offline.

macOS notes:
- Mics usually run at 44.1/48 kHz. We record at the device's native rate
  and resample to the 16 kHz Whisper expects, instead of forcing 16 kHz
  on the hardware.
- CoreAudio sometimes fails to reopen the mic right after `say` used the
  audio device (PortAudio error -9986). We reset PortAudio and retry.
"""
from __future__ import annotations

import time

import numpy as np

WHISPER_RATE = 16_000  # Whisper expects 16 kHz mono audio


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

    def _open_stream(self, sd, rate: int):
        stream = sd.InputStream(samplerate=rate, channels=1, dtype="float32")
        stream.start()
        return stream

    def _start_stream(self, rate: int, attempts: int = 3):
        import sounddevice as sd

        for attempt in range(attempts):
            try:
                return self._open_stream(sd, rate)
            except sd.PortAudioError:
                if attempt == attempts - 1:
                    raise
                # Reset PortAudio so it re-reads the audio devices, then retry.
                sd._terminate()
                time.sleep(0.4)
                sd._initialize()

    def record(self, silence_secs: float = 1.2, max_secs: float = 20.0) -> np.ndarray:
        import sounddevice as sd

        rate = int(sd.query_devices(kind="input")["default_samplerate"])
        block = 0.1  # seconds per chunk
        chunks, silent, heard = [], 0.0, False
        stream = self._start_stream(rate)
        try:
            for _ in range(int(max_secs / block)):
                data, _ = stream.read(int(rate * block))
                chunks.append(data.copy())
                loud = float(np.sqrt(np.mean(data**2))) > self.threshold
                if loud:
                    heard, silent = True, 0.0
                elif heard:
                    silent += block
                if heard and silent >= silence_secs:
                    break
        finally:
            stream.stop()
            stream.close()
        return resample(np.concatenate(chunks).flatten(), rate)

    def listen(self) -> str:
        audio = self.record()
        segments, _ = self.model.transcribe(audio, language="en", vad_filter=True)
        return " ".join(s.text for s in segments).strip()
