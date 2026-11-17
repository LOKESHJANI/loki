import numpy as np

from loki.voice.listen import resample


def test_resample_48k_to_16k_keeps_duration_and_shape():
    rate = 48_000
    t = np.arange(rate) / rate  # 1 second
    tone = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    out = resample(tone, rate)
    assert out.dtype == np.float32
    assert out.size == 16_000
    assert abs(float(np.max(out)) - 1.0) < 0.05


def test_resample_noop_at_16k():
    audio = np.zeros(1600, dtype=np.float32)
    assert resample(audio, 16_000).size == 1600
