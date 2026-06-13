"use client";

import * as React from "react";
import { Icon } from "./Icon";
import { Button, Tag, Sep } from "./primitives";
import { WORKFLOW_STEPS } from "@/lib/compliance-theme";

/* ============================================================
   Brand header (logo + title). No manual screen-nav.
   "New review" appears only on the results screen.
   ============================================================ */
export function BrandHeader({ showNewReview, onNewReview }: { showNewReview?: boolean; onNewReview?: () => void }) {
  return (
    <header style={{ position: "sticky", top: 0, zIndex: 50, background: "rgba(255,255,255,0.82)", backdropFilter: "saturate(180%) blur(12px)", borderBottom: "1px solid var(--line)" }}>
      <div style={{ maxWidth: 1320, margin: "0 auto", padding: "0 28px", height: 60, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ width: 26, height: 26, borderRadius: 7, background: "var(--brand)", display: "grid", placeItems: "center", flexShrink: 0 }}>
            <Icon name="shield" size={16} style={{ stroke: "#fff", strokeWidth: 2 }} />
          </span>
          <div style={{ lineHeight: 1.1 }}>
            <p style={{ margin: 0, fontSize: 14.5, fontWeight: 600, color: "var(--ink)" }}>Compliance Agent</p>
            <p className="mono" style={{ margin: 0, fontSize: 10.5, letterSpacing: "0.1em", color: "var(--ink-4)", textTransform: "uppercase" }}>SOC 2 · Source Code</p>
          </div>
        </div>
        {showNewReview ? (
          <Button variant="outline" size="sm" onClick={onNewReview}>New review</Button>
        ) : null}
      </div>
    </header>
  );
}

/* ---------- Field wrapper ---------- */
export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "grid", gap: 9 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12 }}>
        <label style={{ fontSize: 13.5, fontWeight: 500, color: "var(--ink)" }}>{label}</label>
        {hint ? <span style={{ fontSize: 12, color: "var(--ink-4)" }}>{hint}</span> : null}
      </div>
      {children}
    </div>
  );
}

