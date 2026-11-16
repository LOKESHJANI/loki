"""The "brain": a thin adapter around the LLM.

The rest of LOKI only knows about the `Brain` protocol below, so switching
from Ollama to Claude or OpenAI later means writing one new class - nothing
else changes. (This is the Adapter pattern; a good interview talking point.)

Every brain returns the same normalized shape:
    {"content": "text reply", "tool_calls": [{"name": "...", "arguments": {...}}]}
"""
from __future__ import annotations

from typing import Protocol


class Brain(Protocol):
    def chat(self, messages: list[dict], tools: list[dict]) -> dict: ...


class OllamaBrain:
    """Talks to a local Ollama server (https://ollama.com)."""

    def __init__(self, model: str, host: str):
        import ollama  # imported lazily so tests don't need it

        self.model = model
        self.client = ollama.Client(host=host)

    def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        response = self.client.chat(model=self.model, messages=messages, tools=tools)
        msg = response.message
        calls = [
            {"name": c.function.name, "arguments": dict(c.function.arguments or {})}
            for c in (msg.tool_calls or [])
        ]
        return {"content": msg.content or "", "tool_calls": calls}
