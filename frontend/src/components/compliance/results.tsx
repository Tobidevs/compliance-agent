"use client";

import * as React from "react";
import { Icon } from "./Icon";
import { StatusBadge, SeverityBadge, FindingBadge, Tag, Progress, Sep, SectionLabel } from "./primitives";
import { PostureGauge, ConfidenceRing, StatusDonut } from "./charts";
import {
  STATUS_META, SEVERITY_COLOR, FINDING_FILL,
  pct, pct1, getControlKey,
  type ResultMetrics, type SeverityKey, type FindingKey,
} from "@/lib/compliance-theme";
import { type ControlValidation } from "@/lib/utils";

/* ---------- ResultsHeader ---------- */
function ResultsHeader({
  framework, category, repoOwner, repoName, scopeCount,
}: {
  framework: string; category: string; repoOwner: string; repoName: string; scopeCount: number;
}) {
  const meta = [
    { k: "Framework", v: framework === "soc2-source-code" ? "SOC 2 · Source Code" : (framework || "SOC 2") },
    { k: "Repository", v: repoOwner && repoName ? `${repoOwner}/${repoName}` : "—" },
    { k: "Category", v: category || "Not specified" },
    { k: "Scope", v: scopeCount ? `${scopeCount} families` : "—" },
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1.3fr 0.7fr", gap: 40, alignItems: "end" }}>
      <div>
        <p className="eyebrow">Compliance Validation</p>
        <h2 style={{ fontSize: 34, fontWeight: 600, marginTop: 14 }}>Validation results</h2>
        <p style={{ fontSize: 15, lineHeight: 1.6, color: "var(--ink-3)", marginTop: 12, maxWidth: 540 }}>
          Control outcomes, evidence confidence, and the findings produced by the compliance workflow.
        </p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "18px 28px" }}>
        {meta.map((x) => (
          <div key={x.k}>
            <p className="eyebrow-muted" style={{ margin: 0, fontSize: 10 }}>{x.k}</p>
            <p className="mono" style={{ margin: "7px 0 0", fontSize: 14, color: "var(--ink)", fontWeight: 500, wordBreak: "break-word" }}>{x.v}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- MetricRail ---------- */
function MetricRail({ label, value, caption, accent }: { label: string; value: string; caption: string; accent?: boolean }) {
  return (
    <div style={{ display: "grid", gap: 10 }}>
      <p className="eyebrow-muted" style={{ margin: 0 }}>{label}</p>
      <p className="tnum" style={{ margin: 0, fontSize: 34, fontWeight: 600, letterSpacing: "-0.02em", color: accent ? "var(--brand-600)" : "var(--ink)", lineHeight: 1 }}>{value}</p>
      <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: "var(--ink-3)", maxWidth: 230 }}>{caption}</p>
    </div>
  );
}

/* ---------- StatusLegend ---------- */
function StatusLegend({ segments, total }: { segments: ResultMetrics["statusSegments"]; total: number }) {
  return (
    <div style={{ display: "grid", gap: 2 }}>
      {segments.map((s) => {
        const v = total ? (s.count / total) * 100 : 0;
        return (
          <div key={s.label} style={{ display: "grid", gridTemplateColumns: "1fr auto auto", alignItems: "center", gap: 14, padding: "11px 0", borderBottom: "1px solid var(--line)" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 9, height: 9, borderRadius: 3, background: s.color }} />
              <span style={{ fontSize: 13.5, color: "var(--ink)", fontWeight: 500 }}>{STATUS_META[s.label].label}</span>
            </span>
            <span className="tnum" style={{ fontSize: 13, color: "var(--ink-3)", textAlign: "right", minWidth: 52 }}>{pct1(v)}</span>
            <span className="tnum" style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)", textAlign: "right", minWidth: 24 }}>{s.count}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ---------- SeverityBar ---------- */
function SeverityBar({ severity, sevTotal }: { severity: Record<SeverityKey, number>; sevTotal: number }) {
  const levels: SeverityKey[] = ["critical", "high", "medium", "low"];
  return (
    <div>
      <div style={{ display: "flex", height: 10, width: "100%", borderRadius: 999, overflow: "hidden", background: "var(--paper-3)", gap: 2 }}>
        {levels.map((lv) => {
          const w = sevTotal ? (severity[lv] / sevTotal) * 100 : 0;
          return w ? <div key={lv} className="bar-grow" style={{ width: `${w}%`, background: SEVERITY_COLOR[lv], borderRadius: 999 }} /> : null;
        })}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 24px", marginTop: 18 }}>
        {levels.map((lv) => (
          <div key={lv} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: 9, borderBottom: "1px solid var(--line)" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 9, fontSize: 13.5, color: "var(--ink-2)", textTransform: "capitalize" }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, background: SEVERITY_COLOR[lv] }} />{lv}
            </span>
            <span className="tnum" style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>{severity[lv]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- FindingsComposition ---------- */
function FindingsComposition({ findings, findTotal }: { findings: Record<FindingKey, number>; findTotal: number }) {
  const rows: Array<{ key: FindingKey; label: string }> = [
    { key: "violation", label: "Violations" },
    { key: "gap", label: "Gaps" },
    { key: "pass", label: "Pass signals" },
  ];
  return (
    <div style={{ display: "grid", gap: 18 }}>
      {rows.map((r) => {
        const v = findTotal ? (findings[r.key] / findTotal) * 100 : 0;
        return (
          <div key={r.key} style={{ display: "grid", gridTemplateColumns: "108px 1fr 32px", alignItems: "center", gap: 16 }}>
            <span style={{ fontSize: 13.5, color: "var(--ink-2)" }}>{r.label}</span>
            <Progress value={v} color={FINDING_FILL[r.key]} height={8} />
            <span className="tnum" style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)", textAlign: "right" }}>{findings[r.key]}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ---------- ConfidenceMeter (inline, for table rows) ---------- */
function ConfidenceMeter({ control }: { control: ControlValidation }) {
  return (
    <div style={{ display: "grid", gap: 7 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span className="mono" style={{ fontSize: 10.5, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-4)" }}>{control.confidence_label}</span>
        <span className="mono tnum" style={{ fontSize: 12, color: "var(--ink-2)" }}>{pct(control.confidence * 100)}</span>
      </div>
      <Progress value={control.confidence * 100} color={STATUS_META[control.status].fill} height={5} />
    </div>
  );
}

/* ---------- ControlTableRow ---------- */
function ControlTableRow({ control, selected, onSelect }: { control: ControlValidation; selected: boolean; onSelect: () => void }) {
  const [hover, setHover] = React.useState(false);
  return (
    <button type="button" onClick={onSelect} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ width: "100%", textAlign: "left", border: "none", borderBottom: "1px solid var(--line)", background: selected ? "var(--paper-2)" : "transparent",
        padding: "18px 16px", cursor: "pointer", transition: "background 140ms", position: "relative", display: "block" }}>
      <span style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 2.5, background: selected ? STATUS_META[control.status].fill : hover ? "var(--line-2)" : "transparent", transition: "background 140ms" }} />
      <div style={{ display: "grid", gridTemplateColumns: "84px 1.5fr 118px 96px 150px", gap: 18, alignItems: "center" }}>
        <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)" }}>{control.regulation_id}</span>
        <span style={{ fontSize: 13.5, lineHeight: 1.45, color: "var(--ink-2)", overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>{control.title}</span>
        <StatusBadge status={control.status} size="sm" />
        <span>{control.severity ? <SeverityBadge severity={control.severity} /> : <span style={{ color: "var(--ink-4)", fontSize: 13 }}>—</span>}</span>
        <ConfidenceMeter control={control} />
      </div>
    </button>
  );
}

/* ---------- ControlDetail ---------- */
function ControlDetail({ control }: { control: ControlValidation | null }) {
  if (!control) {
    return <div style={{ padding: "56px 0", textAlign: "center", color: "var(--ink-4)", fontSize: 14 }}>Select a control to inspect its reasoning and evidence.</div>;
  }
  return (
    <div className="anim-fade-in" style={{ display: "grid", gap: 26 }}>
      <div style={{ display: "grid", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <span className="mono" style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.01em", color: "var(--ink)" }}>{control.regulation_id}</span>
          <StatusBadge status={control.status} />
          {control.severity ? <SeverityBadge severity={control.severity} /> : null}
        </div>
        <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.55, color: "var(--ink)" }}>{control.title}</p>
      </div>
      <Sep />
      <div style={{ display: "grid", gap: 10 }}>
        <p className="eyebrow-muted" style={{ margin: 0 }}>Overall reasoning</p>
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.7, color: "var(--ink-2)" }}>{control.overall_reasoning}</p>
      </div>
      <Sep />
      <div style={{ display: "grid", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <p className="eyebrow-muted" style={{ margin: 0 }}>Findings</p>
          <span style={{ fontSize: 13, color: "var(--ink-4)" }}>{control.findings.length} total</span>
        </div>
        {control.findings.map((f, i) => (
          <div key={i} style={{ display: "grid", gap: 11, paddingBottom: 18, borderBottom: i < control.findings.length - 1 ? "1px solid var(--line)" : "none" }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 11, flexWrap: "wrap" }}>
              <FindingBadge type={f.type} />
              <p style={{ margin: 0, fontSize: 14, fontWeight: 500, lineHeight: 1.5, color: "var(--ink)", flex: 1, minWidth: 200 }}>{f.description}</p>
            </div>
            {f.evidence_ref?.snippet ? (
              <div style={{ borderLeft: "2px solid var(--brand)", background: "var(--paper-2)", borderRadius: "0 var(--r-xs) var(--r-xs) 0", padding: "10px 14px" }}>
                <span className="mono" style={{ fontSize: 12.5, lineHeight: 1.6, color: "var(--ink-2)", wordBreak: "break-word" }}>{f.evidence_ref.snippet}</span>
              </div>
            ) : control.status === "NO_EVIDENCE" ? (
              <p style={{ margin: 0, fontSize: 13, color: "var(--ink-4)", fontStyle: "italic" }}>No direct evidence reference was returned for this control.</p>
            ) : null}
            <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.6, color: "var(--ink-3)" }}>{f.reasoning}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- RawOutput ---------- */
function RawOutput({ json }: { json: string }) {
  const [open, setOpen] = React.useState(false);
  return (
    <div>
      <button type="button" onClick={() => setOpen((o) => !o)}
        style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, padding: "0 0 16px",
          border: "none", borderBottom: "1px solid var(--line)", background: "transparent", cursor: "pointer", textAlign: "left" }}>
        <div>
          <p className="eyebrow-muted" style={{ margin: 0 }}>Raw validation output</p>
          <p style={{ margin: "8px 0 0", fontSize: 13.5, color: "var(--ink-3)" }}>The original structured payload, kept available for audit and debugging.</p>
        </div>
        <Icon name="chevronDown" size={18} style={{ stroke: "var(--ink-3)", transform: open ? "rotate(180deg)" : "none", transition: "transform 180ms" }} />
      </button>
      {open ? (
        <pre className="anim-fade-in scroll-quiet" style={{ marginTop: 18, padding: 20, background: "var(--paper-2)", border: "1px solid var(--line)", borderRadius: "var(--r)",
          overflowX: "auto", maxHeight: 360, fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: 1.65, color: "var(--ink-2)" }}>{json || "No validation payload captured yet."}</pre>
      ) : null}
    </div>
  );
}

/* ============================================================
   LedgerResults — the production results layout
   ============================================================ */
export function LedgerResults({
  m, framework, category, repoOwner, repoName, scopeCount, selectedKey, onSelect, selected, json,
}: {
  m: ResultMetrics;
  framework: string; category: string; repoOwner: string; repoName: string; scopeCount: number;
  selectedKey: string; onSelect: (key: string) => void; selected: ControlValidation | null; json: string;
}) {
  return (
    <div className="anim-screen" style={{ maxWidth: 1180, margin: "0 auto" }}>
      <ResultsHeader framework={framework} category={category} repoOwner={repoOwner} repoName={repoName} scopeCount={scopeCount} />
      <Sep style={{ margin: "36px 0 0" }} />

      {/* metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 40, padding: "34px 0" }}>
        <MetricRail label="Posture" value={pct(m.posture)} caption="Weighted readiness from pass and partial outcomes." accent />
        <MetricRail label="Evidence coverage" value={pct(m.coverage)} caption="Controls with repository evidence found." />
        <MetricRail label="Avg confidence" value={pct(m.confidence)} caption="Mean confidence across the validation set." />
        <MetricRail label="Controls reviewed" value={String(m.total)} caption="Total control validations returned." />
      </div>
      <Sep />

      {/* charts row */}
      <div style={{ display: "grid", gridTemplateColumns: "1.15fr 0.85fr", gap: 56, padding: "40px 0" }}>
        <div style={{ display: "grid", gap: 40 }}>
          <div>
            <SectionLabel label="Outcome distribution" caption="Status mix across all validated controls." right={<Tag tone="brand">{m.total} controls</Tag>} />
            <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 40, alignItems: "center", marginTop: 24 }}>
              <StatusDonut segments={m.statusSegments} total={m.total} />
              <StatusLegend segments={m.statusSegments} total={m.total} />
            </div>
          </div>
          <Sep />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 48 }}>
            <div>
              <SectionLabel label="Severity mix" caption="Controls carrying severity labels." />
              <div style={{ marginTop: 22 }}><SeverityBar severity={m.severity} sevTotal={m.sevTotal} /></div>
            </div>
            <div>
              <SectionLabel label="Findings composition" caption="Pass signals, gaps, and violations." />
              <div style={{ marginTop: 22 }}><FindingsComposition findings={m.findings} findTotal={m.findTotal} /></div>
            </div>
          </div>
        </div>

        {/* right rail: gauge + ring, strongly differentiated */}
        <div style={{ borderLeft: "1px solid var(--line)", paddingLeft: 48, display: "grid", gap: 36, alignContent: "start" }}>
          <div>
            <SectionLabel label="Readiness gauge" caption="Single headline score for overall posture." />
            <div style={{ marginTop: 24, display: "flex", justifyContent: "center" }}><PostureGauge value={m.posture} /></div>
          </div>
          <Sep />
          <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
            <ConfidenceRing value={m.confidence} />
            <div>
              <p className="eyebrow-muted" style={{ margin: 0 }}>Evidence confidence</p>
              <p style={{ margin: "10px 0 0", fontSize: 13, lineHeight: 1.6, color: "var(--ink-3)" }}>How decisive the agent was across the full result set. Lower values mean thinner evidence.</p>
            </div>
          </div>
        </div>
      </div>
      <Sep />

      {/* explorer + detail */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 56, padding: "40px 0" }}>
        <div>
          <SectionLabel label="Control explorer" caption="Ordered by risk first, then confidence." right={<Tag>{m.total} loaded</Tag>} />
          <div style={{ marginTop: 22 }}>
            <div style={{ display: "grid", gridTemplateColumns: "84px 1.5fr 118px 96px 150px", gap: 18, padding: "0 16px 12px", borderBottom: "1px solid var(--line-2)" }}>
              {["Control", "Title", "Status", "Severity", "Confidence"].map((h) => (
                <span key={h} className="eyebrow-muted" style={{ fontSize: 10 }}>{h}</span>
              ))}
            </div>
            {m.sorted.map((c) => (
              <ControlTableRow key={getControlKey(c)} control={c} selected={getControlKey(c) === selectedKey} onSelect={() => onSelect(getControlKey(c))} />
            ))}
          </div>
        </div>
        <div style={{ borderLeft: "1px solid var(--line)", paddingLeft: 48 }}>
          <SectionLabel label="Control detail" caption="Reasoning and evidence trail." />
          <div style={{ marginTop: 24 }}><ControlDetail control={selected} /></div>
        </div>
      </div>
      <Sep />
      <div style={{ padding: "36px 0" }}><RawOutput json={json} /></div>
    </div>
  );
}
