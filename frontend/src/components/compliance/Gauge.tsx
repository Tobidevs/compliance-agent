"use client";

import { clamp } from "@/lib/compliance-theme";

/* Readiness posture gauge — 270° arc, brand fill animated via `reveal`. */
export function Gauge({ value, reveal }: { value: number; reveal: number }) {
  const size = 184;
  const stroke = 14;
  const r = (size - stroke) / 2 - 6;
  const c = size / 2;
  const circ = 2 * Math.PI * r;
  const arc = (270 / 360) * circ;
  const v = clamp(value) * reveal;
  const off = arc - (v / 100) * arc;

  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(135deg)" }}>
        <circle
          cx={c}
          cy={c}
          r={r}
          fill="none"
          stroke="var(--paper-3)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${arc} ${circ}`}
        />
        <circle
          cx={c}
          cy={c}
          r={r}
          fill="none"
          stroke="var(--brand)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${arc} ${circ}`}
          strokeDashoffset={off}
          style={{ transition: "stroke-dashoffset 0.25s linear" }}
        />
      </svg>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span
          className="tnum"
          style={{ fontSize: 48, fontWeight: 600, letterSpacing: "-0.03em", color: "var(--ink)", lineHeight: 1 }}
        >
          {Math.round(v)}
        </span>
        <span
          className="mono"
          style={{
            fontSize: 10,
            letterSpacing: "0.14em",
            textTransform: "uppercase",
            color: "var(--ink-4)",
            marginTop: 5,
          }}
        >
          / 100
        </span>
      </div>
    </div>
  );
}
