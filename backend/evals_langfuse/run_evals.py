"""
Langfuse experiment runner for the evidence subagent.

The Langfuse-runner counterpart of `evals/run_evals.py` (Braintrust). Runs ONE evidence
subagent per case (see evals_langfuse/common.py) and grades each run with two reference-free
LLM-judge evaluators:
  - BudgetAdherence   — tool-call budget discipline and protocol (budget_adherence.py)
  - EvidencePrecision — whether the agent searched the RIGHT files (evidence_precision.py)

Item-level scores are attached to each item's trace; run-level averages are attached to the
experiment run. With a Langfuse-hosted dataset these would surface as a dataset run, but here
the data is local, so only traces + scores are tracked (see the Langfuse experiments docs).

Run from the `backend/` directory (with LANGFUSE_* + OPENAI_API_KEY in env / .env):

    python -m evals_langfuse.run_evals
"""

import asyncio

from dotenv import load_dotenv
from langfuse import Evaluation, get_client

from evals_langfuse.common import build_dataset, task
from evals_langfuse.budget_adherence import budget_adherence
from evals_langfuse.evidence_precision import evidence_precision

load_dotenv()


def _average(item_results, score_name):
    values = [
        evaluation.value
        for result in item_results
        for evaluation in result.evaluations
        if evaluation.name == score_name and evaluation.value is not None
    ]
    if not values:
        return None
    return sum(values) / len(values)


def avg_budget_adherence(*, item_results, **kwargs):
    avg = _average(item_results, "BudgetAdherence")
    return Evaluation(name="avg_BudgetAdherence", value=avg)


def avg_evidence_precision(*, item_results, **kwargs):
    avg = _average(item_results, "EvidencePrecision")
    return Evaluation(name="avg_EvidencePrecision", value=avg)


def main():
    langfuse = get_client()

    dataset = asyncio.run(build_dataset())

    result = langfuse.run_experiment(
        name="Compliance Agent",
        description="Evidence subagent — budget adherence + evidence precision judges",
        data=dataset,
        task=task,
        evaluators=[budget_adherence, evidence_precision],
        run_evaluators=[avg_budget_adherence, avg_evidence_precision],
        # Each evidence subagent makes many haiku calls over large transcripts. Run cases
        # serially to stay under the org's per-minute token rate limit; raise if your tier allows.
        max_concurrency=1,
    )

    print(result.format())
    langfuse.flush()


if __name__ == "__main__":
    main()
