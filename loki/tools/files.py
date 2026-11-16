"""File-system tools. All paths go through `safe_path` (the sandbox)."""
from __future__ import annotations

from ..safety import safe_path
from .registry import tool

MAX_READ_CHARS = 4000


@tool()
def list_directory(path: str) -> str:
    """List files and folders inside a directory.

    Args:
        path: Folder path, e.g. "~/Documents".
    """
    p = safe_path(path)
    if not p.is_dir():
        return f"Not a directory: {p}"
    entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    lines = [f"{'[dir] ' if e.is_dir() else '      '}{e.name}" for e in entries if not e.name.startswith(".")]
    return "\n".join(lines[:200]) or "(empty folder)"


@tool()
def read_file(path: str) -> str:
    """Read a text file and return its contents (truncated if long).

    Args:
        path: File path, e.g. "~/Documents/todo.txt".
    """
    p = safe_path(path)
    if not p.is_file():
        return f"File not found: {p}"
    text = p.read_text(errors="replace")
    if len(text) > MAX_READ_CHARS:
        return text[:MAX_READ_CHARS] + f"\n...[truncated, {len(text)} chars total]"
    return text


@tool()
def search_files(folder: str, pattern: str) -> str:
    """Find files whose name matches a pattern, searching subfolders too.

    Args:
        folder: Folder to search in, e.g. "~/Documents".
        pattern: Glob pattern, e.g. "*.pdf" or "*resume*".
    """
    root = safe_path(folder)
    matches = [str(m) for m in root.rglob(pattern) if not any(part.startswith(".") for part in m.parts)]
    if not matches:
        return f"No files matching '{pattern}' in {root}"
    extra = f"\n...and {len(matches) - 50} more" if len(matches) > 50 else ""
    return "\n".join(matches[:50]) + extra


@tool(dangerous=True)
def write_file(path: str, content: str) -> str:
    """Create or overwrite a text file. Requires user confirmation.

    Args:
        path: File path to write, e.g. "~/Documents/notes.txt".
        content: The full text to write.
    """
    p = safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Wrote {len(content)} characters to {p}"
