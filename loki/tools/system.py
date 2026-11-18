"""Mac / system tools."""
from __future__ import annotations

import platform
import subprocess
import webbrowser
from datetime import datetime

from .registry import tool


@tool()
def get_datetime() -> str:
    """Get the current local date and time."""
    return datetime.now().strftime("%A, %B %d %Y, %I:%M %p")


@tool()
def open_application(name: str) -> str:
    """Open a macOS application by name.

    Args:
        name: App name, e.g. "Safari", "Notes", "Visual Studio Code".
    """
    if platform.system() != "Darwin":
        return "open_application only works on macOS."
    result = subprocess.run(["open", "-a", name], capture_output=True, text=True)
    return f"Opened {name}" if result.returncode == 0 else f"Could not open {name}: {result.stderr.strip()}"


@tool()
def open_url(url: str, browser: str = "") -> str:
    """Open a web page in a browser.

    Args:
        url: Full URL, e.g. "https://github.com".
        browser: Optional browser app name, e.g. "Google Chrome" or "Safari". Leave empty to use the user's preferred browser.
    """
    from ..config import settings

    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    browser = browser or settings.browser
    if browser and platform.system() == "Darwin":
        result = subprocess.run(["open", "-a", browser, url], capture_output=True, text=True)
        if result.returncode != 0:
            return f"Could not open {url} in {browser}: {result.stderr.strip()}"
        return f"Opened {url} in {browser}"
    webbrowser.open(url)
    return f"Opened {url} in the system default browser"


@tool(dangerous=True)
def run_shell_command(command: str) -> str:
    """Run a shell command on the Mac and return its output. Requires user confirmation.

    Args:
        command: The shell command, e.g. "ls -la ~/Desktop".
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds."
    output = (result.stdout + result.stderr).strip()
    return f"exit code {result.returncode}\n{output[:3000]}"
