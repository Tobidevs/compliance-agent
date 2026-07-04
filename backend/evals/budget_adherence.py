"""
Budget Adherence judge for the evidence subagent.

A single reference-free LLM-judge choice scorer (`BudgetAdherence`) that grades ONLY how
well the subagent stayed within its tool budgets and followed its operating protocol — not
whether the gathered evidence is correct. The budgets/protocol rules graded here are exactly
those enforced by EVIDENCE_SUBAGENT_SYSTEM_PROMPT in agent/prompts.py. It consumes the
serialized transcript produced by `evals.common.task`.
"""

from autoevals import LLMClassifier

CHOICE_SCORES = {
    "fully_adherent": 1.0,
    "minor_waste": 0.7,
    "moderate_waste": 0.5,
    "major_violation": 0.3,
    "severe_violation": 0.0,
}

BUDGET_ADHERENCE_PROMPT = """
You are a strict auditor of TOOL-CALL BUDGET DISCIPLINE for one evidence-extraction
subagent inside a SOC 2 compliance pipeline. You judge ONLY how well the agent stayed
within its tool budgets and followed its operating protocol. You do NOT judge whether
the gathered evidence is correct, complete, or compliant.

The transcript below is the agent's COMPLETE message list, turn by turn. It begins with
the system prompt (the rules) and the human message (the assigned controls and the repo
root file listing), followed by the agent's turns. Each agent turn may contain a
`think(...)` call and one or more search calls. Tool calls appear as
`-> tool_call: name({args})` and tool results appear as `TOOL_RESULT <name>`.

## Constraints the agent must obey (per this single subagent)

HARD LIMITS (breaching any of these is a severe violation):
- At most 5 `get_repository_tree` calls total, across all controls.
- At most 8 `get_file_content` calls total, across all controls.
- NEVER call `get_repository_tree` on the repository root: a path argument of "", "/",
  ".", or a path_filter that targets the root listing is forbidden. The root listing is
  already provided in the human message.
- Per control: at most 2 `get_repository_tree` calls and at most 3 `get_file_content` calls.
- Exactly one `conclude_evidence` call per assigned control (no control skipped, none
  concluded twice).
- Exactly one `finished_gathering_evidence` call, and only after every control has been
  concluded.

PROTOCOL (slips here are minor-to-moderate, not hard breaches):
- After the first turn, every search turn must include a `think(...)` call together with
  1-3 search tools in the SAME turn. `think()` is required every turn after the first.
- No more than 3 tool calls in a single turn.
- Controls are processed one at a time, in order. The agent should not interleave
  searches for multiple controls.

EFFICIENCY (waste, even when within limits):
- No duplicate or redundant fetches (re-fetching the same path, re-listing the same tree).
- Stop early when fetched files are clearly irrelevant; do not keep searching to prove
  absence after the per-control budget is reached.
- Do not exhaust the global budget on a single control.

## Rubric — choose exactly ONE label

- `fully_adherent` (1.0): All hard limits respected, full protocol compliance (think()
  every turn after the first, 1-3 tools/turn, one conclude per control, one finished
  call), and no wasted or redundant calls.
- `minor_waste` (0.7): Within ALL hard limits, but with at most one minor protocol slip
  OR one small redundant/unnecessary call. Essentially disciplined.
- `moderate_waste` (0.5): No hard limit breached, but the run is clearly wasteful or has
  multiple protocol slips (e.g., several missing think() turns, repeated redundant fetches,
  interleaving controls).
- `major_violation` (0.3): A per-control sub-cap was exceeded (>2 tree or >3 file on one
  control), OR there are repeated/serious protocol violations, OR the agent came right up
  against the global budget through wasteful behavior.
- `severe_violation` (0.0): Any HARD LIMIT was breached — global tree budget (>5) or file
  budget (>8) exceeded, `get_repository_tree` called on the root, a control left without
  exactly one `conclude_evidence`, or `finished_gathering_evidence` missing/duplicated/
  called before all controls concluded.

Count the calls carefully before deciding. When multiple labels could apply, pick the
WORST (lowest-scoring) one that is justified by the transcript.

## Transcript to evaluate

{{output}}
""".strip()

budget_adherence = LLMClassifier(
    name="BudgetAdherence",
    prompt_template=BUDGET_ADHERENCE_PROMPT,
    choice_scores=CHOICE_SCORES,
    model="gpt-4o",
    use_cot=True,
)
