"use client";

import * as React from "react";

import { Icon } from "@/components/icons";
import { WORKFLOW_STEPS } from "@/lib/compliance-theme";
import { useReview } from "@/context/ReviewProvider";

export function RunningView() {
  const { stepIndex, status, repoLabel } = useReview();
  const steps = WORKFLOW_STEPS;
  const allDone = stepIndex >= steps.length;

  return (
    <div className="anim-fade-up" style={{ maxWidth: 680, margin: "0 auto", padding: "52px 32px 80px" }}>
      <div style={{ textAlign: "center" }}>
        <span
          style={{
            display: "inline-grid",
            placeItems: "center",
            width: 56,
            height: 56,
            borderRadius: 999,
            border: "1px solid var(--brand-line)",
            background: "var(--brand-50)",
            marginBottom: 20,
          }}
        >
          <Icon
            name="spinner"
            size={24}
            strokeWidth={1.8}
            style={{ stroke: "var(--brand-600)", animation: "app-spin 1.6s linear infinite" }}
          />
        </span>
        <h2 style={{ margin: 0, fontSize: 27, fontWeight: 600, color: "var(--ink)" }}>Running compliance checks</h2>
        <p style={{ margin: "12px 0 0", fontSize: 14.5, lineHeight: 1.6, color: "var(--ink-3)" }}>
          Analyzing <span className="mono" style={{ color: "var(--ink-2)" }}>{repoLabel}</span> — each stage completes
          in sequence.
        </p>
      </div>

      <div
        style={{
          marginTop: 36,
          border: "1px solid var(--line)",
          borderRadius: "var(--r-lg)",
          background: "var(--paper)",
          boxShadow: "var(--shadow)",
          overflow: "hidden",
        }}
      >
        {steps.map((s, i) => {
          const done = i < stepIndex || allDone;
          const active = i === stepIndex && !allDone;
          return (
            <div
              key={s.key}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 15,
                padding: "17px 22px",
                borderTop: i ? "1px solid var(--line)" : "none",
                background: active ? "var(--brand-50)" : "transparent",
                transition: "background 300ms",
              }}
            >
              <span
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: 999,
                  flexShrink: 0,
                  display: "grid",
                  placeItems: "center",
                  border: `1.5px solid ${done ? "var(--pass)" : active ? "var(--brand)" : "var(--line-2)"}`,
                  background: done ? "var(--pass)" : "transparent",
                  transition: "all 300ms",
                }}
              >
                {done ? (
                  <Icon name="check" size={13} strokeWidth={3} style={{ stroke: "#fff" }} />
                ) : active ? (
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: 999,
                      background: "var(--brand)",
                      animation: "app-pulse 1.1s ease-in-out infinite",
                    }}
                  />
                ) : (
                  <span style={{ width: 6, height: 6, borderRadius: 999, background: "var(--line-2)" }} />
                )}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p
                  style={{
                    margin: 0,
                    fontSize: 14.5,
                    fontWeight: active || done ? 500 : 400,
                    color: active ? "var(--ink)" : done ? "var(--ink-2)" : "var(--ink-4)",
                  }}
                >
                  {s.label}
                </p>
                <p
                  className="mono"
                  style={{
                    margin: "3px 0 0",
                    fontSize: 12.5,
                    color: "var(--ink-4)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {active && status ? status : s.detail}
                </p>
              </div>
              {done ? (
                <span
                  className="mono"
                  style={{ fontSize: 10.5, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--pass)" }}
                >
                  Done
                </span>
              ) : active ? (
                <span
                  className="mono"
                  style={{
                    fontSize: 10.5,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    color: "var(--brand-600)",
                  }}
                >
                  Running
                </span>
              ) : null}
            </div>
          );
        })}
        <div style={{ height: 4, background: "var(--paper-3)", overflow: "hidden" }}>
          <div
            style={{
              height: "100%",
              width: `${(Math.min(stepIndex, steps.length) / steps.length) * 100}%`,
              background: "var(--brand)",
              transition: "width 0.5s cubic-bezier(0.22,1,0.36,1)",
            }}
          />
        </div>
      </div>
    </div>
  );
}
