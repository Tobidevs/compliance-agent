"""
Shared dataset + task infrastructure for the validation-subagent evals.

Unlike the evidence-subagent evals (which run a tool-using subgraph over a real repo), the
validation subagent is a single structured-output LLM call: it takes a batch of controls plus
the evidence gathered upstream and emits one `ControlValidation` per control (status, severity,
confidence, findings, points-of-focus assessments, reasoning). To grade its correctness in
isolation — independently of the nondeterministic evidence-gathering step — this module feeds
it HAND-AUTHORED evidence fixtures (a clear PASS, a FAIL, a NO_EVIDENCE, and a PARTIAL batch)
rather than retrieving controls from Pinecone or scanning GitHub.

Each fixture becomes one `EvalCase`; the `task` runs the validator once and returns both a
human-readable transcript (evidence in / verdicts out) for the LLM-judge scorer and the raw
validations for the deterministic snippet-fidelity scorer. Two scorers grade that one run:
  - ValidationCorrectness — is each verdict justified by the evidence? (validation_correctness.py)
  - SnippetFidelity       — are cited snippets verbatim excerpts of the evidence? (snippet_fidelity.py)
"""

import json
import os

from braintrust import EvalCase
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from agent.prompts import VALIDATION_SUBAGENT_SYSTEM_PROMPT
from agent.state import EvidenceResult, ValidationBatch
from agent.utils.agent_utils import _build_validation_user_message

load_dotenv()

FRAMEWORK = "SOC2&GDPR"
CATEGORY = "Logical and Physical Access Controls"

# Mirror nodes.py's validator wiring exactly (same env var + default + structured output) so
# the eval exercises the real model path without importing agent.nodes (which would pull in
# Pinecone / GitHub MCP init that these fixture-only cases do not need).
validation_model = init_chat_model(
    model=os.getenv("VALIDATION_SUBAGENT_MODEL", "anthropic:claude-sonnet-4-6")
)
compliance_validation_model = validation_model.with_structured_output(ValidationBatch)


