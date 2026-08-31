"""Executable documentation for the two testability traps that cost real debugging time.

These tests exist so the next person meets the trap as a named, passing test rather than as
a confusing failure. Neither asserts product behaviour; both pin harness behaviour.
"""

import pytest
from conftest import make_control, stub_call_tool
from langgraph.config import get_stream_writer

from agent.budget import BudgetLedger
from agent.nodes import combine_validation_results
from agent.subagent_nodes import get_file_content


def _flatten_messages(error: BaseException) -> str:
    """Collect messages across nested ExceptionGroups, which anyio raises from TaskGroups."""
    parts = [str(error)]
    for sub in getattr(error, "exceptions", ()):
        parts.append(_flatten_messages(sub))
    return " ".join(parts)


def test_trap_nodes_need_get_stream_writer_patched(monkeypatch):
    """TRAP 1: nodes raise outside a runnable context.

    `combine_validation_results` calls `get_stream_writer()`. Invoked directly — as every
    node test does — that raises `RuntimeError: Called get_config outside of a runnable
    context` before any of the node's own logic runs. The autouse `stream_events` fixture in
    conftest.py patches it; here we undo the patch to show what happens without it.
    """
    monkeypatch.setattr("agent.nodes.get_stream_writer", get_stream_writer)

    with pytest.raises(RuntimeError, match="outside of a runnable context"):
        combine_validation_results({"clusters": {}, "validation_results": []})


@pytest.mark.asyncio
async def test_trap_patching_fetch_path_silently_disables_the_cache(monkeypatch, manager):
    """TRAP 2: the cache lives INSIDE `GitHubMCPManager.fetch_path`.

    Stubbing `fetch_path` replaces the caching layer itself, so every call looks like a miss
    and a cache assertion built on that stub passes for the wrong reason. Cache tests must
    stub the transport (`_call_tool`) instead — which is what `stub_call_tool` does.
    """
    monkeypatch.setattr("agent.subagent_nodes.get_github_mcp_manager", lambda: manager)

    # The WRONG way: patch fetch_path and the cache is gone.
    fetch_calls = []

    async def fake_fetch_path(owner, repo, path):
        from agent.utils.github_mcp import FileContent

        fetch_calls.append(path)
        return FileContent(path=path, text="body")

    monkeypatch.setattr(manager, "fetch_path", fake_fetch_path)

    ledger = BudgetLedger.for_controls([make_control("CC6.1")])
    state = {"repo_owner": "o", "repo_name": "r", "budget": ledger}

    async with manager.cluster_scope():
        await get_file_content.ainvoke({"path": "a.ts", "state": state})
        await get_file_content.ainvoke({"path": "a.ts", "state": state})

    # Two "fetches" and two budget debits, because the caching layer was stubbed away.
    assert fetch_calls == ["a.ts", "a.ts"]
    assert ledger.fetches_used == 2


@pytest.mark.asyncio
async def test_trap_stubbing_the_transport_keeps_the_cache_live(monkeypatch, manager):
    """The RIGHT way: same scenario, transport stubbed, so the cache does its job."""
    monkeypatch.setattr("agent.subagent_nodes.get_github_mcp_manager", lambda: manager)
    calls = stub_call_tool(monkeypatch, manager, {"a.ts": "body"})

    ledger = BudgetLedger.for_controls([make_control("CC6.1")])
    state = {"repo_owner": "o", "repo_name": "r", "budget": ledger}

    async with manager.cluster_scope():
        await get_file_content.ainvoke({"path": "a.ts", "state": state})
        await get_file_content.ainvoke({"path": "a.ts", "state": state})

    assert len(calls) == 1
    assert ledger.fetches_used == 1


@pytest.mark.asyncio
async def test_trap_cluster_scope_opens_a_real_session_unless_stubbed():
    """TRAP 3: `cluster_scope()` connects before any tool call.

    Stubbing `_call_tool` is not enough — `client.session("github")` opens a live MCP
    handshake first and 400s. The `manager` fixture stubs the session too; an unstubbed
    manager trips the autouse socket guard instead of silently reaching the network.
    """
    from agent.utils.github_mcp import GitHubMCPManager

    unstubbed = GitHubMCPManager()

    with pytest.raises(BaseException) as excinfo:
        async with unstubbed.cluster_scope():
            pass

    # anyio wraps the guard's AssertionError in an ExceptionGroup; assert on the message so
    # this cannot pass for some incidental unrelated failure.
    assert "live network connection" in _flatten_messages(excinfo.value)
