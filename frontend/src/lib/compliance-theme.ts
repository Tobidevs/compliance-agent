import { type ControlValidation, type ValidationFinding } from "@/lib/utils";

/* ============================================================
   Shared metadata + helpers for the compliance UI.
   Single source of truth for status / severity / finding colors,
   ordering, formatting, and the running-workflow steps.
   ============================================================ */

export type StatusKey = ControlValidation["status"];
export type SeverityKey = NonNullable<ControlValidation["severity"]>;
export type FindingKey = ValidationFinding["type"];

type StatusTone = { label: string; color: string; fill: string; bg: string; line: string };

export const STATUS_META: Record<StatusKey, StatusTone> = {
  PASS:        { label: "Pass",        color: "var(--pass)",    fill: "var(--pass-vivid)",    bg: "var(--pass-bg)",    line: "var(--pass-line)" },
  PARTIAL:     { label: "Partial",     color: "var(--partial)", fill: "var(--partial-vivid)", bg: "var(--partial-bg)", line: "var(--partial-line)" },
  FAIL:        { label: "Fail",        color: "var(--fail)",    fill: "var(--fail-vivid)",    bg: "var(--fail-bg)",    line: "var(--fail-line)" },
  NO_EVIDENCE: { label: "No evidence", color: "var(--noev)",    fill: "var(--noev-vivid)",    bg: "var(--noev-bg)",    line: "var(--noev-line)" },
};

export const SEVERITY_COLOR: Record<SeverityKey, string> = {
  critical: "var(--sev-critical)",
  high: "var(--sev-high)",
  medium: "var(--sev-medium)",
  low: "var(--sev-low)",
};

type FindingTone = { label: string; color: string; bg: string; line: string };
export const FINDING_META: Record<FindingKey, FindingTone> = {
  violation: { label: "Violation", color: "var(--fail)",    bg: "var(--fail-bg)",    line: "var(--fail-line)" },
  gap:       { label: "Gap",       color: "var(--partial)", bg: "var(--partial-bg)", line: "var(--partial-line)" },
  pass:      { label: "Pass",      color: "var(--pass)",    bg: "var(--pass-bg)",    line: "var(--pass-line)" },
};

/* Vivid fills for the findings-composition bars */
export const FINDING_FILL: Record<FindingKey, string> = {
  violation: "var(--fail-vivid)",
  gap: "var(--partial-vivid)",
  pass: "var(--pass-vivid)",
};

export const STATUS_ORDER: Record<StatusKey, number> = {
  FAIL: 0,
  PARTIAL: 1,
  NO_EVIDENCE: 2,
  PASS: 3,
};

export const SEVERITY_ORDER: Record<SeverityKey, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export const WORKFLOW_STEPS = [
  { key: "clone", label: "Cloning repository", detail: "Fetching source tree and history" },
  { key: "scope", label: "Resolving control scope", detail: "Mapping selected categories to SOC 2 controls" },
  { key: "scan", label: "Scanning source evidence", detail: "Indexing configuration, IaC, and workflows" },
  { key: "validate", label: "Validating controls", detail: "Reasoning over evidence per control" },
  { key: "compose", label: "Composing report", detail: "Scoring posture and assembling findings" },
] as const;

export const pct = (v: number) => `${Math.round(v)}%`;
export const pct1 = (v: number) => `${v.toFixed(v % 1 === 0 ? 0 : 1)}%`;
export const clamp = (v: number, min = 0, max = 100) => Math.min(max, Math.max(min, v));

export function getControlKey(control: ControlValidation) {
  return `${control.regulation_id}::${control.title}`;
}

export function sortValidationResults(results: ControlValidation[]) {
  return [...results].sort((left, right) => {
    const statusDifference = STATUS_ORDER[left.status] - STATUS_ORDER[right.status];
    if (statusDifference !== 0) return statusDifference;
    const leftSeverity = left.severity && left.severity in SEVERITY_ORDER ? SEVERITY_ORDER[left.severity] : Number.MAX_SAFE_INTEGER;
    const rightSeverity = right.severity && right.severity in SEVERITY_ORDER ? SEVERITY_ORDER[right.severity] : Number.MAX_SAFE_INTEGER;
    if (leftSeverity !== rightSeverity) return leftSeverity - rightSeverity;
    return right.confidence - left.confidence;
  });
}

/* Aggregate metrics for the dashboard. */
export type ResultMetrics = ReturnType<typeof computeMetrics>;
export function computeMetrics(results: ControlValidation[]) {
  const sorted = sortValidationResults(results);
  const total = sorted.length;
  const status: Record<StatusKey, number> = { PASS: 0, PARTIAL: 0, FAIL: 0, NO_EVIDENCE: 0 };
  const severity: Record<SeverityKey, number> = { critical: 0, high: 0, medium: 0, low: 0 };
  const findings: Record<FindingKey, number> = { violation: 0, gap: 0, pass: 0 };
  sorted.forEach((c) => {
    status[c.status]++;
    if (c.severity) severity[c.severity]++;
    c.findings.forEach((f) => findings[f.type]++);
  });
  const posture = total ? ((status.PASS + status.PARTIAL * 0.5) / total) * 100 : 0;
  const coverage = total ? ((total - status.NO_EVIDENCE) / total) * 100 : 0;
  const confidence = total ? (sorted.reduce((s, c) => s + c.confidence, 0) / total) * 100 : 0;
  const sevTotal = severity.critical + severity.high + severity.medium + severity.low;
  const findTotal = findings.violation + findings.gap + findings.pass;
  const statusSegments = (["FAIL", "PARTIAL", "NO_EVIDENCE", "PASS"] as StatusKey[]).map((label) => ({
    label, count: status[label], color: STATUS_META[label].fill,
  }));
  return { sorted, total, status, severity, findings, posture, coverage, confidence, sevTotal, findTotal, statusSegments };
}
