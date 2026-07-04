"""
Evidence Precision judge for the evidence subagent (Langfuse port).

The Langfuse-runner counterpart of `evals/evidence_precision.py` (Braintrust). It exposes a
single reference-free LLM-judge evaluator (`evidence_precision`) that grades whether the
subagent SEARCHED THE RIGHT FILES — i.e. of the files it chose to fetch/search, what fraction
were genuinely relevant to the assigned control(s). This is a PRECISION-only signal: it
penalizes fetching irrelevant/off-target files, and deliberately does NOT penalize missing
relevant files or narrow coverage (that is recall). It consumes the same serialized transcript
produced by `evals_langfuse.common.task` that the Budget Adherence judge grades.

The prompt and choice-score mapping are identical to the Braintrust judge; only the runner
changes — instead of `autoevals.LLMClassifier`, scoring goes through `common.llm_classify`,
and the evaluator returns a Langfuse `Evaluation`.
"""

from evals_langfuse.common import llm_classify

PRECISION_CHOICE_SCORES = {
    "precise": 1.0,         # every file fetched/searched was a well-justified, relevant target
    "mostly_precise": 0.7,  # one borderline/marginal fetch, otherwise on-target
    "mixed": 0.5,           # a meaningful share of fetches were off-target / weakly related
    "imprecise": 0.3,       # most fetches poorly targeted; little relevance to the control
    "misdirected": 0.0,     # searches essentially unrelated to the control(s)
}

EVIDENCE_PRECISION_PROMPT = """
You are a strict auditor of SEARCH PRECISION for one evidence-extraction subagent inside a
SOC 2 / GDPR compliance pipeline. You judge ONLY whether the files the agent chose to fetch
and search were RELEVANT to the compliance control(s) it was assigned. You do NOT judge
tool-call budget discipline, protocol/turn structure, or whether the final evidence
conclusion is correct.

The transcript below is the agent's COMPLETE message list, turn by turn. It begins with the
system prompt and the human message — which contains the ASSIGNED CONTROLS (each with its
requirement text and points of focus) and the repo ROOT FILE LISTING — followed by the
agent's turns. Tool calls appear as `-> tool_call: name({args})` and tool results appear as
`TOOL_RESULT <name>`. The relevant calls are:
- `get_file_content(path=...)` — fetches one file (or lists a directory). The fetched file
  content is shown in the following `TOOL_RESULT <get_file_content>`.
- `get_repository_tree(path_filter=...)` — explores a subdirectory's file tree.
- `conclude_evidence(...)` — its args include `files_searched`, the files the agent
  ultimately credited as evidence for that control.

## What PRECISION means here

Of the files the agent actually FETCHED and the directories it explored, what fraction were
plausibly relevant to the assigned control's requirement and points of focus, given the
repository's structure and file names?
- Weight ACTUAL FILE FETCHES (`get_file_content` on a file) most heavily — these are the
  agent's concrete targeting decisions. Inspect each fetched file's content and ask: was
  this a sensible place to look for evidence of THIS control?
- Treat directory / tree exploration (`get_repository_tree`, listing a folder) as fine when
  the folder plausibly leads to relevant files, even if a given branch turns up empty —
  reasonable exploration toward a relevant area is not an imprecision.
- An off-target fetch is one with no plausible connection to the control (e.g. fetching a
  README, a logo asset, or an unrelated config when investigating an access-control
  requirement, with no signal pointing there).

## Explicitly OUT OF SCOPE (do not penalize)

- Recall / completeness: do NOT penalize the agent for missing relevant files that exist,
  for narrow coverage, or for stopping early.
- Correctly setting `no_evidence_found=true` after a few on-target probes — rather than
  fetching unrelated files to fill the budget — is PRECISE behavior and should score well.
- Budget counts, think() usage, ordering, and whether the final pass/fail-style conclusion
  is right. Other judges cover those.

## Rubric — choose exactly ONE label

- `precise` (1.0): Every file fetched and directory explored was a well-justified, relevant
  target for the assigned control(s). Tight, on-target searching.
- `mostly_precise` (0.7): On-target overall, with at most one borderline or marginally
  relevant fetch.
- `mixed` (0.5): A meaningful share of fetches were off-target or only weakly related to the
  control, mixed in with relevant ones.
- `imprecise` (0.3): Most fetches were poorly targeted, with little relevance to the control.
- `misdirected` (0.0): The searches were essentially unrelated to the assigned control(s) —
  the agent looked in the wrong places throughout.

Reason file-by-file about each fetch before deciding. When multiple labels could apply, pick
the WORST (lowest-scoring) one that is justified by the transcript.

## Transcript to evaluate

{{output}}
""".strip()


def evidence_precision(*, output, **kwargs):
    """Langfuse item-level evaluator: grade search precision from the transcript."""
    return llm_classify(
        name="EvidencePrecision",
        prompt_template=EVIDENCE_PRECISION_PROMPT,
        choice_scores=PRECISION_CHOICE_SCORES,
        output=output,
    )
