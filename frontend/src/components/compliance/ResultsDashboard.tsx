"use client";

import * as React from "react";

import { Donut } from "@/components/compliance/Donut";
import { Gauge } from "@/components/compliance/Gauge";
import { ControlDetail } from "@/components/compliance/ControlDetail";
import { Icon, type IconName } from "@/components/icons";
import {
  FINDING_META,
  SEVERITY_COLOR,
  STATUS_META,
  getControlKey,
  pct,
  pct1,
  type FindingKey,
  type SeverityKey,
  type StatusKey,
} from "@/lib/compliance-theme";
import { copySummary, exportPdf, exportResultsCsv } from "@/lib/export";
import { useReview } from "@/context/ReviewProvider";
import { useReveal } from "@/hooks/useReveal";

const tagBrand: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  padding: "3px 10px",
  borderRadius: "var(--r-pill)",
  border: "1px solid var(--brand-line)",
  background: "var(--brand-50)",
  color: "var(--brand-700)",
  fontFamily: "var(--font-mono)",
  fontSize: 10.5,
  fontWeight: 500,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
};

const eyebrowMono: React.CSSProperties = {
  margin: 0,
  fontFamily: "var(--font-mono)",
  fontSize: 10,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: "var(--ink-4)",
};

export function ResultsDashboard() {
  const { metrics: m, selectedKey, setSelectedKey, selectedControl, search, startNewReview, repoLabel, rawJson } =
    useReview();
  const reveal = useReveal(true, true);

  const [hover, setHover] = React.useState<StatusKey | null>(null);
  const [exportOpen, setExportOpen] = React.useState(false);
  const [rawOpen, setRawOpen] = React.useState(false);
  const [toast, setToast] = React.useState("");
  const exportRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setExportOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const flashToast = (msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(""), 2400);
  };

  const grade =
    m.posture >= 80 ? "Strong" : m.posture >= 55 ? "Developing" : m.posture >= 30 ? "At risk" : "Critical";
  const gradeColor =
    m.posture >= 80
      ? "var(--pass)"
      : m.posture >= 55
        ? "var(--brand-600)"
        : m.posture >= 30
          ? "var(--partial)"
          : "var(--fail)";

  const kpis: { label: string; value: number; unit: string; caption: string; accent: boolean; valueColor: string; icon: IconName }[] = [
    { label: "Posture", value: m.posture, unit: "/100", caption: "Weighted readiness from pass + partial outcomes.", accent: true, valueColor: "var(--brand-700)", icon: "shield" },
    { label: "Coverage", value: m.coverage, unit: "%", caption: "Controls with repository evidence found.", accent: false, valueColor: "var(--ink)", icon: "shieldCheck" },
    { label: "Avg confidence", value: m.confidence, unit: "%", caption: "Mean confidence across the validation set.", accent: false, valueColor: "var(--ink)", icon: "activity" },
    { label: "Controls", value: m.total, unit: "", caption: "Total control validations returned.", accent: false, valueColor: "var(--ink)", icon: "layers" },
  ];

  const sevLevels: SeverityKey[] = ["critical", "high", "medium", "low"];
  const findRows: { key: FindingKey; label: string }[] = [
    { key: "violation", label: "Violations" },
    { key: "gap", label: "Gaps" },
    { key: "pass", label: "Pass signals" },
  ];

  const controlRows = m.sorted.filter((c) => {
    if (!search.trim()) return true;
    const q = search.trim().toLowerCase();
    return c.regulation_id.toLowerCase().includes(q) || c.title.toLowerCase().includes(q);
  });

  const cardBase: React.CSSProperties = {
    border: "1px solid var(--line)",
    borderRadius: "var(--r-lg)",
    background: "var(--paper)",
    boxShadow: "var(--shadow-sm)",
  };

  const exportItem = (label: string, icon: IconName, onClick: () => void) => (
    <button
      type="button"
      onClick={onClick}
      style={{
        width: "100%",
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "9px 11px",
        borderRadius: "var(--r-xs)",
        border: "none",
        background: "transparent",
        color: "var(--ink)",
        fontSize: 13,
        fontFamily: "var(--font-sans)",
        cursor: "pointer",
        textAlign: "left",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--paper-3)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
    >
      <Icon name={icon} size={15} style={{ color: "var(--ink-3)" }} />
      {label}
    </button>
  );

  return (
    <div style={{ maxWidth: 1240, margin: "0 auto", padding: "32px 32px 90px" }}>
      {/* header */}
      <div
        className="anim-fade-up"
        style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 28, flexWrap: "wrap" }}
      >
        <div>
          <p className="eyebrow" style={{ margin: 0 }}>
            Validation complete
          </p>
          <h1 style={{ margin: "12px 0 0", fontSize: 30, fontWeight: 600, color: "var(--ink)" }}>Readiness dashboard</h1>
          <p style={{ margin: "10px 0 0", fontSize: 14, lineHeight: 1.6, color: "var(--ink-3)", maxWidth: 520 }}>
            Control outcomes, evidence confidence, and findings for{" "}
            <span className="mono" style={{ color: "var(--ink-2)" }}>
              {repoLabel}
            </span>
            .
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            type="button"
            onClick={startNewReview}
            className="app-card"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              height: 38,
              padding: "0 16px",
              borderRadius: "var(--r-sm)",
              border: "1px solid var(--line-2)",
              background: "var(--paper)",
              color: "var(--ink)",
              fontSize: 13,
              fontWeight: 500,
              fontFamily: "var(--font-sans)",
              cursor: "pointer",
            }}
          >
            New review
          </button>
          <div ref={exportRef} style={{ position: "relative" }}>
            <button
              type="button"
              onClick={() => setExportOpen((o) => !o)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                height: 38,
                padding: "0 16px",
                borderRadius: "var(--r-sm)",
                border: "1px solid transparent",
                background: "var(--brand)",
                color: "#fff",
                fontSize: 13,
                fontWeight: 500,
                fontFamily: "var(--font-sans)",
                cursor: "pointer",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <Icon name="download" size={15} strokeWidth={1.9} />
              Export report
            </button>
            {exportOpen ? (
              <div
                className="anim-fade-in"
                style={{
                  position: "absolute",
                  top: "calc(100% + 6px)",
                  right: 0,
                  zIndex: 30,
                  width: 196,
                  background: "var(--paper)",
                  border: "1px solid var(--line-2)",
                  borderRadius: "var(--r-sm)",
                  boxShadow: "var(--shadow-lg)",
                  padding: 5,
                }}
              >
                {exportItem("Export to CSV", "csv", () => {
                  exportResultsCsv(m.sorted, repoLabel);
                  setExportOpen(false);
                  flashToast("CSV exported");
                })}
                {exportItem("Export to PDF", "fileText", () => {
                  setExportOpen(false);
                  flashToast("Preparing PDF…");
                  setTimeout(exportPdf, 300);
                })}
                {exportItem("Copy summary", "copy", () => {
                  void copySummary(m, repoLabel);
                  setExportOpen(false);
                  flashToast("Summary copied");
                })}
              </div>
            ) : null}
          </div>
        </div>
      </div>

      {/* KPI strip */}
      <div
        className="anim-fade-up-2"
        style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginTop: 28 }}
      >
        {kpis.map((k) => (
          <div
            key={k.label}
            className="app-card"
            style={{
              ...cardBase,
              border: `1px solid ${k.accent ? "var(--brand-line)" : "var(--line)"}`,
              background: k.accent ? "var(--brand-50)" : "var(--paper)",
              padding: "18px 20px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <p style={{ ...eyebrowMono, fontSize: 10, letterSpacing: "0.16em" }}>{k.label}</p>
              <span
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: 7,
                  display: "grid",
                  placeItems: "center",
                  background: k.accent ? "var(--brand-100)" : "var(--paper-3)",
                  color: k.accent ? "var(--brand-700)" : "var(--ink-3)",
                }}
              >
                <Icon name={k.icon} size={14} strokeWidth={1.9} />
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 3, marginTop: 14 }}>
              <span
                className="tnum"
                style={{ fontSize: 34, fontWeight: 600, letterSpacing: "-0.02em", lineHeight: 1, color: k.valueColor }}
              >
                {Math.round(k.value * reveal)}
              </span>
              <span style={{ fontSize: 15, fontWeight: 500, color: "var(--ink-4)" }}>{k.unit}</span>
            </div>
            <p style={{ margin: "10px 0 0", fontSize: 12, lineHeight: 1.5, color: "var(--ink-3)" }}>{k.caption}</p>
          </div>
        ))}
      </div>

      {/* charts row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.15fr", gap: 16, marginTop: 16 }}>
        {/* gauge */}
        <div className="app-card" style={{ ...cardBase, padding: "22px 24px", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <p style={{ margin: 0, fontSize: 13.5, fontWeight: 600, color: "var(--ink)" }}>Readiness posture</p>
            <span style={{ ...eyebrowMono, fontSize: 10.5, letterSpacing: "0.08em" }}>Weighted</span>
          </div>
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 30,
              padding: "8px 0",
              flexWrap: "wrap",
            }}
          >
            <Gauge value={m.posture} reveal={reveal} />
            <div style={{ display: "grid", gap: 14, minWidth: 140 }}>
              <div>
                <p style={{ ...eyebrowMono, fontSize: 10 }}>Grade</p>
                <p
                  style={{
                    margin: "7px 0 0",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    fontSize: 18,
                    fontWeight: 600,
                    color: gradeColor,
                  }}
                >
                  <span style={{ width: 8, height: 8, borderRadius: 999, background: gradeColor }} />
                  {grade}
                </p>
              </div>
              <div style={{ height: 1, background: "var(--line)" }} />
              <div>
                <p style={{ ...eyebrowMono, fontSize: 10 }}>Evidence coverage</p>
                <p className="tnum" style={{ margin: "7px 0 0", fontSize: 18, fontWeight: 600, color: "var(--ink)" }}>
                  {pct(m.coverage * reveal)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* donut */}
        <div className="app-card" style={{ ...cardBase, padding: "22px 24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <p style={{ margin: 0, fontSize: 13.5, fontWeight: 600, color: "var(--ink)" }}>Outcome distribution</p>
            <span style={tagBrand}>{m.total} controls</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "168px 1fr", gap: 26, alignItems: "center", marginTop: 14 }}>
            <Donut segments={m.statusSegments} total={m.total} reveal={reveal} hover={hover} onHover={setHover} />
            <div style={{ display: "grid", gap: 1 }}>
              {m.statusSegments.map((s) => (
                <div
                  key={s.label}
                  onMouseEnter={() => setHover(s.label)}
                  onMouseLeave={() => setHover(null)}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr auto auto",
                    alignItems: "center",
                    gap: 12,
                    padding: "9px 4px",
                    borderBottom: "1px solid var(--line)",
                    cursor: "default",
                  }}
                >
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 9 }}>
                    <span style={{ width: 9, height: 9, borderRadius: 3, background: s.color }} />
                    <span style={{ fontSize: 13, color: "var(--ink)", fontWeight: 500 }}>
                      {STATUS_META[s.label].label}
                    </span>
                  </span>
                  <span
                    className="tnum"
                    style={{ fontSize: 12.5, color: "var(--ink-3)", textAlign: "right", minWidth: 46 }}
                  >
                    {pct1(m.total ? (s.count / m.total) * 100 : 0)}
                  </span>
                  <span
                    className="tnum"
                    style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)", textAlign: "right", minWidth: 22 }}
                  >
                    {s.count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* severity + findings */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
        <div className="app-card" style={{ ...cardBase, padding: "22px 24px" }}>
          <p style={{ margin: 0, fontSize: 13.5, fontWeight: 600, color: "var(--ink)" }}>Severity exposure</p>
          <p style={{ margin: "6px 0 0", fontSize: 12.5, color: "var(--ink-3)" }}>
            Across controls carrying a severity label.
          </p>
          <div
            style={{
              display: "flex",
              height: 11,
              width: "100%",
              borderRadius: 999,
              overflow: "hidden",
              background: "var(--paper-3)",
              gap: 2,
              marginTop: 20,
            }}
          >
            {sevLevels.map((lv) => {
              const w = m.sevTotal ? (m.severity[lv] / m.sevTotal) * 100 * reveal : 0;
              return w ? (
                <div
                  key={lv}
                  style={{ width: `${w}%`, background: SEVERITY_COLOR[lv], borderRadius: 999, transition: "width 0.3s linear" }}
                />
              ) : null;
            })}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "9px 26px", marginTop: 18 }}>
            {sevLevels.map((lv) => (
              <div
                key={lv}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  paddingBottom: 9,
                  borderBottom: "1px solid var(--line)",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 9,
                    fontSize: 13,
                    color: "var(--ink-2)",
                    textTransform: "capitalize",
                  }}
                >
                  <span style={{ width: 8, height: 8, borderRadius: 999, background: SEVERITY_COLOR[lv] }} />
                  {lv}
                </span>
                <span className="tnum" style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>
                  {m.severity[lv]}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="app-card" style={{ ...cardBase, padding: "22px 24px" }}>
          <p style={{ margin: 0, fontSize: 13.5, fontWeight: 600, color: "var(--ink)" }}>Findings composition</p>
          <p style={{ margin: "6px 0 0", fontSize: 12.5, color: "var(--ink-3)" }}>
            Pass signals, gaps, and violations across the run.
          </p>
          <div style={{ display: "grid", gap: 17, marginTop: 24 }}>
            {findRows.map((f) => (
              <div key={f.key} style={{ display: "grid", gridTemplateColumns: "96px 1fr 30px", alignItems: "center", gap: 14 }}>
                <span style={{ fontSize: 13, color: "var(--ink-2)" }}>{f.label}</span>
                <div style={{ height: 8, width: "100%", background: "var(--paper-3)", borderRadius: 999, overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%",
                      width: `${m.findTotal ? (m.findings[f.key] / m.findTotal) * 100 * reveal : 0}%`,
                      background: FINDING_META[f.key].fill,
                      borderRadius: 999,
                      transition: "width 0.3s linear",
                    }}
                  />
                </div>
                <span className="tnum" style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)", textAlign: "right" }}>
                  {m.findings[f.key]}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* explorer + detail */}
      <div style={{ display: "grid", gridTemplateColumns: "1.25fr 1fr", gap: 16, marginTop: 16, alignItems: "start" }}>
        <div className="app-card" style={{ ...cardBase, overflow: "hidden" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "18px 22px",
              borderBottom: "1px solid var(--line)",
            }}
          >
            <div>
              <p style={{ margin: 0, fontSize: 13.5, fontWeight: 600, color: "var(--ink)" }}>Control explorer</p>
              <p style={{ margin: "5px 0 0", fontSize: 12, color: "var(--ink-3)" }}>
                Ranked by risk, then confidence. Click to inspect.
              </p>
            </div>
            <span style={tagBrand}>{controlRows.length} of {m.total}</span>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "74px 1fr 100px 116px",
              gap: 14,
              padding: "11px 22px",
              borderBottom: "1px solid var(--line-2)",
              background: "var(--paper-2)",
            }}
          >
            {["Control", "Title", "Status", "Confidence"].map((h, i) => (
              <span
                key={h}
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 9.5,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  color: "var(--ink-4)",
                  textAlign: i === 3 ? "right" : "left",
                }}
              >
                {h}
              </span>
            ))}
          </div>
          <div className="scroll-quiet" style={{ maxHeight: 560, overflow: "auto" }}>
            {controlRows.length === 0 ? (
              <div style={{ padding: "48px 22px", textAlign: "center", color: "var(--ink-4)", fontSize: 13.5 }}>
                No controls match “{search}”.
              </div>
            ) : (
              controlRows.map((c) => {
                const key = getControlKey(c);
                const sel = key === selectedKey;
                const meta = STATUS_META[c.status];
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSelectedKey(key)}
                    className="app-row"
                    style={{
                      width: "100%",
                      textAlign: "left",
                      border: "none",
                      borderBottom: "1px solid var(--line)",
                      background: sel ? "var(--paper-2)" : "transparent",
                      padding: "15px 22px",
                      cursor: "pointer",
                      position: "relative",
                      display: "block",
                      transition: "background 140ms",
                    }}
                  >
                    <span
                      style={{
                        position: "absolute",
                        left: 0,
                        top: 0,
                        bottom: 0,
                        width: 3,
                        background: sel ? meta.fill : "transparent",
                      }}
                    />
                    <div style={{ display: "grid", gridTemplateColumns: "74px 1fr 100px 116px", gap: 14, alignItems: "center" }}>
                      <span className="mono" style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ink)" }}>
                        {c.regulation_id}
                      </span>
                      <span
                        style={{
                          fontSize: 13,
                          lineHeight: 1.4,
                          color: "var(--ink-2)",
                          overflow: "hidden",
                          display: "-webkit-box",
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: "vertical",
                        }}
                      >
                        {c.title}
                      </span>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "2px 8px",
                          borderRadius: "var(--r-pill)",
                          border: `1px solid ${meta.line}`,
                          background: meta.bg,
                          color: meta.color,
                          fontFamily: "var(--font-mono)",
                          fontSize: 9.5,
                          fontWeight: 500,
                          letterSpacing: "0.05em",
                          textTransform: "uppercase",
                          whiteSpace: "nowrap",
                          justifySelf: "start",
                        }}
                      >
                        <span style={{ width: 6, height: 6, borderRadius: 999, background: meta.color }} />
                        {meta.label}
                      </span>
                      <div style={{ display: "flex", alignItems: "center", gap: 9, justifyContent: "flex-end" }}>
                        <div
                          style={{
                            position: "relative",
                            width: 44,
                            height: 20,
                            borderRadius: 5,
                            background: "var(--paper-3)",
                            overflow: "hidden",
                            flexShrink: 0,
                          }}
                        >
                          <div
                            style={{
                              position: "absolute",
                              inset: 0,
                              background: meta.fill,
                              opacity: 0.18 + c.confidence * 0.7,
                              borderRadius: 5,
                            }}
                          />
                        </div>
                        <span
                          className="tnum mono"
                          style={{ fontSize: 12, color: "var(--ink-2)", minWidth: 34, textAlign: "right" }}
                        >
                          {pct(c.confidence * 100)}
                        </span>
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        <div className="app-card" style={{ ...cardBase, padding: 24, position: "sticky", top: 0 }}>
          <ControlDetail control={selectedControl} />
        </div>
      </div>

      {/* raw output */}
      <div style={{ marginTop: 24 }}>
        <button
          type="button"
          onClick={() => setRawOpen((o) => !o)}
          style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            padding: "0 0 16px",
            border: "none",
            borderBottom: "1px solid var(--line)",
            background: "transparent",
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          <div>
            <p style={eyebrowMono}>Raw validation output</p>
            <p style={{ margin: "8px 0 0", fontSize: 13, color: "var(--ink-3)" }}>
              The structured payload, kept available for audit and debugging.
            </p>
          </div>
          <Icon
            name="chevronDown"
            size={18}
            style={{ color: "var(--ink-3)", transform: rawOpen ? "rotate(180deg)" : "none", transition: "transform 180ms" }}
          />
        </button>
        {rawOpen ? (
          <pre
            className="anim-fade-in scroll-quiet"
            style={{
              marginTop: 18,
              padding: 20,
              background: "var(--paper-2)",
              border: "1px solid var(--line)",
              borderRadius: "var(--r)",
              overflowX: "auto",
              maxHeight: 360,
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              lineHeight: 1.65,
              color: "var(--ink-2)",
            }}
          >
            {rawJson}
          </pre>
        ) : null}
      </div>

      {toast ? (
        <div
          style={{
            position: "fixed",
            left: 0,
            right: 0,
            bottom: 28,
            zIndex: 70,
            display: "flex",
            justifyContent: "center",
            pointerEvents: "none",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              background: "var(--ink)",
              color: "var(--paper)",
              borderRadius: "var(--r-pill)",
              padding: "11px 20px",
              boxShadow: "var(--shadow-lg)",
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            <Icon name="check" size={14} strokeWidth={2.4} style={{ color: "var(--brand)" }} />
            {toast}
          </div>
        </div>
      ) : null}
    </div>
  );
}
