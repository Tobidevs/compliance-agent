"use client";

import * as React from "react";

import { Icon } from "@/components/icons";
import { Select } from "@/components/compliance/Select";
import { CATEGORIES, FRAMEWORKS, SCOPE_OPTIONS, fmtFramework } from "@/lib/constants";
import { useReview } from "@/context/ReviewProvider";

const sectionLabel: React.CSSProperties = {
  width: 24,
  height: 24,
  borderRadius: 7,
  background: "var(--brand-50)",
  color: "var(--brand-700)",
  display: "grid",
  placeItems: "center",
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  fontWeight: 600,
};

const fieldLabel: React.CSSProperties = { fontSize: 13, fontWeight: 500, color: "var(--ink-2)" };

function ScopeRow({ label, checked, onToggle }: { label: string; checked: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        width: "100%",
        textAlign: "left",
        padding: "12px 14px",
        borderRadius: "var(--r-sm)",
        border: `1px solid ${checked ? "var(--brand-line)" : "var(--line)"}`,
        background: checked ? "var(--brand-50)" : "var(--paper)",
        cursor: "pointer",
        transition: "all 140ms",
        fontFamily: "var(--font-sans)",
      }}
      onMouseEnter={(e) => {
        if (!checked) e.currentTarget.style.borderColor = "var(--line-2)";
      }}
      onMouseLeave={(e) => {
        if (!checked) e.currentTarget.style.borderColor = "var(--line)";
      }}
    >
      <span
        style={{
          width: 18,
          height: 18,
          borderRadius: 5,
          flexShrink: 0,
          display: "grid",
          placeItems: "center",
          border: `1.5px solid ${checked ? "var(--brand)" : "var(--line-2)"}`,
          background: checked ? "var(--brand)" : "transparent",
          transition: "all 140ms",
        }}
      >
        {checked ? <Icon name="check" size={12} strokeWidth={3} style={{ stroke: "#fff" }} /> : null}
      </span>
      <span style={{ fontSize: 13, color: "var(--ink)", lineHeight: 1.35 }}>{label}</span>
    </button>
  );
}

function BriefRow({ label, value }: { label: string; value: string }) {
  return (
    <>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <span style={{ fontSize: 13, color: "var(--ink-3)" }}>{label}</span>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 12.5,
            fontWeight: 500,
            color: "var(--ink)",
            textAlign: "right",
            wordBreak: "break-all",
          }}
        >
          {value}
        </span>
      </div>
      <div style={{ height: 1, background: "var(--line)" }} />
    </>
  );
}

