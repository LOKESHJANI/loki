"""Text-to-speech. On macOS we use the built-in `say` command: free, offline, no setup."""
from __future__ import annotations

import platform
import shutil
import subprocess


class Speaker:
    def __init__(self, voice: str = "Daniel"):
        self.voice = voice
        self.enabled = platform.system() == "Darwin" and shutil.which("say") is not None

    def say(self, text: str) -> None:
        if not text:
            return
        if self.enabled:
            subprocess.run(["say", "-v", self.voice, text], check=False)
