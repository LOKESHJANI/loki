"""Tool registry.

A "tool" is just a Python function the LLM is allowed to call. The LLM never
runs code itself - it replies with JSON like
    {"name": "read_file", "arguments": {"path": "~/Documents/notes.txt"}}
and *our* code runs the function and sends the result back.

To tell the LLM which tools exist, we send a JSON Schema for each one. This
module builds that schema automatically from the function's type hints and
docstring, so adding a tool is just:

    @tool()
    def get_weather(city: str) -> str:
        \"\"\"Get the weather for a city.

        Args:
            city: City name, e.g. "Halifax".
        \"\"\"
"""
from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Any, Callable, get_type_hints

_TYPE_MAP = {str: "string", int: "integer", float: "number", bool: "boolean"}


@dataclass
class Tool:
    name: str
    description: str
    func: Callable[..., Any]
    parameters: dict
    dangerous: bool = False

    def schema(self) -> dict:
        """OpenAI/Ollama-style function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


REGISTRY: dict[str, Tool] = {}


def _parse_docstring(doc: str | None) -> tuple[str, dict[str, str]]:
    doc = inspect.cleandoc(doc or "")
    summary, _, rest = doc.partition("Args:")
    arg_docs = {}
    for line in rest.splitlines():
        m = re.match(r"\s*(\w+)\s*:\s*(.+)", line)
        if m:
            arg_docs[m.group(1)] = m.group(2).strip()
    return " ".join(summary.split()), arg_docs


def tool(dangerous: bool = False) -> Callable:
    """Decorator that registers a function as an LLM tool."""

    def wrap(func: Callable) -> Callable:
        summary, arg_docs = _parse_docstring(func.__doc__)
        hints = get_type_hints(func)
        props, required = {}, []
        for name, param in inspect.signature(func).parameters.items():
            props[name] = {
                "type": _TYPE_MAP.get(hints.get(name, str), "string"),
                "description": arg_docs.get(name, ""),
            }
            if param.default is inspect.Parameter.empty:
                required.append(name)
        REGISTRY[func.__name__] = Tool(
            name=func.__name__,
            description=summary,
            func=func,
            parameters={"type": "object", "properties": props, "required": required},
            dangerous=dangerous,
        )
        return func

    return wrap