export function IntakeForm() {
  const {
    framework,
    setFramework,
    category,
    setCategory,
    scopes,
    toggleScope,
    repoOwner,
    setRepoOwner,
    repoName,
    setRepoName,
    ready,
    repoLabel,
    loading,
    submitReview,
  } = useReview();

  const inputStyle: React.CSSProperties = {
    height: 44,
    border: "1px solid var(--line-2)",
    borderRadius: "var(--r-sm)",
    background: "var(--paper)",
    padding: "0 14px",
    fontSize: 14,
    color: "var(--ink)",
    fontFamily: "var(--font-sans)",
    outline: "none",
  };

  const onFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    e.currentTarget.style.borderColor = "var(--brand)";
    e.currentTarget.style.boxShadow = "0 0 0 3px var(--brand-50)";
  };
  const onBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    e.currentTarget.style.borderColor = "var(--line-2)";
    e.currentTarget.style.boxShadow = "none";
  };

  return (
    <div style={{ maxWidth: 1080, margin: "0 auto", padding: "40px 32px 80px" }}>
      <div className="anim-fade-up">
        <p className="eyebrow" style={{ margin: 0 }}>
          New validation
        </p>
        <h1 style={{ margin: "14px 0 0", fontSize: 32, fontWeight: 600, color: "var(--ink)", lineHeight: 1.1 }}>
          Configure a compliance review
        </h1>
        <p style={{ margin: "12px 0 0", fontSize: 15, lineHeight: 1.6, color: "var(--ink-3)", maxWidth: 560 }}>
          Point the agent at a source repository, choose the control families in scope, and it maps evidence, validates
          each control, and scores readiness.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 320px",
          gap: 28,
          marginTop: 34,
          alignItems: "start",
        }}
      >
        <form
          className="anim-fade-up-2"
          onSubmit={(e) => {
            e.preventDefault();
            submitReview();
          }}
          style={{
            border: "1px solid var(--line)",
            borderRadius: "var(--r-lg)",
            background: "var(--paper)",
            boxShadow: "var(--shadow)",
            overflow: "visible",
          }}
        >
          {/* Section 01 */}
          <div style={{ padding: "26px 28px", borderBottom: "1px solid var(--line)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 11, marginBottom: 20 }}>
              <span style={sectionLabel}>01</span>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "var(--ink)" }}>Framework &amp; category</h3>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
              <div style={{ display: "grid", gap: 8 }}>
                <label style={fieldLabel}>Framework</label>
                <Select
                  value={framework}
                  placeholder="Select framework"
                  options={FRAMEWORKS}
                  onChange={setFramework}
                  format={fmtFramework}
                />
              </div>
              <div style={{ display: "grid", gap: 8 }}>
                <label style={fieldLabel}>Category</label>
                <Select value={category} placeholder="Select category" options={CATEGORIES} onChange={setCategory} />
              </div>
            </div>
          </div>

          {/* Section 02 */}
          <div style={{ padding: "26px 28px", borderBottom: "1px solid var(--line)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
                <span style={sectionLabel}>02</span>
                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "var(--ink)" }}>Source code categories</h3>
              </div>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "3px 10px",
                  borderRadius: "var(--r-pill)",
                  border: `1px solid ${scopes.length ? "var(--brand-line)" : "var(--line-2)"}`,
                  background: scopes.length ? "var(--brand-50)" : "transparent",
                  color: scopes.length ? "var(--brand-700)" : "var(--ink-3)",
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  fontWeight: 500,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                }}
              >
                {scopes.length} selected
              </span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 9 }}>
              {SCOPE_OPTIONS.map((o) => (
                <ScopeRow key={o} label={o} checked={scopes.includes(o)} onToggle={() => toggleScope(o)} />
              ))}
            </div>
          </div>

          {/* Section 03 */}
          <div style={{ padding: "26px 28px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 11, marginBottom: 18 }}>
              <span style={sectionLabel}>03</span>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "var(--ink)" }}>Repository target</h3>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
              <div style={{ display: "grid", gap: 8 }}>
                <label style={fieldLabel}>Owner</label>
                <input
                  value={repoOwner}
                  onChange={(e) => setRepoOwner(e.target.value)}
                  placeholder="org-or-user"
                  style={inputStyle}
                  onFocus={onFocus}
                  onBlur={onBlur}
                />
              </div>
              <div style={{ display: "grid", gap: 8 }}>
                <label style={fieldLabel}>Repository</label>
                <input
                  value={repoName}
                  onChange={(e) => setRepoName(e.target.value)}
                  placeholder="repo-name"
                  style={inputStyle}
                  onFocus={onFocus}
                  onBlur={onBlur}
                />
              </div>
            </div>
          </div>

          {/* Footer */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 16,
              padding: "18px 28px",
              borderTop: "1px solid var(--line)",
              background: "var(--paper-2)",
            }}
          >
            <span className="mono" style={{ fontSize: 12.5, color: "var(--ink-3)" }}>
              {repoLabel}
            </span>
            <button
              type="submit"
              disabled={!ready || loading}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 9,
                height: 44,
                padding: "0 22px",
                borderRadius: "var(--r-sm)",
                border: "1px solid transparent",
                background: "var(--brand)",
                color: "#fff",
                fontSize: 14,
                fontWeight: 500,
                fontFamily: "var(--font-sans)",
                cursor: ready && !loading ? "pointer" : "not-allowed",
                boxShadow: "var(--shadow-sm)",
                opacity: ready && !loading ? 1 : 0.5,
              }}
            >
              {loading ? "Running…" : "Run compliance review"}
              <Icon name="arrowRight" size={16} strokeWidth={2} />
            </button>
          </div>
        </form>

        <div className="anim-fade-up-2" style={{ display: "grid", gap: 16 }}>
          <div
            style={{
              border: "1px solid var(--line)",
              borderRadius: "var(--r-lg)",
              background: "var(--paper)",
              boxShadow: "var(--shadow-sm)",
              padding: 20,
            }}
          >
            <p
              className="eyebrow-muted"
              style={{ margin: 0, fontSize: 10, letterSpacing: "0.18em", color: "var(--ink-4)" }}
            >
              Run brief
            </p>
            <div style={{ display: "grid", gap: 14, marginTop: 16 }}>
              <BriefRow label="Framework" value={fmtFramework(framework)} />
              <BriefRow label="Families in scope" value={String(scopes.length)} />
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
                <span style={{ fontSize: 13, color: "var(--ink-3)" }}>Target</span>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 12.5,
                    fontWeight: 500,
                    color: "var(--ink)",
                    textAlign: "right",
                    wordBreak: "break-all",
                  }}
                >
                  {repoLabel}
                </span>
              </div>
            </div>
          </div>

          <div
            style={{
              border: "1px solid var(--brand-line)",
              borderRadius: "var(--r-lg)",
              background: "var(--brand-50)",
              padding: "18px 20px",
            }}
          >
            <div style={{ display: "flex", gap: 11 }}>
              <Icon name="info" size={18} strokeWidth={1.8} style={{ stroke: "var(--brand-700)", marginTop: 1 }} />
              <p style={{ margin: 0, fontSize: 13, lineHeight: 1.6, color: "var(--brand-700)" }}>
                Evidence is read directly from source. Process-bound controls — incident response, ROPA — may report{" "}
                <strong>No evidence</strong> if they live outside the repository.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
