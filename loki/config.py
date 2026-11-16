"""Central settings for LOKI.

Everything is read from environment variables so you can change behaviour
without editing code (12-factor style). Copy `.env.example` to `.env` and
`export $(cat .env | xargs)` or set them in your shell.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _paths(env_var: str, default: list[str]) -> list[Path]:
    raw = os.getenv(env_var)
    items = raw.split(":") if raw else default
    return [Path(p).expanduser().resolve() for p in items if p]


@dataclass
class Settings:
    # The "brain": any Ollama model that supports tool calling.
    model: str = field(default_factory=lambda: os.getenv("LOKI_MODEL", "qwen2.5:7b"))
    ollama_host: str = field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434"))

    # Sandbox: LOKI may only touch files inside these folders.
    allowed_dirs: list[Path] = field(
        default_factory=lambda: _paths("LOKI_ALLOWED_DIRS", ["~/Documents", "~/Desktop", "~/Downloads"])
    )

    # Voice
    voice: str = field(default_factory=lambda: os.getenv("LOKI_VOICE", "Daniel"))  # macOS `say -v ?` lists voices
    whisper_model: str = field(default_factory=lambda: os.getenv("LOKI_WHISPER_MODEL", "base.en"))

    # Agent loop guard: max think->act cycles per request.
    max_steps: int = field(default_factory=lambda: int(os.getenv("LOKI_MAX_STEPS", "8")))


settings = Settings()
