"""Phase 4.3 — 5.6 invariant 5: compaction preserves message count and never unwraps.

Two failures this guards, both silent:
- Dropping a ToolMessage outright orphans its `tool_use` block and the provider rejects the
  whole request.
- Removing a `wrap_untrusted` wrapper while keeping the content inside it would hand the
  model raw repository bytes with no containment — the unwrap failure.
"""

from conftest import ai_tool_call, human, tool_result

from agent.compaction import MIN_COMPACT_CHARS, compact_thread
from agent.untrusted import FILE_TAG, UNTRUSTED_REMINDER, wrap_untrusted

BODY = "const secret = 1\n" * 40


def wrapped_file(path: str = "src/middleware.ts") -> str:
    return wrap_untrusted(FILE_TAG, path, BODY)


def thread_with_conclusion():
    """A realistic cluster thread: fetch, think, conclude, then keep working."""
    return [
        human(),
        ai_tool_call("get_file_content", {"path": "src/middleware.ts"}, "f1"),
        tool_result("get_file_content", "f1", wrapped_file()),
        ai_tool_call("think", {"evidence": "auth middleware present"}, "t1"),
        tool_result("think", "t1", '{"status": "logged"}'),
        ai_tool_call("conclude_evidence", {}, "c1"),
        tool_result("conclude_evidence", "c1", "{}"),
        ai_tool_call("get_file_content", {"path": "src/next.ts"}, "f2"),
        tool_result("get_file_content", "f2", wrapped_file("src/next.ts")),
    ]


def test_message_count_is_preserved():
    messages = thread_with_conclusion()

    compacted = compact_thread(messages)

    # Deleting the ToolMessage would orphan its tool_use block and the provider 400s.
    assert len(compacted) == len(messages)


def test_tool_call_ids_are_preserved():
    messages = thread_with_conclusion()

    compacted = compact_thread(messages)

    original_ids = [getattr(m, "tool_call_id", None) for m in messages]
    assert [getattr(m, "tool_call_id", None) for m in compacted] == original_ids


def test_pre_conclusion_file_bytes_are_replaced_by_a_pointer():
    compacted = compact_thread(thread_with_conclusion())

    assert compacted[2].content.startswith("[compacted:")
    assert "src/middleware.ts" in compacted[2].content
    assert "const secret" not in compacted[2].content


def test_compaction_never_leaves_content_without_its_wrapper():
    """The unwrap failure: repo bytes surviving with their delimiters stripped."""
    for message in compact_thread(thread_with_conclusion()):
        content = message.content
        if not isinstance(content, str) or "const secret" not in content:
            continue
        # Any message still carrying repo bytes must still carry the full wrapper.
        assert content.startswith(f"<{FILE_TAG} ")
        assert f"</{FILE_TAG}>" in content
        assert UNTRUSTED_REMINDER in content


def test_content_after_the_last_conclusion_is_untouched():
    messages = thread_with_conclusion()

    compacted = compact_thread(messages)

    # The current control still needs its bytes.
    assert compacted[-1].content == messages[-1].content


def test_think_and_conclude_results_are_never_compacted():
    messages = thread_with_conclusion()
    compacted = compact_thread(messages)

    assert compacted[4].content == messages[4].content
    assert compacted[6].content == messages[6].content


def test_a_thread_with_no_conclusion_is_returned_unchanged():
    messages = [
        human(),
        ai_tool_call("get_file_content", {"path": "a.ts"}, "f1"),
        tool_result("get_file_content", "f1", wrapped_file()),
    ]

    compacted = compact_thread(messages)

    assert [m.content for m in compacted] == [m.content for m in messages]


def test_short_results_are_left_alone():
    """Below the threshold a result is a refusal or an error string, not repo bytes."""
    short = "BUDGET REFUSED — this get_file_content call did NOT run."
    assert len(short) < MIN_COMPACT_CHARS
    messages = [
        human(),
        ai_tool_call("get_file_content", {"path": "a.ts"}, "f1"),
        tool_result("get_file_content", "f1", short),
        ai_tool_call("conclude_evidence", {}, "c1"),
        tool_result("conclude_evidence", "c1", "{}"),
    ]

    assert compact_thread(messages)[2].content == short


def test_empty_thread_is_handled():
    assert compact_thread([]) == []
    assert compact_thread(None) == []
