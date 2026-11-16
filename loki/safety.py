"""Safety layer.

Two ideas keep LOKI from doing damage:
1. Sandboxing  - file tools can only reach folders listed in settings.allowed_dirs.
2. Human-in-the-loop - tools marked `dangerous=True` need a yes from you first
   (the agent calls a `confirm` callback before running them).
"""
from __future__ import annotations

from pathlib import Path

from .config import settings


class PermissionDenied(Exception):
    """Raised when a tool tries to leave the sandbox."""


def safe_path(path: str) -> Path:
    """Resolve `path` and make sure it lives inside an allowed folder.

    `.resolve()` collapses `..` and follows symlinks, so tricks like
    `~/Documents/../.ssh/id_rsa` are caught.
    """
    p = Path(path).expanduser().resolve()
    for root in settings.allowed_dirs:
        if p == root or root in p.parents:
            return p
    allowed = ", ".join(str(r) for r in settings.allowed_dirs)
    raise PermissionDenied(f"{p} is outside the allowed folders ({allowed})")
