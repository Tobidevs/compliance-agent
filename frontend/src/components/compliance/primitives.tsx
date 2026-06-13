"use client";

import * as React from "react";
import { Icon } from "./Icon";
import {
  STATUS_META,
  SEVERITY_COLOR,
  FINDING_META,
  type StatusKey,
  type SeverityKey,
  type FindingKey,
} from "@/lib/compliance-theme";

/* ---------- StatusBadge ---------- */
export function StatusBadge({ status, size = "md" }: { status: StatusKey; size?: "sm" | "md" }) {
  const m = STATUS_META[status];
  return (
    <span
      style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        padding: size === "sm" ? "2px 8px" : "3px 10px 3px 8px",
        borderRadius: "var(--r-pill)", border: `1px solid ${m.line}`, background: m.bg,
        color: m.color, fontFamily: "var(--font-mono)", fontSize: size === "sm" ? 10.5 : 11,
        fontWeight: 500, letterSpacing: "0.06em", textTransform: "uppercase", whiteSpace: "nowrap",
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: 999, background: m.color }} />
      {m.label}
    </span>
  );
}

/* ---------- SeverityBadge ---------- */
export function SeverityBadge({ severity }: { severity: SeverityKey | null | undefined }) {
  if (!severity) return <span style={{ color: "var(--ink-4)", fontSize: 13 }}>—</span>;
  const c = SEVERITY_COLOR[severity];
  return (
    <span
      style={{
        display: "inline-flex", alignItems: "center", gap: 6, padding: "2px 9px",
        borderRadius: "var(--r-pill)", border: `1px solid ${c}33`, background: `${c}14`,
        color: c, fontFamily: "var(--font-mono)", fontSize: 10.5, fontWeight: 500,
        letterSpacing: "0.06em", textTransform: "capitalize",
      }}
    >
      {severity}
    </span>
  );
}

/* ---------- FindingBadge ---------- */
export function FindingBadge({ type }: { type: FindingKey }) {
  const m = FINDING_META[type] ?? FINDING_META.gap;
  return (
    <span
      style={{
        display: "inline-flex", alignItems: "center", padding: "2px 9px",
        borderRadius: "var(--r-pill)", border: `1px solid ${m.line}`, background: m.bg,
        color: m.color, fontFamily: "var(--font-mono)", fontSize: 10.5, fontWeight: 500,
        letterSpacing: "0.06em", textTransform: "uppercase",
      }}
    >
      {m.label}
    </span>
  );
}

/* ---------- Tag (neutral metadata chip) ---------- */
export function Tag({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "brand" }) {
  const tones = {
    neutral: { color: "var(--ink-3)", border: "var(--line-2)", bg: "transparent" },
    brand: { color: "var(--brand-700)", border: "var(--brand-line)", bg: "var(--brand-50)" },
  } as const;
  const t = tones[tone];
  return (
    <span
      style={{
        display: "inline-flex", alignItems: "center", gap: 6, padding: "3px 10px",
        borderRadius: "var(--r-pill)", border: `1px solid ${t.border}`, background: t.bg,
        color: t.color, fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 500,
        letterSpacing: "0.08em", textTransform: "uppercase",
      }}
    >
      {children}
    </span>
  );
}

/* ---------- Button ---------- */
type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
  iconLeft?: React.ReactNode;
  iconRight?: React.ReactNode;
};
export function Button({
  children, variant = "default", size = "md", iconLeft, iconRight, disabled, ...props
}: ButtonProps) {
  const [hover, setHover] = React.useState(false);
  const sizes = {
    md: { height: 44, padding: "0 22px", fontSize: 14 },
    sm: { height: 36, padding: "0 14px", fontSize: 13 },
    lg: { height: 50, padding: "0 28px", fontSize: 15 },
  } as const;
  const base: React.CSSProperties = {
    display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 9,
    borderRadius: "var(--r-sm)", fontFamily: "var(--font-sans)", fontWeight: 500,
    cursor: "pointer", border: "1px solid transparent", transition: "all 140ms ease",
    ...sizes[size],
  };
  const variants: Record<string, React.CSSProperties> = {
    default: { background: "var(--brand)", color: "#fff", boxShadow: "var(--shadow-sm)" },
    outline: { background: "var(--paper)", color: "var(--ink)", border: "1px solid var(--line-2)" },
    ghost: { background: "transparent", color: "var(--ink-2)" },
  };
  const hoverStyle: React.CSSProperties = hover
    ? variant === "default"
      ? { background: "var(--brand-600)" }
      : variant === "outline"
        ? { background: "var(--brand-50)", borderColor: "var(--brand-line)", color: "var(--brand-700)" }
        : { background: "var(--paper-3)", color: "var(--ink)" }
    : {};
  return (
    <button
      className="focusable"
      style={{ ...base, ...variants[variant], ...hoverStyle, opacity: disabled ? 0.5 : 1, pointerEvents: disabled ? "none" : "auto" }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      disabled={disabled}
      {...props}
    >
      {iconLeft}{children}{iconRight}
    </button>
  );
}

/* ---------- Progress (thin, refined) ---------- */
export function Progress({
  value, color = "var(--brand)", track = "var(--paper-3)", height = 6, animate = true,
}: {
  value: number; color?: string; track?: string; height?: number; animate?: boolean;
}) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div style={{ height, width: "100%", background: track, borderRadius: 999, overflow: "hidden" }}>
      <div className={animate ? "bar-grow" : ""} style={{ height: "100%", width: `${v}%`, background: color, borderRadius: 999 }} />
    </div>
  );
}

/* ---------- Separator ---------- */
export function Sep({ style }: { style?: React.CSSProperties }) {
  return <div aria-hidden="true" style={{ height: 1, width: "100%", background: "var(--line)", ...style }} />;
}

/* ---------- SectionLabel ---------- */
export function SectionLabel({
  label, caption, right,
}: {
  label: string; caption?: string; right?: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16 }}>
      <div>
        <p className="eyebrow-muted" style={{ margin: 0 }}>{label}</p>
        {caption ? <p style={{ margin: "8px 0 0", fontSize: 14, lineHeight: 1.5, color: "var(--ink-3)" }}>{caption}</p> : null}
      </div>
      {right}
    </div>
  );
}