/* ---------- Custom Select ---------- */
export function Select({
  value, placeholder, options, onChange, format,
}: {
  value: string; placeholder: string; options: string[];
  onChange: (v: string) => void; format?: (v: string) => string;
}) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  const display = value ? (format ? format(value) : value) : placeholder;
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button type="button" className="focusable" onClick={() => setOpen((o) => !o)}
        style={{ height: 46, width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0 14px", borderRadius: "var(--r-sm)", border: `1px solid ${open ? "var(--brand)" : "var(--line-2)"}`,
          background: "var(--paper)", color: value ? "var(--ink)" : "var(--ink-4)", fontSize: 14, fontFamily: "var(--font-sans)",
          cursor: "pointer", transition: "border-color 140ms", boxShadow: open ? "0 0 0 3px rgba(249,115,22,0.12)" : "none" }}>
        <span>{display}</span>
        <Icon name="chevronDown" size={16} style={{ stroke: "var(--ink-3)", transform: open ? "rotate(180deg)" : "none", transition: "transform 160ms" }} />
      </button>
      {open ? (
        <div className="anim-fade-in" style={{ position: "absolute", top: "calc(100% + 6px)", left: 0, right: 0, zIndex: 30,
          background: "var(--paper)", border: "1px solid var(--line-2)", borderRadius: "var(--r-sm)", boxShadow: "var(--shadow-lg)", padding: 5, overflow: "hidden" }}>
          {options.map((opt) => {
            const sel = opt === value;
            return (
              <button key={opt} type="button" onClick={() => { onChange(opt); setOpen(false); }}
                style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10,
                  padding: "10px 11px", borderRadius: "var(--r-xs)", border: "none", background: sel ? "var(--brand-50)" : "transparent",
                  color: "var(--ink)", fontSize: 14, fontFamily: "var(--font-sans)", cursor: "pointer", textAlign: "left", transition: "background 120ms" }}
                onMouseEnter={(e) => { if (!sel) e.currentTarget.style.background = "var(--paper-3)"; }}
                onMouseLeave={(e) => { if (!sel) e.currentTarget.style.background = "transparent"; }}>
                <span>{format ? format(opt) : opt}</span>
                {sel ? <Icon name="check" size={15} style={{ stroke: "var(--brand-600)" }} /> : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

/* ---------- TextInput ---------- */
export function TextInput({
  value, onChange, placeholder, prefix,
}: {
  value: string; onChange: (v: string) => void; placeholder?: string; prefix?: string;
}) {
  const [focus, setFocus] = React.useState(false);
  return (
    <div className="focusable" style={{ height: 46, display: "flex", alignItems: "center", borderRadius: "var(--r-sm)",
      border: `1px solid ${focus ? "var(--brand)" : "var(--line-2)"}`, background: "var(--paper)", overflow: "hidden",
      transition: "border-color 140ms", boxShadow: focus ? "0 0 0 3px rgba(249,115,22,0.12)" : "none" }}>
      {prefix ? <span className="mono" style={{ paddingLeft: 14, color: "var(--ink-4)", fontSize: 13.5 }}>{prefix}</span> : null}
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}
        style={{ flex: 1, height: "100%", border: "none", outline: "none", background: "transparent", padding: "0 14px",
          fontSize: 14, color: "var(--ink)", fontFamily: "var(--font-sans)" }} />
    </div>
  );
}

/* ---------- ScopeRow ---------- */
function ScopeRow({ label, checked, onToggle }: { label: string; checked: boolean; onToggle: () => void }) {
  return (
    <button type="button" onClick={onToggle}
      style={{ display: "flex", alignItems: "center", gap: 13, width: "100%", textAlign: "left", padding: "13px 15px",
        borderRadius: "var(--r-sm)", border: `1px solid ${checked ? "var(--brand-line)" : "var(--line)"}`,
        background: checked ? "var(--brand-50)" : "var(--paper)", cursor: "pointer", transition: "all 140ms", fontFamily: "var(--font-sans)" }}
      onMouseEnter={(e) => { if (!checked) e.currentTarget.style.borderColor = "var(--line-2)"; }}
      onMouseLeave={(e) => { if (!checked) e.currentTarget.style.borderColor = "var(--line)"; }}>
      <span style={{ width: 19, height: 19, borderRadius: 6, flexShrink: 0, display: "grid", placeItems: "center",
        border: `1.5px solid ${checked ? "var(--brand)" : "var(--line-2)"}`, background: checked ? "var(--brand)" : "transparent", transition: "all 140ms" }}>
        {checked ? <Icon name="check" size={12} style={{ stroke: "#fff", strokeWidth: 3 }} /> : null}
      </span>
      <span style={{ fontSize: 13.5, color: "var(--ink)", lineHeight: 1.35 }}>{label}</span>
    </button>
  );
}

/* ============================================================
   IntakeScreen — ledger-style document form
   ============================================================ */
const FRAMEWORKS = ["soc2-source-code"];
const CATEGORIES = ["Category A", "Category B", "Category C"];
const SCOPE_OPTIONS = [
  "Change Management & SDLC", "Identity & Access Management", "Data Protection & Privacy",
  "Processing Integrity", "Network & Systems Security", "Logging & Monitoring", "Operations & Incident Management",
];
const fmtFramework = (v: string) => (v === "soc2-source-code" ? "SOC 2 · Source Code" : v);

function SectionHead({ n, title, desc }: { n: string; title: string; desc: string }) {
  return (
    <div>
      <p className="eyebrow-muted" style={{ margin: 0 }}>{n}</p>
      <h3 style={{ fontSize: 17, fontWeight: 600, marginTop: 10 }}>{title}</h3>
      <p style={{ fontSize: 13, lineHeight: 1.55, color: "var(--ink-3)", marginTop: 8, maxWidth: 230 }}>{desc}</p>
    </div>
  );
}

export function IntakeScreen({
  framework, setFramework, category, setCategory,
  scopes, toggleScope, repoOwner, setRepoOwner, repoName, setRepoName,
  loading, onSubmit,
}: {
  framework: string; setFramework: (v: string) => void;
  category: string; setCategory: (v: string) => void;
  scopes: string[]; toggleScope: (v: string) => void;
  repoOwner: string; setRepoOwner: (v: string) => void;
  repoName: string; setRepoName: (v: string) => void;
  loading: boolean; onSubmit: () => void;
}) {
  const ready = Boolean(framework && repoOwner && repoName && scopes.length > 0);
  const sectionGrid: React.CSSProperties = { display: "grid", gridTemplateColumns: "minmax(170px, 0.5fr) 1fr", gap: 40, padding: "32px 0", alignItems: "start" };

  return (
    <div style={{ maxWidth: 880, margin: "0 auto", padding: "8px 0 64px" }}>
      <div className="anim-fade-up" style={{ textAlign: "center", maxWidth: 560, margin: "0 auto" }}>
        <p className="eyebrow">Compliance Validation</p>
        <h1 style={{ fontSize: 38, fontWeight: 600, marginTop: 16, lineHeight: 1.08 }}>Validate a repository<br />against SOC 2 controls</h1>
        <p style={{ fontSize: 15.5, lineHeight: 1.6, color: "var(--ink-3)", marginTop: 16 }}>
          Point the agent at a source repository and choose the control families in scope. We map the evidence, validate each control, and score readiness.
        </p>
      </div>

      <form className="anim-fade-up-2" onSubmit={(e) => { e.preventDefault(); onSubmit(); }}
        style={{ marginTop: 48, border: "1px solid var(--line)", borderRadius: "var(--r-lg)", background: "var(--paper)", boxShadow: "var(--shadow)", overflow: "hidden" }}>
        <div style={{ padding: "0 40px" }}>
          <div style={sectionGrid}>
            <SectionHead n="01 / Framework" title="Framework & category" desc="Select the standard and review category the agent should apply." />
            <div style={{ display: "grid", gap: 22 }}>
              <Field label="Framework"><Select value={framework} placeholder="Select framework" options={FRAMEWORKS} onChange={setFramework} format={fmtFramework} /></Field>
              <Field label="Category"><Select value={category} placeholder="Select category" options={CATEGORIES} onChange={setCategory} /></Field>
            </div>
          </div>
          <Sep />
          <div style={sectionGrid}>
            <SectionHead n="02 / Scope" title="Source code categories" desc="Choose the control families the agent will look for evidence of." />
            <div>
              <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
                <Tag tone={scopes.length ? "brand" : "neutral"}>{scopes.length} selected</Tag>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {SCOPE_OPTIONS.map((o) => <ScopeRow key={o} label={o} checked={scopes.includes(o)} onToggle={() => toggleScope(o)} />)}
              </div>
            </div>
          </div>
          <Sep />
          <div style={sectionGrid}>
            <SectionHead n="03 / Target" title="Repository" desc="The owner and repository name the agent will clone and scan." />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
              <Field label="Owner"><TextInput value={repoOwner} onChange={setRepoOwner} placeholder="org-or-user" /></Field>
              <Field label="Repository"><TextInput value={repoName} onChange={setRepoName} placeholder="compliance-agent" /></Field>
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, padding: "20px 40px",
          borderTop: "1px solid var(--line)", background: "var(--paper-2)" }}>
          <span className="mono" style={{ fontSize: 12, color: "var(--ink-3)", letterSpacing: "0.02em" }}>
            {repoOwner && repoName ? `${repoOwner}/${repoName}` : "No repository set"}
          </span>
          <Button type="submit" disabled={!ready || loading} iconRight={<Icon name="arrowRight" size={16} style={{ stroke: "currentColor" }} />}>
            {loading ? "Running…" : "Run compliance review"}
          </Button>
        </div>
      </form>
    </div>
  );
}

/* ============================================================
   RunningScreen — stepper. Driven by real stream progress:
   `stepIndex` advances as backend status events arrive, and the
   live `statusMessage` shows beneath the active step.
   ============================================================ */
export function RunningScreen({
  stepIndex, statusMessage, repoOwner, repoName,
}: {
  stepIndex: number; statusMessage?: string; repoOwner: string; repoName: string;
}) {
  const steps = WORKFLOW_STEPS;
  return (
    <div className="anim-fade-up" style={{ maxWidth: 620, margin: "0 auto", padding: "40px 0", textAlign: "center" }}>
      <p className="eyebrow">Compliance Validation</p>
      <h2 style={{ fontSize: 30, fontWeight: 600, marginTop: 16 }}>Running compliance checks</h2>
      <p style={{ fontSize: 15, lineHeight: 1.6, color: "var(--ink-3)", marginTop: 14, maxWidth: 460, marginInline: "auto" }}>
        Analyzing <span className="mono" style={{ color: "var(--ink-2)" }}>{repoOwner || "owner"}/{repoName || "repo"}</span>. Each step completes in sequence.
      </p>

      <div style={{ marginTop: 40, textAlign: "left", border: "1px solid var(--line)", borderRadius: "var(--r-lg)", background: "var(--paper)", boxShadow: "var(--shadow)", overflow: "hidden" }}>
        {steps.map((s, i) => {
          const done = i < stepIndex, active = i === stepIndex;
          return (
            <div key={s.key} style={{ display: "flex", alignItems: "center", gap: 16, padding: "18px 22px",
              borderTop: i ? "1px solid var(--line)" : "none", background: active ? "var(--brand-50)" : "transparent", transition: "background 300ms" }}>
              <span style={{ width: 26, height: 26, borderRadius: 999, flexShrink: 0, display: "grid", placeItems: "center",
                border: `1.5px solid ${done ? "var(--pass)" : active ? "var(--brand)" : "var(--line-2)"}`,
                background: done ? "var(--pass)" : "transparent", transition: "all 300ms" }}>
                {done ? <Icon name="check" size={13} style={{ stroke: "#fff", strokeWidth: 3 }} />
                  : active ? <span style={{ width: 8, height: 8, borderRadius: 999, background: "var(--brand)", animation: "step-pulse 1.1s ease-in-out infinite" }} />
                  : <span style={{ width: 6, height: 6, borderRadius: 999, background: "var(--line-2)" }} />}
              </span>
              <div style={{ flex: 1 }}>
                <p style={{ margin: 0, fontSize: 14.5, fontWeight: active || done ? 500 : 400, color: active ? "var(--ink)" : done ? "var(--ink-2)" : "var(--ink-4)" }}>{s.label}</p>
                <p style={{ margin: "3px 0 0", fontSize: 12.5, color: "var(--ink-4)" }}>{active && statusMessage ? statusMessage : s.detail}</p>
              </div>
              {active ? <span className="mono" style={{ fontSize: 11, color: "var(--brand-600)", letterSpacing: "0.1em" }}>RUNNING</span>
                : done ? <span className="mono" style={{ fontSize: 11, color: "var(--pass)", letterSpacing: "0.1em" }}>DONE</span> : null}
            </div>
          );
        })}
        <div style={{ height: 4, background: "var(--paper-3)", overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${(Math.min(stepIndex, steps.length) / steps.length) * 100}%`, background: "var(--brand)", transition: "width 500ms cubic-bezier(0.22,1,0.36,1)" }} />
        </div>
      </div>
    </div>
  );
}
