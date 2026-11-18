"""Tests run without Ollama or a microphone: we swap in a FakeBrain that
replays scripted LLM replies. This is dependency injection in action."""
from pathlib import Path

import pytest

from loki import safety
from loki.agent import Agent
from loki.config import settings
from loki.tools import REGISTRY
from loki.tools.registry import tool


class FakeBrain:
    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def chat(self, messages, tools):
        self.seen.append(list(messages))
        return self.replies.pop(0)


def reply(content="", calls=None):
    return {"content": content, "tool_calls": calls or []}


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "allowed_dirs", [tmp_path.resolve()])
    return tmp_path


def test_schema_built_from_docstring():
    schema = REGISTRY["read_file"].schema()["function"]
    assert schema["name"] == "read_file"
    assert schema["parameters"]["required"] == ["path"]
    assert "File path" in schema["parameters"]["properties"]["path"]["description"]


def test_plain_answer_needs_no_tools():
    agent = Agent(FakeBrain([reply("Hello Bharath")]), confirm=lambda *_: True)
    assert agent.ask("hi") == "Hello Bharath"


def test_agent_runs_tool_and_feeds_result_back(sandbox):
    (sandbox / "todo.txt").write_text("buy milk")
    brain = FakeBrain(
        [
            reply(calls=[{"name": "read_file", "arguments": {"path": str(sandbox / "todo.txt")}}]),
            reply("Your todo says buy milk."),
        ]
    )
    agent = Agent(brain, confirm=lambda *_: True)
    assert agent.ask("what's on my todo?") == "Your todo says buy milk."
    tool_msg = brain.seen[1][-1]
    assert tool_msg["role"] == "tool" and tool_msg["content"] == "buy milk"


def test_dangerous_tool_blocked_when_user_declines(sandbox):
    target = sandbox / "x.txt"
    brain = FakeBrain(
        [
            reply(calls=[{"name": "write_file", "arguments": {"path": str(target), "content": "hi"}}]),
            reply("Okay, I didn't write it."),
        ]
    )
    Agent(brain, confirm=lambda *_: False).ask("write a file")
    assert not target.exists()
    assert "declined" in brain.seen[1][-1]["content"]


def test_sandbox_blocks_paths_outside_allowed(sandbox):
    with pytest.raises(safety.PermissionDenied):
        safety.safe_path(str(sandbox / ".." / "secret.txt"))


def test_tool_errors_do_not_crash_agent(sandbox):
    @tool()
    def boom() -> str:
        """Always fails."""
        raise RuntimeError("kaboom")

    try:
        brain = FakeBrain([reply(calls=[{"name": "boom", "arguments": {}}]), reply("That failed.")])
        assert Agent(brain, confirm=lambda *_: True).ask("go") == "That failed."
        assert "kaboom" in brain.seen[1][-1]["content"]
    finally:
        REGISTRY.pop("boom")


def test_step_limit_stops_infinite_loops():
    looping = [reply(calls=[{"name": "get_datetime", "arguments": {}}])] * 3
    agent = Agent(FakeBrain(looping), confirm=lambda *_: True, max_steps=3)
    assert "more steps" in agent.ask("loop forever")


def test_unknown_tool_is_reported():
    brain = FakeBrain([reply(calls=[{"name": "hack_nasa", "arguments": {}}]), reply("Can't do that.")])
    Agent(brain, confirm=lambda *_: True).ask("x")
    assert "no tool called" in brain.seen[1][-1]["content"]


def test_text_tool_call_fallback_parses_known_tools_only():
    from loki.brain import extract_text_tool_calls

    known = {"get_datetime", "read_file"}
    tagged = '<tool_call>{"name": "read_file", "arguments": {"path": "~/x.txt"}}</tool_call>'
    assert extract_text_tool_calls(tagged, known) == [{"name": "read_file", "arguments": {"path": "~/x.txt"}}]
    bare = 'Sure: {"name": "get_datetime", "arguments": {}}'
    assert extract_text_tool_calls(bare, known) == [{"name": "get_datetime", "arguments": {}}]
    assert extract_text_tool_calls('{"name": "delete_everything", "arguments": {}}', known) == []
    assert extract_text_tool_calls("The current time is [get_datetime].", known) == []


def test_system_prompt_covers_web_rules():
    from loki.agent import SYSTEM_PROMPT

    assert "web_search" in SYSTEM_PROMPT and "read_webpage" in SYSTEM_PROMPT
    assert "UNTRUSTED WEB CONTENT" in SYSTEM_PROMPT
    assert "CANNOT" in SYSTEM_PROMPT


def test_agent_chains_search_then_read(sandbox, monkeypatch):
    from loki.tools import web

    monkeypatch.setattr(web, "_search", lambda q, n: [{"title": "T", "href": "https://example.org", "body": "b"}])
    monkeypatch.setattr(web, "is_public_host", lambda h: True)
    monkeypatch.setattr(web, "_fetch", lambda u: "<html/>")
    monkeypatch.setattr(web, "_extract_text", lambda h: "The answer is 42.")
    brain = FakeBrain(
        [
            reply(calls=[{"name": "web_search", "arguments": {"query": "answer"}}]),
            reply(calls=[{"name": "read_webpage", "arguments": {"url": "https://example.org"}}]),
            reply("It's 42, according to example.org."),
        ]
    )
    assert Agent(brain, confirm=lambda *_: True).ask("what is the answer?") == "It's 42, according to example.org."
    assert "The answer is 42." in brain.seen[2][-1]["content"]


def test_trim_history_keeps_system_prompt_and_starts_at_user(monkeypatch):
    from loki import agent as agent_mod

    monkeypatch.setattr(agent_mod, "MAX_HISTORY_CHARS", 100)
    a = Agent(FakeBrain([]), confirm=lambda *_: True)
    system = a.history[0]
    for i in range(5):
        a.history += [
            {"role": "user", "content": f"q{i}" * 10},
            {"role": "assistant", "content": "", "tool_calls": []},
            {"role": "tool", "content": "r" * 30},
            {"role": "assistant", "content": "a" * 10},
        ]
    a.trim_history()
    assert a.history[0] is system
    assert a.history[1]["role"] == "user"
    assert sum(len(m["content"]) for m in a.history[1:]) <= 100
    assert a.history[-1]["content"] == "a" * 10  # newest turn survives
