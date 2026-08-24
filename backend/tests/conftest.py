"""Shared fixtures for the backend suite.

Three testability traps are encoded here because all three cost real debugging time:

1. Every graph node calls `get_stream_writer()`, which raises
   `RuntimeError: Called get_config outside of a runnable context` when the node is invoked
   directly instead of through the graph. The autouse `stream_events` fixture patches it in
   both node modules, so node tests just work. `test_traps.py` pins the behaviour.
2. The file cache lives INSIDE `GitHubMCPManager.fetch_path`. Stubbing `fetch_path` in a
   test silently disables the cache and the test then passes for the wrong reason, so cache
   tests stub the transport (`_call_tool`) instead — see `stub_call_tool`.
3. `cluster_scope()` opens a real MCP session BEFORE any tool call, so stubbing `_call_tool`
   alone still hits `api.githubcopilot.com` and fails with a confusing 400. The `manager`
   fixture stubs `client.session` too, and `_no_sockets` turns any live call anywhere in the
   suite into an immediate, obvious failure.
"""

import json
import socket
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import nodes, subagent_nodes  # noqa: E402
from agent.state import ControlValidation, EvidenceResult, ValidationFinding  # noqa: E402
from agent.utils.github_mcp import GitHubMCPManager  # noqa: E402


@pytest.fixture(autouse=True)
def _no_sockets(monkeypatch):
    """No test may touch the network. Fail loudly instead of 400-ing against a real host."""

    def blocked(*args, **kwargs):
        raise AssertionError(
            "A test attempted a live network connection. Stub the transport "
            "(`_call_tool`) and the MCP session (`client.session`) instead."
        )

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)


@pytest.fixture(autouse=True)
def stream_events(monkeypatch):
    """Patch `get_stream_writer` in both node modules and record what nodes emit.

    Without this, calling any node directly raises RuntimeError before its logic runs.
    """
    events: list[dict] = []
    monkeypatch.setattr(nodes, "get_stream_writer", lambda: events.append)
    monkeypatch.setattr(subagent_nodes, "get_stream_writer", lambda: events.append)
    return events


# ---------------------------------------------------------------------------
# Message builders
# ---------------------------------------------------------------------------
def ai_tool_call(name: str, args: dict, call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


def ai_tool_calls(calls: list[tuple[str, dict, str]]) -> AIMessage:
    """One assistant turn issuing several tool calls, which is what the prompt encourages."""
    return AIMessage(
        content="",
        tool_calls=[
            {"name": name, "args": args, "id": call_id, "type": "tool_call"}
            for name, args, call_id in calls
        ],
    )


def tool_result(name: str, call_id: str, content="{}") -> ToolMessage:
    body = content if isinstance(content, str) else json.dumps(content)
    return ToolMessage(content=body, name=name, tool_call_id=call_id)


def human(text: str = "assignment") -> HumanMessage:
    return HumanMessage(content=text)


# ---------------------------------------------------------------------------
# Domain object builders
# ---------------------------------------------------------------------------
def make_control(regulation_id: str, category: str = "System Operations", **extra) -> dict:
    control = {
        "regulation_id": regulation_id,
        "title": f"Control {regulation_id}",
        "requirement": f"Requirement text for {regulation_id}",
        "points_of_focus": "focus a|focus b",
        "category": category,
    }
    control.update(extra)
    return control


def make_regulation(control_id: str, category: str = "System Operations", **extra) -> dict:
    """A raw Pinecone-shaped record, as `format_regulation_results` emits it."""
    record = {
        "control_id": control_id,
        "title": f"Control {control_id}",
        "requirement": f"Requirement text for {control_id}",
        "points_of_focus": "focus a|focus b",
        "category": category,
    }
    record.update(extra)
    return record


def make_evidence(regulation_id: str, **extra) -> EvidenceResult:
    payload = {
        "regulation_id": regulation_id,
        "title": f"Control {regulation_id}",
        "requirement": "req",
        "files_searched": ["src/middleware.ts"],
        "code_snippets": ["export const config = {}"],
        "description": "found something",
        "no_evidence_found": False,
        "points_of_focus_coverage": [],
    }
    payload.update(extra)
    return EvidenceResult(**payload)


def make_validation(regulation_id: str, status: str = "PASS") -> ControlValidation:
    return ControlValidation(
        regulation_id=regulation_id,
        title=f"Control {regulation_id}",
        status=status,
        severity=None,
        confidence=0.8,
        confidence_label="High",
        findings=[ValidationFinding(type="pass", description="ok", reasoning="because")],
        points_of_focus=[],
        overall_reasoning="reasoned",
    )


# ---------------------------------------------------------------------------
# GitHub MCP transport stubbing
# ---------------------------------------------------------------------------
class _FakeContent:
    def __init__(self, text):
        self.text = text


class _FakeToolResult:
    def __init__(self, text):
        self.content = [_FakeContent(text)]


def stub_call_tool(monkeypatch, manager: GitHubMCPManager, responses: dict[str, str]):
    """Stub the MCP transport, NOT `fetch_path`.

    `fetch_path` is where the cache lives: patching it would disable caching and any cache
    assertion built on top would be vacuous. Returns the list of payloads that actually
    reached the wire, so callers can count real fetches.
    """
    calls: list[dict] = []

    async def fake_call_tool(tool_name, payload):
        calls.append({"tool": tool_name, **payload})
        return _FakeToolResult(responses.get(payload.get("path", ""), "default body"))

    monkeypatch.setattr(manager, "_call_tool", fake_call_tool)
    return calls


@pytest.fixture
def manager() -> GitHubMCPManager:
    """A real manager with a stubbed session; only the transport layer is faked.

    `cluster_scope()` enters `client.session("github")` before any tool call, so stubbing
    `_call_tool` alone still opens a live HTTP/MCP handshake. The session object itself is
    never used once `_call_tool` is stubbed, so an inert placeholder is enough.
    """
    instance = GitHubMCPManager()

    @asynccontextmanager
    async def fake_session(*args, **kwargs):
        yield object()

    instance.client.session = fake_session
    return instance
