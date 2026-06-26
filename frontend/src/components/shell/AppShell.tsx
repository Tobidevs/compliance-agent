"use client";

import * as React from "react";

import { Icon } from "@/components/icons";
import { Sidebar } from "@/components/shell/Sidebar";
import { Topbar } from "@/components/shell/Topbar";
import { useReview } from "@/context/ReviewProvider";

/* ============================================================
   AppShell — persistent dashboard chrome (sidebar + topbar) that
   wraps every route. The route page renders into the scrolling
   content region. The global error toast lives here so it shows
   regardless of which screen is active.
   ============================================================ */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { errorMessage, dismissError } = useReview();

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        width: "100%",
        overflow: "hidden",
        background: "var(--paper)",
        color: "var(--ink)",
        fontFamily: "var(--font-sans)",
        WebkitFontSmoothing: "antialiased",
      }}
    >
      <div data-app-chrome>
        <Sidebar />
      </div>

      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div data-app-chrome>
          <Topbar />
        </div>

        <div data-print-region className="scroll-quiet" style={{ flex: 1, overflow: "auto", minHeight: 0 }}>
          {children}
        </div>
      </div>

      {errorMessage ? (
        <div
          data-app-chrome
          style={{
            position: "fixed",
            insetInline: 0,
            top: 20,
            zIndex: 80,
            display: "flex",
            justifyContent: "center",
            padding: "0 16px",
            pointerEvents: "none",
          }}
        >
          <div
            role="alert"
            aria-live="assertive"
            style={{
              pointerEvents: "auto",
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: 16,
              width: "100%",
              maxWidth: 560,
              border: "1px solid var(--fail-line)",
              background: "var(--fail-bg)",
              borderRadius: "var(--r-lg)",
              padding: "16px 20px",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            <div>
              <p className="eyebrow-muted" style={{ margin: 0, color: "var(--fail)" }}>
                Compliance run failed
              </p>
              <p style={{ margin: "8px 0 0", fontSize: 14, lineHeight: 1.55, color: "var(--ink)" }}>
                {errorMessage}
              </p>
            </div>
            <button
              type="button"
              onClick={dismissError}
              className="focusable"
              style={{
                flexShrink: 0,
                display: "grid",
                placeItems: "center",
                width: 28,
                height: 28,
                borderRadius: "var(--r-pill)",
                border: "1px solid var(--fail-line)",
                background: "transparent",
                color: "var(--fail)",
                cursor: "pointer",
              }}
              aria-label="Dismiss error"
            >
              <Icon name="x" size={14} strokeWidth={2} />
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
