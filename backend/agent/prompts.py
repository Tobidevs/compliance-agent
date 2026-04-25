POLICY_EXTRACTION_PROMPT = """
Extract compliance-relevant statements from this policy document.
For each distinct claim output:
- topic: short label (human-readable only, not used for matching)
- strength: "explicit" | "implicit" | "absent"
- excerpt: exact sentence(s) from the policy. Null if absent.
- policy_assertion: one sentence describing what protection or control 
  the policy puts in place. 

  Rules for policy_assertion:
  - Describe the WHAT (what is protected or controlled), not the HOW or WHERE
  - No section references ("Section 7", "per §4.2")
  - No regulatory references ("GDPR", "SOC 2", "CC6.1")
  - No trigger conditions ("upon account deletion", "when requested")
  - No system-specific terms ("via account deletion", "using Lambda")

  Good: "Users have the right to request deletion of all their personal data."
  Bad:  "Section 7 establishes deletion standards triggered via account deletion 
         for GDPR compliance."

Policy excerpts:
{excerpts}

Return a JSON array only.
"""