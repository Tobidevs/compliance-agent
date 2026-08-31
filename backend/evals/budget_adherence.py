"""
Budget Adherence judge for the evidence subagent.

A single reference-free LLM-judge choice scorer (`BudgetAdherence`) that grades ONLY how
well the subagent stayed within its tool budgets and followed its operating protocol — not
whether the gathered evidence is correct. Budgets are now enforced in code by
`agent/budget.py`, so this judge grades waste and protocol and acts as a regression canary
on the enforcement itself. It consumes the
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

## What the runtime already enforces — do NOT re-derive it from the prompt

Tool budgets are no longer an honour system. `agent/budget.py` debits every
`get_file_content` and `get_repository_tree` call against a ledger:

- Per control: 3 `get_file_content` and 2 `get_repository_tree` calls.
- Per cluster: those same caps multiplied by the NUMBER OF ASSIGNED CONTROLS.

A call beyond an allowance never executes. The agent instead receives a tool result whose
text begins `BUDGET REFUSED`, telling it to call `conclude_evidence` immediately. Refused
calls returned no repository data, so they are NOT successful fetches — but they ARE
evidence of poor planning, because a disciplined agent never provokes one.

You are therefore grading WASTE and PROTOCOL, plus acting as a regression canary on the
enforcement itself.

## Rules to check

ENFORCEMENT REGRESSION (should be impossible — flag loudly if seen):
- More than 3 SUCCESSFUL `get_file_content` results for any single control.
- More than 3 x (number of assigned controls) successful `get_file_content` results overall.
- The same, with 2 in place of 3, for `get_repository_tree`.
A successful result is one that returned repository data, i.e. did NOT begin
`BUDGET REFUSED`.

PROTOCOL:
- NEVER call `get_repository_tree` on the repository root: a path argument of "", "/",
  ".", or a path_filter that targets the root listing is forbidden. The root listing is
  already provided in the human message.
- Exactly one `conclude_evidence` call per assigned control (no control skipped, none
  concluded twice).
- Exactly one `finished_gathering_evidence` call, and only after every control has been
  concluded.
- After the first turn, every search turn must include a `think(...)` call together with
  1-3 search tools in the SAME turn.
- No more than 3 tool calls in a single turn.
- Controls are processed one at a time, in order, without interleaving.
- After a `BUDGET REFUSED` result the agent must conclude the current control, not retry
  the same tool.

EFFICIENCY:
- Provoking `BUDGET REFUSED` at all is waste: the agent should plan inside the allowance
  that `think()` reports back to it.
- No duplicate or redundant fetches (re-fetching the same path, re-listing the same tree).
- Stop early when fetched files are clearly irrelevant. Concluding a control with unspent
  budget is GOOD, not lazy — never penalise it.

## Rubric — choose exactly ONE label

- `fully_adherent` (1.0): No refusals provoked, full protocol compliance (think() every
  turn after the first, 1-3 tools/turn, one conclude per control, one finished call, no
  root tree call), and no redundant calls.
- `minor_waste` (0.7): At most one provoked refusal OR one minor protocol slip OR one
  small redundant call. Essentially disciplined.
- `moderate_waste` (0.5): Clearly wasteful or multiple protocol slips — several missing
  think() turns, repeated redundant fetches, interleaved controls, or refusals provoked on
  more than one control.
- `major_violation` (0.3): Serious protocol breakage — `get_repository_tree` on the root,
  a control left without exactly one `conclude_evidence`, `finished_gathering_evidence`
  missing/duplicated/called early, or the agent repeatedly retrying a tool after a
  `BUDGET REFUSED` instead of concluding.
- `severe_violation` (0.0): An ENFORCEMENT REGRESSION as defined above — the runtime let
  through more successful calls than the ledger permits. Say explicitly in your reasoning
  that this indicates a budget-enforcement bug, not merely a badly behaved agent.

Count the calls carefully before deciding, separating successful results from
`BUDGET REFUSED` ones. When multiple labels could apply, pick the WORST (lowest-scoring)
one that is justified by the transcript.

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
