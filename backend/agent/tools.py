from langchain.tools import tool

from .state import EvidenceItem


def conclude_evidence(evidence_items: list[EvidenceItem]):
    """Call this ONCE you have completed ALL searching and evidence gathering for ALL controls. This signals that your evidence gathering process is finished and triggers the final output assembly."""

    normalized_items = []
    for item in evidence_items:
        if isinstance(item, EvidenceItem):
            normalized_items.append(item.model_dump())
        else:
            normalized_items.append(item)

    return {"evidence_items": normalized_items}


def think(
    evidence: str,
    code_snippets: list[str],
    finished: bool,
    fetches_remaining: int,
    tree_calls_remaining: int,
) -> dict:
    """
    Structured mid-loop checkpoint. Call this immediately after EVERY get_file_content call,
    before issuing any other tool call.

    Args:
        evidence: One or two factual sentences describing what this file contained
                or did not contain relative to the CURRENT control being investigated.
                Do not use compliant, non-compliant, violation, passes, fails,
                secure, insecure, adequate, inadequate.
        code_snippets: Exact verbatim code from the file relevant to the current control.
                        Preserve whitespace. Empty list if nothing relevant was found.
        finished: A boolean flag indicating whether the evidence gathering process for ALL controls is complete.
        fetches_remaining: An integer indicating how many more file fetches are allowed before concluding.
        tree_calls_remaining: An integer indicating how many more repository tree calls are allowed before concluding.
    """
    # No-op server-side. Forces the model to externalize and structure
    # its working memory after each fetch before context grows further.
    return {
        "status": "logged",
        "snippets_captured": len(code_snippets),
        "tree_calls_remaining": tree_calls_remaining,
        "fetches_remaining": fetches_remaining,
    }
