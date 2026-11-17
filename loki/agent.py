"""The agent loop - the heart of LOKI.

    user request
        |
        v
    +-> LLM thinks (sees conversation + tool list)
    |       |
    |       |-- replies with text only? --> done, return the answer
    |       |
    |       '-- asks for tool call(s)
    |               |
    |               v
    |        run each tool (with sandbox + confirmation)
    |               |
    '------ append results to conversation

This is often called the ReAct pattern (Reason + Act).
"""
from __future__ import annotations

from typing import Callable

from .brain import Brain
from .safety import PermissionDenied
from .tools import REGISTRY, Tool

SYSTEM_PROMPT = """You are LOKI, a personal AI assistant running on the user's Mac.
You can take real actions by calling the provided tool functions.

Rules:
- If a request needs real information (time, files, folders) or an action (open, write, run), CALL THE TOOL FUNCTION. Do not describe the call, and never write placeholders like [get_datetime] or [time].
- Only answer after you have the tool result, and base the answer on that result.
- Never invent file contents, dates or results.
- Folder shortcuts: Downloads = ~/Downloads, Desktop = ~/Desktop, Documents = ~/Documents.
- If a tool returns an error or the user declines, say so plainly.
- Replies are spoken aloud: keep them short (1-3 sentences), no markdown, no lists of more than 5 items."""

ConfirmFn = Callable[[str, dict], bool]
EventFn = Callable[[str, str], None]
MAX_RESULT_CHARS = 6000


class Agent:
    def __init__(
        self,
        brain: Brain,
        confirm: ConfirmFn,
        max_steps: int = 8,
        tools: dict[str, Tool] | None = None,
        on_event: EventFn | None = None,
    ):
        self.brain = brain
        self.confirm = confirm
        self.max_steps = max_steps
        self.tools = tools if tools is not None else REGISTRY
        self.on_event = on_event or (lambda kind, text: None)
        self.history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    @property
    def tool_schemas(self) -> list[dict]:
        return [t.schema() for t in self.tools.values()]

    def ask(self, user_text: str) -> str:
        self.history.append({"role": "user", "content": user_text})

        for _ in range(self.max_steps):
            reply = self.brain.chat(self.history, self.tool_schemas)
            self.history.append(
                {
                    "role": "assistant",
                    "content": reply["content"],
                    "tool_calls": [
                        {"function": {"name": c["name"], "arguments": c["arguments"]}}
                        for c in reply["tool_calls"]
                    ],
                }
            )

            if not reply["tool_calls"]:
                return reply["content"]

            for call in reply["tool_calls"]:
                self.on_event("tool", f"{call['name']}({call['arguments']})")
                result = self.run_tool(call["name"], call["arguments"])
                self.on_event("result", result[:200])
                self.history.append({"role": "tool", "content": result, "tool_name": call["name"]})

        return "Sorry, that took more steps than I'm allowed. Try breaking it into smaller requests."

    def run_tool(self, name: str, args: dict) -> str:
        tool = self.tools.get(name)
        if tool is None:
            return f"Error: there is no tool called '{name}'."
        if tool.dangerous and not self.confirm(name, args):
            return "The user declined this action."
        try:
            return str(tool.func(**args))[:MAX_RESULT_CHARS]
        except PermissionDenied as e:
            return f"Permission denied: {e}"
        except TypeError as e:
            return f"Error: wrong arguments for {name}: {e}"
        except Exception as e:  # tool bugs shouldn't crash the assistant
            return f"Error running {name}: {type(e).__name__}: {e}"

    def reset(self) -> None:
        self.history = self.history[:1]
