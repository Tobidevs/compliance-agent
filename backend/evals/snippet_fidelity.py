"""
Snippet Fidelity scorer for the validation subagent.

A deterministic (non-LLM) scorer that checks every snippet the validator cited in a finding's
`evidence_ref` is a VERBATIM excerpt of the evidence it was given — i.e. it copied, not
paraphrased or hallucinated. VALIDATION_SUBAGENT_SYSTEM_PROMPT requires each `evidence_ref.snippet`
to be an exact excerpt (<=200 chars) of the evidence `code_snippets`; this scorer measures the
fraction of cited snippets that actually appear in the provided evidence.

Findings legitimately without a snippet (NO_EVIDENCE gaps, where `evidence_ref` is null) are not
counted either way. A batch with no cited snippets at all scores None (nothing to verify), which
Braintrust omits from aggregation. Comparison collapses runs of whitespace on both sides so that
reformatted indentation is not treated as a mismatch, while paraphrases and fabrications still fail.
"""

import re

from autoevals import Score


def _normalize(text: str) -> str:
    """Collapse all whitespace runs to single spaces so indentation/newline reflow does not cause
    a spurious mismatch; content and ordering must still match to count as verbatim."""
    return re.sub(r"\s+", " ", text or "").strip()


def snippet_fidelity(input=None, output=None, **kwargs) -> Score:
    input = input or {}
    output = output or {}

    # Union of every evidence snippet the validator was given, normalized once. Matching against
    # the whole batch (not per-control) scopes this strictly to fabrication: a snippet is faithful
    # if it appears verbatim ANYWHERE in the evidence. Cross-control misattribution is a verdict
    # concern that the ValidationCorrectness judge covers, not a fidelity concern.
    evidence_pool = [
        _normalize(s)
        for e in input.get("evidence", [])
        for s in e.get("code_snippets", [])
    ]

    matched = 0
    total = 0
    mismatches = []
    for v in output.get("validations", []):
        for finding in v.get("findings", []):
            ref = finding.get("evidence_ref")
            snippet = ref.get("snippet") if isinstance(ref, dict) else None
            if not snippet:
                continue
            total += 1
            needle = _normalize(snippet)
            if any(needle in hay for hay in evidence_pool):
                matched += 1
            else:
                mismatches.append(
                    {"regulation_id": v.get("regulation_id"), "snippet": snippet}
                )

    if total == 0:
        return Score(
            name="SnippetFidelity",
            score=None,
            metadata={"matched": 0, "total": 0, "note": "no cited snippets to verify"},
        )

    return Score(
        name="SnippetFidelity",
        score=matched / total,
        metadata={"matched": matched, "total": total, "mismatches": mismatches},
    )
