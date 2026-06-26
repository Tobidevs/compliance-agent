import { type ControlValidation } from "@/lib/types";
import { type ResultMetrics } from "@/lib/compliance-theme";

/* ============================================================
   Report export helpers. CSV is generated client-side and
   downloaded; PDF reuses the browser's print-to-PDF on a print
   stylesheet; copy summary writes a short digest to the clipboard.
   ============================================================ */

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function csvEscape(value: unknown) {
  return `"${String(value == null ? "" : value).replace(/"/g, '""')}"`;
}

export function exportResultsCsv(results: ControlValidation[], repo: string) {
  const head = [
    "regulation_id",
    "title",
    "status",
    "severity",
    "confidence",
    "confidence_label",
    "findings",
    "overall_reasoning",
  ];
  const body = results.map((c) =>
    [
      c.regulation_id,
      c.title,
      c.status,
      c.severity ?? "",
      `${Math.round(c.confidence * 100)}%`,
      c.confidence_label,
      c.findings.map((f) => `${f.type}: ${f.description}`).join(" | "),
      c.overall_reasoning,
    ]
      .map(csvEscape)
      .join(","),
  );
  const csv = [head.join(","), ...body].join("\n");
  const safeRepo = repo.replace(/[^a-z0-9._-]+/gi, "-") || "review";
  triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), `${safeRepo}-validation.csv`);
}

export function exportPdf() {
  // The print stylesheet in globals.css collapses the app chrome and prints
  // the results document; the user picks "Save as PDF" in the print dialog.
  window.print();
}

export async function copySummary(metrics: ResultMetrics, repo: string) {
  const text =
    `Compliance validation — ${repo}\n` +
    `Posture ${Math.round(metrics.posture)} / 100 · ` +
    `Coverage ${Math.round(metrics.coverage)}% · ` +
    `Avg confidence ${Math.round(metrics.confidence)}% · ` +
    `${metrics.total} controls\n` +
    `Pass ${metrics.status.PASS} · Partial ${metrics.status.PARTIAL} · ` +
    `Fail ${metrics.status.FAIL} · No evidence ${metrics.status.NO_EVIDENCE}`;
  try {
    if (navigator.clipboard) await navigator.clipboard.writeText(text);
  } catch {
    /* clipboard unavailable — silent no-op */
  }
}
