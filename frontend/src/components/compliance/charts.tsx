"use client";

import * as React from "react";
import { STATUS_META, clamp, type StatusKey } from "@/lib/compliance-theme";

/* Charts — strongly differentiated:
   PostureGauge  = single hero KPI as a 270° brand-orange gauge.
   ConfidenceRing = compact secondary signal, thin full ink ring.
   StatusDonut   = categorical status mix in semantic vivid colors. */

export function PostureGauge({ value }: { value: number }) {
  const v = clamp(value);
  const size = 200, stroke = 14, r = (size - stroke) / 2 - 6, cx = size / 2, cy = size / 2;
  const start = 135, sweep = 270;
  const circ = 2 * Math.PI * r;
  const arcLen = (sweep / 360) * circ;
  const off = arcLen - (v / 100) * arcLen;
  const grade = v >= 80 ? "Strong" : v >= 55 ? "Developing" : v >= 30 ? "At risk" : "Critical";
  const gradeColor = v >= 80 ? "var(--pass)" : v >= 55 ? "var(--brand-600)" : v >= 30 ? "var(--partial)" : "var(--fail)";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div style={{ position: "relative", width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: `rotate(${start}deg)` }} aria-hidden="true">
          <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--paper-3)" strokeWidth={stroke}
            strokeLinecap="round" strokeDasharray={`${arcLen} ${circ}`} />
          <circle className="ring-progress" cx={cx} cy={cy} r={r} fill="none" stroke="var(--brand)" strokeWidth={stroke}
            strokeLinecap="round" strokeDasharray={`${arcLen} ${circ}`} strokeDashoffset={off}
            style={{ "--ring-len": arcLen, "--ring-off": off } as React.CSSProperties} />
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <span className="tnum" style={{ fontSize: 52, fontWeight: 600, letterSpacing: "-0.03em", color: "var(--ink)", lineHeight: 1 }}>{Math.round(v)}</span>
          <span className="eyebrow-muted" style={{ marginTop: 6 }}>Posture</span>
        </div>
      </div>
      <span style={{ marginTop: 2, display: "inline-flex", alignItems: "center", gap: 7, fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: gradeColor }}>
        <span style={{ width: 6, height: 6, borderRadius: 999, background: gradeColor }} />{grade}
      </span>
    </div>
  );
}

export function ConfidenceRing({ value, size = 124 }: { value: number; size?: number }) {
  const v = clamp(value);
  const stroke = 7, r = (size - stroke) / 2 - 2, cx = size / 2, cy = size / 2;
  const circ = 2 * Math.PI * r;
  const off = circ - (v / 100) * circ;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }} aria-hidden="true">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--paper-3)" strokeWidth={stroke} />
        <circle className="ring-progress" cx={cx} cy={cy} r={r} fill="none" stroke="var(--ink-2)" strokeWidth={stroke}
          strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={off}
          style={{ "--ring-len": circ, "--ring-off": off } as React.CSSProperties} />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <span className="tnum" style={{ fontSize: Math.round(size * 0.2), fontWeight: 600, letterSpacing: "-0.02em", color: "var(--ink)", lineHeight: 1 }}>{Math.round(v)}</span>
        <span className="mono" style={{ marginTop: 4, fontSize: Math.max(7.5, size * 0.072), fontWeight: 500, letterSpacing: "0.04em", textTransform: "uppercase", color: "var(--ink-3)" }}>Confidence</span>
      </div>
    </div>
  );
}

type Segment = { label: StatusKey; count: number; color: string };
export function StatusDonut({ segments, total, size = 188 }: { segments: Segment[]; total: number; size?: number }) {
  const stroke = 20, r = (size - stroke) / 2 - 2, cx = size / 2, cy = size / 2;
  const circ = 2 * Math.PI * r;
  const [hover, setHover] = React.useState<StatusKey | null>(null);
  let acc = 0;
  const arcs = segments.map((s) => {
    const frac = total ? s.count / total : 0;
    const len = frac * circ;
    const arc = { ...s, len, offset: -acc, frac };
    acc += len;
    return arc;
  });
  const active = hover != null ? arcs.find((a) => a.label === hover) : null;
  return (
    <div style={{ position: "relative", width: size, height: size, margin: "0 auto" }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--paper-3)" strokeWidth={stroke} />
        {arcs.map((a) => a.count ? (
          <circle key={a.label} cx={cx} cy={cy} r={r} fill="none" stroke={a.color}
            strokeWidth={hover === a.label ? stroke + 3 : stroke}
            strokeDasharray={`${Math.max(a.len - 1.5, 0)} ${circ}`} strokeDashoffset={a.offset}
            style={{ transition: "stroke-width 160ms ease", cursor: "pointer", opacity: hover && hover !== a.label ? 0.35 : 1 }}
            onMouseEnter={() => setHover(a.label)} onMouseLeave={() => setHover(null)} />
        ) : null)}
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", pointerEvents: "none" }}>
        <span className="tnum" style={{ fontSize: Math.round(size * 0.21), fontWeight: 600, letterSpacing: "-0.03em", color: active ? active.color : "var(--ink)", lineHeight: 1, transition: "color 160ms" }}>
          {active ? active.count : total}
        </span>
        <span className="mono" style={{ marginTop: 5, fontSize: Math.max(8, size * 0.058), fontWeight: 500, letterSpacing: "0.04em", textTransform: "uppercase", color: active ? active.color : "var(--ink-3)", maxWidth: size * 0.78, textAlign: "center", lineHeight: 1.1 }}>
          {active ? STATUS_META[active.label].label : "Controls"}
        </span>
      </div>
    </div>
  );
}
