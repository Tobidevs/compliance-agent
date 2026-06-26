"use client";

import * as React from "react";

import { Icon } from "@/components/icons";

/* Custom dropdown select matching the prototype (no native <select>). */
export function Select({
  value,
  placeholder,
  options,
  onChange,
  format,
}: {
  value: string;
  placeholder: string;
  options: string[];
  onChange: (v: string) => void;
  format?: (v: string) => string;
}) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const display = value ? (format ? format(value) : value) : placeholder;

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        type="button"
        className="focusable"
        onClick={() => setOpen((o) => !o)}
        style={{
          height: 44,
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 14px",
          borderRadius: "var(--r-sm)",
          border: `1px solid ${open ? "var(--brand)" : "var(--line-2)"}`,
          background: "var(--paper)",
          color: value ? "var(--ink)" : "var(--ink-4)",
          fontSize: 14,
          fontFamily: "var(--font-sans)",
          cursor: "pointer",
          transition: "border-color 140ms",
          boxShadow: open ? "0 0 0 3px var(--brand-50)" : "none",
        }}
      >
        <span>{display}</span>
        <Icon
          name="chevronDown"
          size={16}
          strokeWidth={1.9}
          style={{
            stroke: "var(--ink-3)",
            transform: open ? "rotate(180deg)" : "none",
            transition: "transform 160ms",
          }}
        />
      </button>
      {open ? (
        <div
          className="anim-fade-in"
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            left: 0,
            right: 0,
            zIndex: 30,
            background: "var(--paper)",
            border: "1px solid var(--line-2)",
            borderRadius: "var(--r-sm)",
            boxShadow: "var(--shadow-lg)",
            padding: 5,
            overflow: "hidden",
          }}
        >
          {options.map((opt) => {
            const sel = opt === value;
            return (
              <button
                key={opt}
                type="button"
                onClick={() => {
                  onChange(opt);
                  setOpen(false);
                }}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 10,
                  padding: "10px 11px",
                  borderRadius: "var(--r-xs)",
                  border: "none",
                  background: sel ? "var(--brand-50)" : "transparent",
                  color: "var(--ink)",
                  fontSize: 13.5,
                  fontFamily: "var(--font-sans)",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "background 120ms",
                }}
                onMouseEnter={(e) => {
                  if (!sel) e.currentTarget.style.background = "var(--paper-3)";
                }}
                onMouseLeave={(e) => {
                  if (!sel) e.currentTarget.style.background = "transparent";
                }}
              >
                <span>{format ? format(opt) : opt}</span>
                {sel ? <Icon name="check" size={15} strokeWidth={2.2} style={{ stroke: "var(--brand-600)" }} /> : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