# ---------------------------------------------------------------------------
# Fixtures: hand-authored evidence scenarios (one batch per EvalCase)
# ---------------------------------------------------------------------------
# Each case is a batch of controls; every control carries its own pre-gathered evidence, shaped
# exactly like the EvidenceResult the real evidence subagent produces. `intended_status` is a
# human-readable note of the verdict a correct validator should reach — it is NOT gold used by
# any scorer (grading is reference-free), only documentation of what the fixture is testing.
VALIDATION_CASES = [
    {
        "case_id": "clear_pass",
        "intended_status": "PASS",
        "evidence": [
            {
                "regulation_id": "CC6.1.1",
                "title": "Logical Access — Authentication Enforcement",
                "requirement": "The entity restricts logical access to information assets by requiring users to authenticate before access is granted.",
                "files_searched": ["src/middleware/auth.ts", "src/app/api/route.ts"],
                "code_snippets": [
                    "export async function requireAuth(req: Request) {\n  const session = await getSession(req);\n  if (!session?.userId) {\n    throw new UnauthorizedError('Authentication required');\n  }\n  return session;\n}",
                    "export const GET = withAuth(async (req) => {\n  const session = await requireAuth(req);\n  return json(await listResources(session.userId));\n});",
                ],
                "description": "API routes are wrapped in withAuth and call requireAuth, which rejects unauthenticated requests before any resource access.",
                "no_evidence_found": False,
                "points_of_focus_coverage": [
                    {"point_of_focus": "Restricts logical access to information assets", "coverage": "satisfied"},
                    {"point_of_focus": "Authenticates users prior to granting access", "coverage": "satisfied"},
                    {"point_of_focus": "Manages credential lifecycle", "coverage": "partial"},
                ],
            }
        ],
    },
    {
        "case_id": "clear_fail",
        "intended_status": "FAIL",
        "evidence": [
            {
                "regulation_id": "CC6.1.2",
                "title": "Logical Access — Credential Protection",
                "requirement": "The entity protects authentication credentials and secrets against unauthorized disclosure and does not embed them in source code.",
                "files_searched": ["src/lib/api-client.ts"],
                "code_snippets": [
                    "const API_KEY = 'sk-live-9f2c4b7a1e0d6h3k';\nexport const client = new PaymentClient({ apiKey: API_KEY });",
                    "// TODO: move to env before launch\nconst DB_PASSWORD = 'prod_admin_2023';",
                ],
                "description": "A live payment API key and a production database password are hardcoded directly in the committed source.",
                "no_evidence_found": False,
                "points_of_focus_coverage": [
                    {"point_of_focus": "Protects credentials from unauthorized disclosure", "coverage": "absent"},
                    {"point_of_focus": "Stores secrets outside source control", "coverage": "absent"},
                ],
            }
        ],
    },
    {
        "case_id": "no_evidence",
        "intended_status": "NO_EVIDENCE",
        "evidence": [
            {
                "regulation_id": "CC6.6.1",
                "title": "Physical Access — Datacenter Controls",
                "requirement": "The entity restricts physical access to facilities and information assets to authorized personnel.",
                "files_searched": [],
                "code_snippets": [],
                "description": "No source-code evidence relates to physical datacenter access controls; this is typically enforced by the hosting provider.",
                "no_evidence_found": True,
                "points_of_focus_coverage": [
                    {"point_of_focus": "Restricts physical access to authorized personnel", "coverage": "absent"},
                ],
            }
        ],
    },
    {
        "case_id": "partial_batch",
        "intended_status": "PARTIAL (first control), PASS or PARTIAL (second control)",
        "evidence": [
            {
                "regulation_id": "CC6.2.1",
                "title": "Access Provisioning and Deprovisioning",
                "requirement": "The entity registers and authorizes new users before granting access, and removes access when it is no longer required.",
                "files_searched": ["src/lib/rbac.ts", "src/actions/invite.ts"],
                "code_snippets": [
                    "export async function inviteUser(email: string, role: Role) {\n  await requireRole('admin');\n  return db.invitations.create({ email, role, status: 'pending' });\n}",
                ],
                "description": "New-user provisioning is gated behind an admin role check, but no code was found that revokes or deprovisions access when a user is removed.",
                "no_evidence_found": False,
                "points_of_focus_coverage": [
                    {"point_of_focus": "Authorizes new users before granting access", "coverage": "satisfied"},
                    {"point_of_focus": "Removes access when no longer required", "coverage": "absent"},
                ],
            },
            {
                "regulation_id": "CC6.3.1",
                "title": "Role-Based Access Enforcement",
                "requirement": "The entity restricts access to data and functionality based on defined roles and least privilege.",
                "files_searched": ["src/lib/rbac.ts"],
                "code_snippets": [
                    "export function requireRole(required: Role) {\n  const role = getCurrentRole();\n  if (!ROLE_HIERARCHY[role].includes(required)) {\n    throw new ForbiddenError();\n  }\n}",
                ],
                "description": "A role hierarchy check enforces least-privilege access on protected operations.",
                "no_evidence_found": False,
                "points_of_focus_coverage": [
                    {"point_of_focus": "Restricts access based on defined roles", "coverage": "satisfied"},
                    {"point_of_focus": "Enforces least privilege", "coverage": "satisfied"},
                ],
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Dataset generation: one EvalCase per fixture batch
# ---------------------------------------------------------------------------
def _controls_from_evidence(evidence: list[dict]) -> list[dict]:
    """Derive the control list the validator user-message expects from the evidence batch.

    The validator reads control identity from the evidence items themselves; `controls` only
    drives the batch count in the user message, so we mirror the evidence one-to-one."""
    return [
        {
            "regulation_id": e["regulation_id"],
            "title": e["title"],
            "requirement": e["requirement"],
        }
        for e in evidence
    ]


def build_validation_dataset() -> list[EvalCase]:
    """Return one EvalCase per fixture batch. Fully local — no Pinecone or GitHub calls."""
    cases = []
    for fixture in VALIDATION_CASES:
        evidence = fixture["evidence"]
        cases.append(
            EvalCase(
                input={
                    "case_id": fixture["case_id"],
                    "framework": FRAMEWORK,
                    "category": CATEGORY,
                    "controls": _controls_from_evidence(evidence),
                    "evidence": evidence,
                },
                metadata={
                    "case_id": fixture["case_id"],
                    "intended_status": fixture["intended_status"],
                    "num_controls": len(evidence),
                    "framework": FRAMEWORK,
                    "category": CATEGORY,
                },
            )
        )
    return cases


# ---------------------------------------------------------------------------
# Task: run ONE validation subagent over the fixture batch
# ---------------------------------------------------------------------------
def _invoke_validator(messages) -> ValidationBatch:
    """Mirror nodes.invoke_validation_subagent's model call + JSON fallback, minus the stream
    writer (which requires a live LangGraph run context that the eval does not provide)."""
    raw_response = compliance_validation_model.invoke(messages)
    if isinstance(raw_response, ValidationBatch):
        return raw_response
    content = raw_response.content if hasattr(raw_response, "content") else str(raw_response)
    parsed = json.loads(content)
    if isinstance(parsed, list):
        parsed = {"validations": parsed}
    if isinstance(parsed, dict) and isinstance(parsed.get("validations"), str):
        parsed["validations"] = json.loads(parsed["validations"])
    return ValidationBatch.model_validate(parsed)


def _serialize_evidence_block(evidence: list[dict]) -> str:
    blocks = []
    for e in evidence:
        pof = "\n".join(
            f'      - "{p["point_of_focus"]}": {p["coverage"]}'
            for p in e.get("points_of_focus_coverage", [])
        )
        snippets = "\n".join(f"      ```\n{s}\n      ```" for s in e.get("code_snippets", []))
        blocks.append(
            f"### Control {e['regulation_id']} — {e['title']}\n"
            f"Requirement: {e['requirement']}\n"
            f"no_evidence_found: {e['no_evidence_found']}\n"
            f"Files searched: {e.get('files_searched', [])}\n"
            f"Points of focus coverage:\n{pof or '      (none)'}\n"
            f"Code snippets:\n{snippets or '      (none)'}"
        )
    return "\n\n".join(blocks)


def _serialize_validations_block(validations) -> str:
    blocks = []
    for v in validations:
        findings = []
        for f in v.findings:
            snippet = f.evidence_ref.snippet if f.evidence_ref else None
            findings.append(
                f"    - [{f.type}] {f.description}\n"
                f"      evidence_ref.snippet: {json.dumps(snippet)}\n"
                f"      reasoning: {f.reasoning}"
            )
        pof = "\n".join(
            f'    - "{p.point_of_focus}": {p.status} — {p.assessment}'
            for p in v.points_of_focus
        )
        blocks.append(
            f"### Control {v.regulation_id} — {v.title}\n"
            f"Status: {v.status}\n"
            f"Severity: {v.severity}\n"
            f"Confidence: {v.confidence} ({v.confidence_label})\n"
            f"Findings:\n" + "\n".join(findings) + "\n"
            f"Points of focus:\n{pof or '    (none)'}\n"
            f"Overall reasoning: {v.overall_reasoning}"
        )
    return "\n\n".join(blocks)


def serialize_transcript(input: dict, batch: ValidationBatch) -> str:
    """Render the evidence given to the validator and the verdicts it produced into a single
    auditable string the LLM judge grades via {{output.transcript}}."""
    return (
        f"FRAMEWORK: {input['framework']}\n"
        f"CATEGORY: {input['category']}\n"
        f"CONTROLS IN BATCH: {len(input['evidence'])}\n\n"
        f"## Evidence provided to the validator\n\n"
        f"{_serialize_evidence_block(input['evidence'])}\n\n"
        f"## Validator output\n\n"
        f"{_serialize_validations_block(batch.validations)}"
    )


def task(input) -> dict:
    evidence_items = [EvidenceResult(**e) for e in input["evidence"]]
    sub_input = {
        "cluster_id": input["category"],
        "controls": input["controls"],
        "evidence_items": evidence_items,
        "framework": input["framework"],
        "category": input["category"],
    }
    messages = [
        SystemMessage(content=VALIDATION_SUBAGENT_SYSTEM_PROMPT),
        HumanMessage(content=_build_validation_user_message(sub_input)),
    ]

    batch = _invoke_validator(messages)

    # Return both a transcript (for the LLM verdict judge) and the raw validations (for the
    # deterministic snippet-fidelity scorer, which needs structured access, not prose).
    return {
        "transcript": serialize_transcript(input, batch),
        "validations": [v.model_dump() for v in batch.validations],
    }
