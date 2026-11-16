"""Speech-to-text.

1. Record from the microphone until you stop talking (simple energy-based
   voice activity detection: RMS loudness above a threshold = speech).
2. Transcribe locally with Whisper (via faster-whisper). Runs offline on CPU.
"""
from __future__ import annotations

import numpy as np

SAMPLE_RATE = 16_000  # Whisper expects 16 kHz mono audio


class Listener:
    def __init__(self, model_size: str = "base.en", threshold: float = 0.01):
        from faster_whisper import WhisperModel

        # int8 quantization keeps it fast on a laptop CPU
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.threshold = threshold

    def record(self, silence_secs: float = 1.2, max_secs: float = 20.0) -> np.ndarray:
        import sounddevice as sd

        block = 0.1  # seconds per chunk
        chunks, silent, heard = [], 0.0, False
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
            for _ in range(int(max_secs / block)):
                data, _ = stream.read(int(SAMPLE_RATE * block))
                chunks.append(data.copy())
                loud = float(np.sqrt(np.mean(data**2))) > self.threshold
                if loud:
                    heard, silent = True, 0.0
                elif heard:
                    silent += block
                if heard and silent >= silence_secs:
                    break
        return np.concatenate(chunks).flatten()

    def listen(self) -> str:
        audio = self.record()
        segments, _ = self.model.transcribe(audio, language="en", vad_filter=True)
        return " ".join(s.text for s in segments).strip()
