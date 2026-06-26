/* ============================================================
   Intake option lists — must match the backend exactly.
   The backend filters control retrieval with `category $eq`, so a
   mismatch in these strings returns zero controls. Do not edit the
   values without changing the backend control set in lockstep.
   ============================================================ */

export const FRAMEWORKS = ["SOC2&GDPR"];

export const CATEGORIES = ["Category A", "Category B", "Category C"];

export const SCOPE_OPTIONS = [
  "Logical and Physical Access Controls",
  "System Operations",
  "Change Management",
  "Risk Mitigation",
  "Availability",
  "Processing Integrity",
  "Data Processing Principles",
  "Privacy by Design and Default",
  "Security of Processing",
  "Data Subject Rights",
  "Breach Notification",
  "PII Handling and Logging",
];

export const fmtFramework = (v: string) => (v === "SOC2&GDPR" ? "SOC 2 & GDPR" : v || "SOC 2");
