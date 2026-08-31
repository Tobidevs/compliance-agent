"""Bounded context for the evidence subagent's shared cluster thread.

One subagent walks up to 8 controls in a single growing thread, so a file fetched for
control 1 would otherwise be re-sent on every turn of controls 2-8. Once a control has
been concluded, its raw file bytes have already done their job: the `think` summaries and
the concluded `EvidenceResult` carry the findings forward, so the bytes are dropped.

Security note: compaction only ever removes untrusted repository content together with its
`wrap_untrusted` delimiters. It never unwraps content while keeping it.
"""

import re

# Tool results carrying raw repository bytes. `think` / `conclude_evidence` results are
# the summaries we are compacting *down to*, so they are always kept intact.
BULK_TOOL_NAMES = {"get_file_content", "get_repository_tree"}

# Below this, a result is a refusal or an error string, not repo bytes worth compacting.
MIN_COMPACT_CHARS = 200

_MAX_PATH_CHARS = 120
# Matches the header wrap_untrusted() emits; the path was already defanged when written.
_WRAPPED_HEADER = re.compile(r'^<(untrusted_[a-z_]+) path="([^"]*)">')


def _placeholder(content: str) -> str:
    match = _WRAPPED_HEADER.match(content)
    path = match.group(2)[:_MAX_PATH_CHARS] if match else ""
    location = f' of "{path}"' if path else ""
    return (
        f"[compacted: {len(content)} chars{location} were removed after the control they "
        "were fetched for was concluded. The relevant findings are in the think() "
        "summaries and the conclude_evidence result above.]"
    )


def _is_compactable(message, index: int, cutoff: int) -> bool:
    if index >= cutoff:
        return False
    if getattr(message, "type", None) != "tool":
        return False
    if getattr(message, "name", None) not in BULK_TOOL_NAMES:
        return False
    content = getattr(message, "content", None)
    return isinstance(content, str) and len(content) >= MIN_COMPACT_CHARS


def compact_thread(messages: list) -> list:
    """Return the thread with pre-conclusion file bytes replaced by a one-line pointer.

    The ToolMessage itself is kept so every tool_use block still has its matching
    tool_result — deleting it outright would make the provider reject the request.
    """
    cutoff = -1
    for index, message in enumerate(messages or []):
        if (
            getattr(message, "type", None) == "tool"
            and getattr(message, "name", None) == "conclude_evidence"
        ):
            cutoff = index

    if cutoff < 0:
        return list(messages or [])

    compacted = []
    for index, message in enumerate(messages):
        if _is_compactable(message, index, cutoff):
            compacted.append(
                message.model_copy(update={"content": _placeholder(message.content)})
            )
        else:
            compacted.append(message)
    return compacted
