"use client";

import * as React from "react";

import { STATUS_META, type StatusKey } from "@/lib/compliance-theme";

type Segment = { label: StatusKey; count: number; color: string };

/* Outcome-distribution donut. Hover a segment to focus it; the center
   reflects the hovered segment's count, else the total. */
export function Donut({
  segments,
  total,
  reveal,
  hover,
  onHover,
}: {
  segments: Segment[];
  total: number;
  reveal: number;
  hover: StatusKey | null;
  onHover: (label: StatusKey | null) => void;
}) {
  const size = 168;
  const stroke = 22;
  const r = (size - stroke) / 2 - 2;
  const c = size / 2;
  const circ = 2 * Math.PI * r;

  let acc = 0;
  const arcs = segments.map((s) => {
    const frac = total ? s.count / total : 0;
    const len = frac * circ * reveal;
    const arc = {
      label: s.label,
      color: s.color,
      dashArray: `${Math.max(len - 1.5, 0)} ${circ}`,
      offset: -acc,
    };
    acc += frac * circ;
    return arc;
  });

  const active = hover ? segments.find((s) => s.label === hover) : null;
  const centerColor = active ? active.color : "var(--ink)";

  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={c} cy={c} r={r} fill="none" stroke="var(--paper-3)" strokeWidth={stroke} />
        {arcs.map((a) => (
          <circle
            key={a.label}
            cx={c}
            cy={c}
            r={r}
            fill="none"
            stroke={a.color}
            strokeWidth={hover === a.label ? stroke + 4 : stroke}
            strokeDasharray={a.dashArray}
            strokeDashoffset={a.offset}
            style={{
              transition: "stroke-width 160ms ease, opacity 160ms ease",
              cursor: "default",
              opacity: hover && hover !== a.label ? 0.32 : 1,
            }}
            onMouseEnter={() => onHover(a.label)}
            onMouseLeave={() => onHover(null)}
          />
        ))}
      </svg>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          pointerEvents: "none",
        }}
      >
        <span
          className="tnum"
          style={{ fontSize: 36, fontWeight: 600, letterSpacing: "-0.03em", lineHeight: 1, color: centerColor }}
        >
          {active ? active.count : Math.round(total * reveal)}
        </span>
        <span
          className="mono"
          style={{
            fontSize: 9.5,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: centerColor,
            marginTop: 4,
          }}
        >
          {active ? STATUS_META[active.label].label : "Controls"}
        </span>
      </div>
    </div>
  );
}
