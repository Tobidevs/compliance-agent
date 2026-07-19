"""
Braintrust eval runner for the agent subagents.

Defines two experiments under the "Compliance Agent" project:

Evidence subagent — runs ONE evidence subagent per case (see evals/common.py), graded by two
reference-free LLM-judge scorers:
  - BudgetAdherence   — tool-call budget discipline and protocol (evals/budget_adherence.py)
  - EvidencePrecision — whether the agent searched the RIGHT files (evals/evidence_precision.py)

Validation subagent — runs ONE validator per fixture batch (see evals/validation_common.py),
graded by:
  - ValidationCorrectness — is each verdict justified by the evidence? (evals/validation_correctness.py)
  - SnippetFidelity       — are cited snippets verbatim excerpts? (evals/snippet_fidelity.py)

Run from the `backend/` directory:

    braintrust eval evals/run_evals.py
"""

from braintrust import Eval

from evals.common import build_dataset, task
from evals.budget_adherence import budget_adherence
from evals.evidence_precision import evidence_precision
from evals.validation_common import build_validation_dataset, task as validation_task
from evals.validation_correctness import validation_correctness
from evals.snippet_fidelity import snippet_fidelity

Eval(
    "Compliance Agent",
    data=build_dataset,
    task=task,
    scores=[budget_adherence, evidence_precision],
    # Each evidence subagent makes many haiku calls over large transcripts. Run cases
    # serially to stay under the org's per-minute token rate limit; raise if your tier allows.
    max_concurrency=1,
    experiment_name="evidence_subagent",
)

Eval(
    "Compliance Agent",
    data=build_validation_dataset,
    task=validation_task,
    scores=[validation_correctness, snippet_fidelity],
    # One Sonnet structured-output call per fixture batch; kept serial for parity with the
    # evidence eval and to stay well under rate limits.
    max_concurrency=1,
    experiment_name="validation_subagent",
)
