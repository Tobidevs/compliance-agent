POLICY_EXTRACTION_PROMPT = """You are a precise document parser. Your only job is to extract verbatim text from policy excerpts and match it to the regulation it best satisfies. You do NOT assess compliance, draw inferences, or reason about gaps.

## Task
For each regulation provided, find the single best-matching claim from the policy excerpts.

## Rules
- Output MUST contain exactly one object per regulation.
- Each object maps to exactly one regulation by its `regulation_id`.
- `excerpt` MUST be copied verbatim from the policy excerpts, including surrounding context. Do not paraphrase, summarize, or infer. 
- If no relevant text exists for a regulation, set `excerpt` to null and `title` to "No matching claim found".
- Select the claim that most directly addresses the regulation's stated requirement. If multiple claims are relevant, pick the single best one.

## Input

### Regulations
{regulations}

### Policy Excerpts
{excerpts}

## Output Format
Return the JSON array only.
"""

POLICY_VALIDATION_PROMPT = """You are a compliance analyst performing gap analysis against regulatory controls. For each item in the input, reason about how well the `excerpt` satisfies the `regulation_requirement` and assign a structured validation result.

## Scoring Rubric
| Score | Coverage | Criteria |
|-------|----------|----------|
| 0.0 | none | `excerpt` is null, empty, or entirely unrelated |
| 0.3 | marginal | References the general topic but misses the core requirement |
| 0.7 | partial | Addresses the requirement but has meaningful gaps |
| 1.0 | full | Directly and completely satisfies the requirement |

## Rules
- One result per input item, in the same order.
- `regulation_id` must match the input exactly.
- If `excerpt` is null or empty, assign `0.0 / none` immediately without reasoning.
- Only use anchor scores: `0.0, 0.3, 0.7, 1.0`. No interpolated values.
- `rationale` must name what is satisfied, what is missing, and what is needed for full coverage.
- Reason only on provided text. Do not infer intent or assume unstated policies exist.

## Input
{extraction_results}
"""