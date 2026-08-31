"""Phase 0.2 / 5.1 — evidence extraction and termination under parallel tool calls.

The system prompt encourages several tool calls per turn, so `ToolNode` emits a *batch* of
ToolMessages. Every function here has to be correct for any ordering within that batch.
"""

from conftest import ai_tool_call, ai_tool_calls, human, make_evidence, tool_result

from agent.subagent_nodes import (
    _extract_concluded_evidence_result,
    _extract_pending_concluded_evidence_results,
    is_finished,
)


def _conclude_turn(regulation_id: str, call_id: str):
    """One conclude_evidence tool call and its result."""
    args = {"evidence_result": make_evidence(regulation_id).model_dump()}
    return ai_tool_call("conclude_evidence", args, call_id), tool_result(
        "conclude_evidence", call_id
    )


# ---------------------------------------------------------------------------
# is_finished — Phase 0.2
# ---------------------------------------------------------------------------
def test_is_finished_when_terminate_signal_is_last():
    messages = [human(), ai_tool_call("finished_gathering_evidence", {}, "1"),
                tool_result("finished_gathering_evidence", "1")]
    assert is_finished({"messages": messages}) == "process_evidence"


def test_is_finished_when_terminate_signal_is_not_last_in_the_batch():
    # The original bug: only messages[-1] was inspected, so a parallel batch that put
    # finished_gathering_evidence anywhere but last looped until the recursion limit.
    ai = ai_tool_calls(
        [
            ("think", {"evidence": "x", "code_snippets": [], "finished": True}, "a"),
            ("finished_gathering_evidence", {}, "b"),
            ("think", {"evidence": "y", "code_snippets": [], "finished": True}, "c"),
        ]
    )
    messages = [
        human(),
        ai,
        tool_result("think", "a"),
        tool_result("finished_gathering_evidence", "b"),
        tool_result("think", "c"),
    ]

    assert is_finished({"messages": messages}) == "process_evidence"


def test_is_finished_stops_scanning_at_the_previous_model_turn():
    # A terminate signal from an EARLIER batch must not end a later gathering turn.
    messages = [
        human(),
        ai_tool_call("finished_gathering_evidence", {}, "old"),
        tool_result("finished_gathering_evidence", "old"),
        ai_tool_call("get_file_content", {"path": "a.ts"}, "new"),
        tool_result("get_file_content", "new", "body"),
    ]

    assert is_finished({"messages": messages}) == "gather_evidence"


def test_is_finished_keeps_gathering_without_a_signal():
    messages = [human(), ai_tool_call("get_file_content", {"path": "a.ts"}, "1"),
                tool_result("get_file_content", "1", "body")]
    assert is_finished({"messages": messages}) == "gather_evidence"


# ---------------------------------------------------------------------------
# _extract_concluded_evidence_result
# ---------------------------------------------------------------------------
def test_extracts_conclusion_from_the_matching_tool_call_args():
    ai, result = _conclude_turn("CC6.1", "call-1")

    extracted = _extract_concluded_evidence_result({"messages": [human(), ai, result]})

    assert [e.regulation_id for e in extracted] == ["CC6.1"]


def test_extracts_nothing_when_last_message_is_not_a_conclusion():
    messages = [human(), ai_tool_call("get_file_content", {"path": "a"}, "1"),
                tool_result("get_file_content", "1", "body")]
    assert _extract_concluded_evidence_result({"messages": messages}) == []


def test_extracts_nothing_from_an_empty_thread():
    assert _extract_concluded_evidence_result({"messages": []}) == []


def test_malformed_conclusion_degrades_instead_of_raising():
    # A control whose id survived must stay visible downstream, not vanish.
    ai = ai_tool_call(
        "conclude_evidence",
        {"evidence_result": {"regulation_id": "CC6.1", "files_searched": "not-a-list"}},
        "call-1",
    )
    extracted = _extract_concluded_evidence_result(
        {"messages": [human(), ai, tool_result("conclude_evidence", "call-1")]}
    )

    assert len(extracted) == 1
    assert extracted[0].regulation_id == "CC6.1"
    assert extracted[0].no_evidence_found is True


def test_malformed_conclusion_without_an_id_is_dropped():
    ai = ai_tool_call("conclude_evidence", {"evidence_result": {"title": "?"}}, "call-1")
    extracted = _extract_concluded_evidence_result(
        {"messages": [human(), ai, tool_result("conclude_evidence", "call-1")]}
    )
    assert extracted == []


# ---------------------------------------------------------------------------
# _extract_pending_concluded_evidence_results
# ---------------------------------------------------------------------------
def test_collects_the_trailing_conclusion():
    ai_a, res_a = _conclude_turn("CC6.1", "a")

    pending = _extract_pending_concluded_evidence_results(
        {"messages": [human(), ai_a, res_a]}
    )

    assert [e.regulation_id for e in pending] == ["CC6.1"]


def test_skips_conclusions_already_consumed_by_a_later_model_turn():
    # A conclusion followed by an AI turn was already returned by gather_evidence_node;
    # re-emitting it here would double it through the operator.add reducer.
    ai_a, res_a = _conclude_turn("CC6.1", "a")
    ai_b, res_b = _conclude_turn("CC6.2", "b")

    pending = _extract_pending_concluded_evidence_results(
        {"messages": [human(), ai_a, res_a, ai_b, res_b]}
    )

    assert [e.regulation_id for e in pending] == ["CC6.2"]


def test_collects_a_parallel_batch_of_conclusions_in_one_turn():
    args_a = {"evidence_result": make_evidence("CC6.1").model_dump()}
    args_b = {"evidence_result": make_evidence("CC6.2").model_dump()}
    ai = ai_tool_calls(
        [("conclude_evidence", args_a, "a"), ("conclude_evidence", args_b, "b")]
    )
    messages = [
        human(),
        ai,
        tool_result("conclude_evidence", "a"),
        tool_result("conclude_evidence", "b"),
    ]

    pending = _extract_pending_concluded_evidence_results({"messages": messages})

    assert sorted(e.regulation_id for e in pending) == ["CC6.1", "CC6.2"]
