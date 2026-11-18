"""The "brain": a thin adapter around the LLM.

The rest of LOKI only knows about the `Brain` protocol below, so switching
from Ollama to Claude or OpenAI later means writing one new class - nothing
else changes. (This is the Adapter pattern; a good interview talking point.)

Every brain returns the same normalized shape:
    {"content": "text reply", "tool_calls": [{"name": "...", "arguments": {...}}]}
"""
from __future__ import annotations

import json
import re
from typing import Protocol


class Brain(Protocol):
    def chat(self, messages: list[dict], tools: list[dict]) -> dict: ...


def extract_text_tool_calls(content: str, known_tools: set[str]) -> list[dict]:
    """Fallback for small local models that *write* a tool call as text
    instead of using the structured tool_calls field, e.g.

        <tool_call>{"name": "get_datetime", "arguments": {}}</tool_call>
        {"name": "read_file", "arguments": {"path": "~/x.txt"}}

    Only calls to tools we actually have are accepted.
    """
    calls = []
    candidates = re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.S)
    if not candidates:
        candidates = re.findall(r"\{[^{}]*\"name\"[^{}]*(?:\{[^{}]*\}[^{}]*)?\}", content, re.S)
    for raw in candidates:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        name = obj.get("name")
        args = obj.get("arguments", obj.get("parameters", {})) or {}
        if name in known_tools and isinstance(args, dict):
            calls.append({"name": name, "arguments": args})
    return calls


class OllamaBrain:
    """Talks to a local Ollama server (https://ollama.com)."""

    def __init__(self, model: str, host: str, temperature: float = 0.0, keep_alive: str = "2m"):
        import ollama  # imported lazily so tests don't need it

        self.model = model
        self.client = ollama.Client(host=host)
        # Temperature 0 = most predictable output, which makes tool use reliable.
        self.options = {"temperature": temperature}
        # Unload the model from RAM this long after the last reply (matters on 8 GB Macs).
        self.keep_alive = keep_alive

    def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        response = self.client.chat(
            model=self.model, messages=messages, tools=tools, options=self.options, keep_alive=self.keep_alive
        )
        msg = response.message
        content = msg.content or ""
        calls = [
            {"name": c.function.name, "arguments": dict(c.function.arguments or {})}
            for c in (msg.tool_calls or [])
        ]
        if not calls and content:
            known = {t["function"]["name"] for t in tools}
            calls = extract_text_tool_calls(content, known)
            if calls:
                content = ""  # it was a tool call, not an answer
        return {"content": content, "tool_calls": calls}
