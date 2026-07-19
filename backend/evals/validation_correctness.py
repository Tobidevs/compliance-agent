"""
Validation Correctness judge for the validation subagent.

A single reference-free LLM-judge choice scorer (`ValidationCorrectness`) that grades whether
each verdict the validator produced is JUSTIFIED BY THE EVIDENCE it was given — the right status
(PASS/FAIL/PARTIAL/NO_EVIDENCE), a severity consistent with that status, a calibrated confidence,
and findings of the correct type. The rules graded here are exactly those enforced by
VALIDATION_SUBAGENT_SYSTEM_PROMPT in agent/prompts.py. It does NOT check whether cited snippets
are verbatim (SnippetFidelity covers that). It consumes the transcript produced by
`evals.validation_common.task` (evidence in / verdicts out).
"""

from autoevals import LLMClassifier

CHOICE_SCORES = {
    "fully_justified": 1.0,      # every control's verdict follows from its evidence and the rules
    "mostly_justified": 0.7,     # one minor miscalibration (e.g. confidence band slightly off)
    "mixed": 0.5,                # a defensible verdict alongside a clearly unsupported one
    "poorly_justified": 0.3,     # most verdicts weakly supported or rule-violating
    "unjustified": 0.0,          # verdicts contradict the evidence / break the hard status rules
}

VALIDATION_CORRECTNESS_PROMPT = """
You are a strict auditor of VERDICT CORRECTNESS for one validation subagent inside a SOC 2 /
GDPR compliance pipeline. Evidence was gathered upstream; this agent's only job is to judge each
control against its pre-gathered evidence and emit a structured verdict. You judge ONLY whether
those verdicts are JUSTIFIED BY THE EVIDENCE and consistent with the rules below. You do NOT judge
whether the evidence itself is complete, nor whether cited snippets are copied verbatim (another
judge covers snippet fidelity).

The transcript has two parts: `## Evidence provided to the validator` (one block per control — its
requirement, `no_evidence_found` flag, points-of-focus coverage, and code snippets) and
`## Validator output` (the verdict per control — status, severity, confidence, findings, points of
focus, reasoning). Match each verdict to its evidence block by regulation id.

## Rules the validator must obey (per control)

STATUS (getting this wrong is the most serious error):
- NO_EVIDENCE is REQUIRED when `no_evidence_found` is true OR there are no code snippets. It must
  NOT be used when real snippets are present.
- PASS requires evidence that explicitly and directly demonstrates compliance.
- FAIL requires evidence that explicitly demonstrates non-compliance (e.g. a hardcoded secret,
  a disabled control).
- PARTIAL is for genuine mixed signals — some compliance shown, real gaps remain.
- The status must not contradict the evidence (e.g. PASS over evidence of a hardcoded credential,
  or FAIL when the snippet clearly satisfies the requirement, is a serious error).

SEVERITY:
- null for PASS and NO_EVIDENCE; a non-null level (critical/high/medium/low) for FAIL and PARTIAL.
- The chosen level should be defensible given the risk the gap represents.

CONFIDENCE:
- NO_EVIDENCE must be 0.0 with label Inconclusive.
- Otherwise the float and label should match evidence strength: High/0.85-1.00 for direct explicit
  evidence, Medium/0.60-0.84 for indirect or partial, Low/0.35-0.59 for limited/ambiguous,
  Inconclusive/0.00-0.34 for present-but-too-weak. Reward honest calibration; penalize a high
  confidence that the evidence does not support.

FINDINGS:
- At least one finding per control. PASS -> a "pass" finding citing the satisfying snippet;
  FAIL/PARTIAL -> a "violation" or "gap" finding with a snippet reference; NO_EVIDENCE -> exactly
  one "gap" finding stating no evidence was retrieved.

POINTS OF FOCUS:
- One assessment per point of focus, each status grounded in the raw evidence (satisfied/partial/
  absent/not_applicable), not merely echoing the upstream coverage label.

## Rubric — choose exactly ONE label

- `fully_justified` (1.0): Every control's status, severity, confidence, and findings follow from
  its evidence and obey the rules. Calibrated and well-reasoned throughout.
- `mostly_justified` (0.7): Verdicts correct, with at most one minor slip — e.g. a confidence a band
  off, or a debatable severity — no wrong status.
- `mixed` (0.5): At least one control is well-judged but another has a clearly unsupported verdict
  or a rule break (wrong severity nullity, findings-type mismatch).
- `poorly_justified` (0.3): Most verdicts are weakly supported, miscalibrated, or rule-violating.
- `unjustified` (0.0): A status directly contradicts the evidence, or a hard status rule is broken
  (NO_EVIDENCE misused, snippets present but marked NO_EVIDENCE, or vice versa).

Reason control-by-control before deciding. When multiple labels could apply, pick the WORST
(lowest-scoring) one justified by the transcript.

## Transcript to evaluate

{{output.transcript}}
""".strip()

validation_correctness = LLMClassifier(
    name="ValidationCorrectness",
    prompt_template=VALIDATION_CORRECTNESS_PROMPT,
    choice_scores=CHOICE_SCORES,
    model="gpt-4o",
    use_cot=True,
)
