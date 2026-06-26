"use client";

import { FINDING_META, SEVERITY_COLOR, STATUS_META, pct } from "@/lib/compliance-theme";
import { type ControlValidation } from "@/lib/types";

/* Detail panel for the selected control: status, confidence, overall
   reasoning, and each finding with its evidence snippet. */
export function ControlDetail({ control }: { control: ControlValidation | null }) {
  if (!control) {
    return (
      <div style={{ padding: "48px 0", textAlign: "center", color: "var(--ink-4)", fontSize: 14 }}>
        Select a control to inspect its reasoning and evidence.
      </div>
    );
  }

  const meta = STATUS_META[control.status];

  return (
    <div key={`${control.regulation_id}::${control.title}`} className="anim-fade-in">
      <div style={{ display: "flex", alignItems: "center", gap: 11, flexWrap: "wrap" }}>
        <span
          className="mono"
          style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em", color: "var(--ink)" }}
        >
          {control.regulation_id}
        </span>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: "3px 10px",
            borderRadius: "var(--r-pill)",
            border: `1px solid ${meta.line}`,
            background: meta.bg,
            color: meta.color,
            fontFamily: "var(--font-mono)",
            fontSize: 10.5,
            fontWeight: 500,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
          }}
        >
          <span style={{ width: 6, height: 6, borderRadius: 999, background: meta.color }} />
          {meta.label}
        </span>
        {control.severity ? (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "2px 9px",
              borderRadius: "var(--r-pill)",
              border: `1px solid ${SEVERITY_COLOR[control.severity]}44`,
              background: `${SEVERITY_COLOR[control.severity]}1f`,
              color: SEVERITY_COLOR[control.severity],
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              fontWeight: 500,
              letterSpacing: "0.05em",
              textTransform: "capitalize",
            }}
          >
            {control.severity}
          </span>
        ) : null}
      </div>

      <p style={{ margin: "13px 0 0", fontSize: 14.5, lineHeight: 1.5, color: "var(--ink)", fontWeight: 500 }}>
        {control.title}
      </p>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginTop: 16,
          padding: "12px 14px",
          borderRadius: "var(--r-sm)",
          background: "var(--paper-2)",
          border: "1px solid var(--line)",
        }}
      >
        <span
          className="mono"
          style={{ fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--ink-4)" }}
        >
          Confidence
        </span>
        <div style={{ flex: 1, height: 6, background: "var(--paper-3)", borderRadius: 999, overflow: "hidden" }}>
          <div
            style={{
              height: "100%",
              width: `${control.confidence * 100}%`,
              background: meta.fill,
              borderRadius: 999,
            }}
          />
        </div>
        <span
          className="mono tnum"
          style={{ fontSize: 12.5, fontWeight: 500, color: "var(--ink-2)" }}
        >
          {pct(control.confidence * 100)}
        </span>
      </div>

      <div style={{ height: 1, background: "var(--line)", margin: "20px 0" }} />

      <p
        className="mono"
        style={{ margin: 0, fontSize: 10, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--ink-4)" }}
      >
        Overall reasoning
      </p>
      <p style={{ margin: "10px 0 0", fontSize: 13.5, lineHeight: 1.65, color: "var(--ink-2)" }}>
        {control.overall_reasoning}
      </p>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", margin: "22px 0 14px" }}>
        <p
          className="mono"
          style={{
            margin: 0,
            fontSize: 10,
            letterSpacing: "0.16em",
            textTransform: "uppercase",
            color: "var(--ink-4)",
          }}
        >
          Findings
        </p>
        <span style={{ fontSize: 12, color: "var(--ink-4)" }}>{control.findings.length} total</span>
      </div>

      <div style={{ display: "grid", gap: 16 }}>
        {control.findings.map((f, i) => {
          const fm = FINDING_META[f.type] ?? FINDING_META.gap;
          return (
            <div
              key={i}
              style={{
                display: "grid",
                gap: 10,
                paddingBottom: 16,
                borderBottom: i < control.findings.length - 1 ? "1px solid var(--line)" : "none",
              }}
            >
              <div style={{ display: "flex", alignItems: "flex-start", gap: 10, flexWrap: "wrap" }}>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    padding: "2px 9px",
                    borderRadius: "var(--r-pill)",
                    border: `1px solid ${fm.line}`,
                    background: fm.bg,
                    color: fm.color,
                    fontFamily: "var(--font-mono)",
                    fontSize: 10,
                    fontWeight: 500,
                    letterSpacing: "0.05em",
                    textTransform: "uppercase",
                  }}
                >
                  {fm.label}
                </span>
                <p
                  style={{
                    margin: 0,
                    fontSize: 13.5,
                    fontWeight: 500,
                    lineHeight: 1.5,
                    color: "var(--ink)",
                    flex: 1,
                    minWidth: 160,
                  }}
                >
                  {f.description}
                </p>
              </div>
              {f.evidence_ref && f.evidence_ref.snippet ? (
                <div
                  style={{
                    borderLeft: "2px solid var(--brand)",
                    background: "var(--paper-2)",
                    borderRadius: "0 var(--r-xs) var(--r-xs) 0",
                    padding: "9px 13px",
                  }}
                >
                  <span
                    className="mono"
                    style={{ fontSize: 11.5, lineHeight: 1.6, color: "var(--ink-2)", wordBreak: "break-word" }}
                  >
                    {f.evidence_ref.snippet}
                  </span>
                </div>
              ) : null}
              <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.6, color: "var(--ink-3)" }}>{f.reasoning}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
