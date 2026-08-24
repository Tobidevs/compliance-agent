"""Phase 1 / 5.1 — the budget ledger, and the invariant that it is a hard cost ceiling.

Invariant 4: real MCP fetches are capped at `3 * len(controls)`, cache hits are free, and a
refused call never reaches the MCP client.
"""

import pytest
from conftest import make_control, stub_call_tool

from agent.budget import FETCHES_PER_CONTROL, TREES_PER_CONTROL, BudgetLedger
from agent.subagent_nodes import get_file_content, get_repository_tree
from agent.tools import think


def ledger_for(count: int) -> BudgetLedger:
    return BudgetLedger.for_controls([make_control(f"CC{i}") for i in range(count)])


# ---------------------------------------------------------------------------
# Ledger arithmetic
# ---------------------------------------------------------------------------
def test_ledger_is_sized_from_cluster_width():
    ledger = ledger_for(8)
    assert ledger.fetches_max == FETCHES_PER_CONTROL * 8
    assert ledger.trees_max == TREES_PER_CONTROL * 8


def test_empty_cluster_still_gets_a_bounded_allowance():
    ledger = BudgetLedger.for_controls([])
    assert ledger.fetches_max == FETCHES_PER_CONTROL
    assert ledger.trees_max == TREES_PER_CONTROL


def test_spend_refuses_once_the_per_control_allowance_is_gone():
    ledger = ledger_for(4)

    for _ in range(FETCHES_PER_CONTROL):
        assert ledger.spend("fetch") is None

    refusal = ledger.spend("fetch")
    assert refusal is not None
    assert refusal.startswith("BUDGET REFUSED")
    assert "conclude_evidence" in refusal
    # The cluster still has budget; only this control is exhausted.
    assert ledger.cluster_remaining("fetch") > 0


def test_spend_refuses_once_the_whole_cluster_allowance_is_gone():
    ledger = ledger_for(2)
    # Advance the current control between allowances so the cluster cap is what bites.
    for index in range(2):
        ledger.control_index = index
        for _ in range(FETCHES_PER_CONTROL):
            assert ledger.spend("fetch") is None

    ledger.control_index = 1
    refusal = ledger.spend("fetch")
    assert refusal is not None
    assert "entire cluster is exhausted" in refusal


def test_a_refusal_does_not_consume_budget():
    ledger = ledger_for(1)
    for _ in range(FETCHES_PER_CONTROL):
        ledger.spend("fetch")

    used_before = ledger.fetches_used
    ledger.spend("fetch")
    assert ledger.fetches_used == used_before
    assert ledger.refusals == 1


def test_recursion_limit_is_derived_from_the_budget():
    ledger = ledger_for(8)
    expected = 2 * (ledger.fetches_max + ledger.trees_max + 2 * 8 + 4)
    assert ledger.recursion_limit() == expected


def test_sync_progress_tracks_the_concluded_control_count():
    from conftest import tool_result

    ledger = ledger_for(3)
    ledger.sync_progress(
        [tool_result("conclude_evidence", "a"), tool_result("get_file_content", "b")]
    )
    assert ledger.control_index == 1
    assert ledger.current_control_id == "CC1"


# ---------------------------------------------------------------------------
# think reports the budget; the model no longer supplies it (Phase 1.3)
# ---------------------------------------------------------------------------
def test_think_does_not_accept_model_supplied_budget_arguments():
    params = set(think.args_schema.model_fields)
    assert "fetches_remaining" not in params
    assert "tree_calls_remaining" not in params


def test_think_returns_the_server_computed_remainders():
    ledger = ledger_for(2)
    ledger.spend("fetch")

    reported = think.func(
        evidence="saw middleware",
        code_snippets=[],
        finished=False,
        state={"budget": ledger},
    )

    assert reported["fetches_remaining_this_control"] == FETCHES_PER_CONTROL - 1
    assert reported["fetches_remaining_this_cluster"] == ledger.fetches_max - 1
    assert reported["current_control"] == "CC0"


# ---------------------------------------------------------------------------
# Invariant 4 — enforcement at the tool boundary
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_refused_fetches_never_reach_the_mcp_client(monkeypatch, manager):
    monkeypatch.setattr(
        "agent.subagent_nodes.get_github_mcp_manager", lambda: manager
    )
    calls = stub_call_tool(monkeypatch, manager, {})

    ledger = ledger_for(1)
    state = {"repo_owner": "o", "repo_name": "r", "budget": ledger}

    async with manager.cluster_scope():
        results = [
            await get_file_content.ainvoke({"path": f"file{i}.ts", "state": state})
            for i in range(FETCHES_PER_CONTROL + 3)
        ]

    # Invariant: real fetches capped at 3 * len(controls); every extra call is refused.
    assert len(calls) == FETCHES_PER_CONTROL
    assert all(r.startswith("BUDGET REFUSED") for r in results[FETCHES_PER_CONTROL:])


@pytest.mark.asyncio
async def test_fetch_budget_scales_with_cluster_width(monkeypatch, manager):
    monkeypatch.setattr(
        "agent.subagent_nodes.get_github_mcp_manager", lambda: manager
    )
    calls = stub_call_tool(monkeypatch, manager, {})

    controls = [make_control(f"CC{i}") for i in range(4)]
    ledger = BudgetLedger.for_controls(controls)
    state = {"repo_owner": "o", "repo_name": "r", "budget": ledger}

    async with manager.cluster_scope():
        for i in range(50):
            # Walk the current control forward so per-control caps do not mask the total.
            ledger.control_index = i % len(controls)
            await get_file_content.ainvoke({"path": f"file{i}.ts", "state": state})

    assert len(calls) == FETCHES_PER_CONTROL * len(controls)


@pytest.mark.asyncio
async def test_refused_tree_calls_never_reach_the_mcp_client(monkeypatch, manager):
    monkeypatch.setattr(
        "agent.subagent_nodes.get_github_mcp_manager", lambda: manager
    )
    calls = stub_call_tool(monkeypatch, manager, {})

    ledger = ledger_for(1)
    state = {"repo_owner": "o", "repo_name": "r", "budget": ledger}

    for i in range(TREES_PER_CONTROL + 2):
        await get_repository_tree.ainvoke({"path_filter": f"src{i}", "state": state})

    assert len(calls) == TREES_PER_CONTROL


@pytest.mark.asyncio
async def test_no_pinned_repo_short_circuits_before_any_spend(monkeypatch, manager):
    monkeypatch.setattr(
        "agent.subagent_nodes.get_github_mcp_manager", lambda: manager
    )
    calls = stub_call_tool(monkeypatch, manager, {})

    ledger = ledger_for(2)
    result = await get_file_content.ainvoke(
        {"path": "a.ts", "state": {"repo_owner": "", "repo_name": "", "budget": ledger}}
    )

    assert "REPOSITORY NOT CONFIGURED" in result
    assert calls == []
    assert ledger.fetches_used == 0
