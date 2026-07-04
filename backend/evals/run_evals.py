"""
Braintrust eval runner for the evidence subagent.

Runs ONE evidence subagent per case (see evals/common.py) and grades each run with two
reference-free LLM-judge scorers:
  - BudgetAdherence   — tool-call budget discipline and protocol (evals/budget_adherence.py)
  - EvidencePrecision — whether the agent searched the RIGHT files (evals/evidence_precision.py)

Run from the `backend/` directory:

    braintrust eval evals/run_evals.py
"""

from braintrust import Eval

from evals.common import build_dataset, task
from evals.budget_adherence import budget_adherence
from evals.evidence_precision import evidence_precision

Eval(
    "Compliance Agent",
    data=build_dataset,
    task=task,
    scores=[budget_adherence, evidence_precision],
    # Each evidence subagent makes many haiku calls over large transcripts. Run cases
    # serially to stay under the org's per-minute token rate limit; raise if your tier allows.
    max_concurrency=1,
)
