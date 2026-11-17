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


def test_record_collects_until_silence_without_reopening_mic():
    from loki.voice.listen import Listener

    lis = Listener.__new__(Listener)  # skip loading Whisper
    import queue

    lis._queue, lis._recording, lis.threshold, lis.rate = queue.Queue(), False, 0.01, 16_000
    lis._stream = object()  # pretend the mic is already open
    loud, quiet = np.full(1600, 0.5, np.float32), np.zeros(1600, np.float32)
    import threading
    import time

    def mic():  # feed audio like a real mic would, once recording starts
        while not lis._recording:
            time.sleep(0.001)
        for block in [loud] * 5 + [quiet] * 20:
            lis._queue.put(block)

    threading.Thread(target=mic, daemon=True).start()
    audio = lis.record(silence_secs=1.2)
    assert audio.size == 1600 * (5 + 12)  # stops after 1.2 s of quiet
    assert lis._recording is False
