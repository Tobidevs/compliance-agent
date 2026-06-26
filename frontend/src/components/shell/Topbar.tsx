"use client";

import { usePathname } from "next/navigation";
import * as React from "react";

import { Icon } from "@/components/icons";
import { useReview } from "@/context/ReviewProvider";

const TITLES: Record<string, { t: string; s: string }> = {
  "/": { t: "New review", s: "Configure a SOC 2 & GDPR validation run" },
  "/run": { t: "Live run", s: "Compliance agent is analyzing the repository" },
  "/results": { t: "Readiness dashboard", s: "Validation results and findings" },
};

export function Topbar() {
  const pathname = usePathname();
  const { loading, hasResults, search, setSearch } = useReview();
  const inputRef = React.useRef<HTMLInputElement>(null);

  const meta = TITLES[pathname] ?? TITLES["/"];
  const onResults = pathname.startsWith("/results");

  // ⌘K / Ctrl-K focuses the control search.
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const chip = loading
    ? { label: "Running", c: "var(--brand-700)", bg: "var(--brand-50)", pulse: true }
    : hasResults && onResults
      ? { label: "Complete", c: "var(--pass)", bg: "var(--pass-bg)", pulse: false }
      : { label: "Idle", c: "var(--ink-3)", bg: "var(--paper-3)", pulse: false };

  return (
    <header
      style={{
        height: 60,
        flexShrink: 0,
        borderBottom: "1px solid var(--line)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 20,
        padding: "0 26px",
        background: "var(--paper)",
      }}
    >
      <div style={{ minWidth: 0 }}>
        <p style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "var(--ink)", letterSpacing: "-0.01em" }}>
          {meta.t}
        </p>
        <p
          style={{
            margin: "1px 0 0",
            fontSize: 12,
            color: "var(--ink-3)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {meta.s}
        </p>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
        <div
          className="focusable"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            height: 34,
            padding: "0 12px",
            border: "1px solid var(--line)",
            borderRadius: "var(--r-sm)",
            color: "var(--ink-4)",
            background: "var(--paper-2)",
            minWidth: 200,
          }}
        >
          <Icon name="search" size={15} strokeWidth={1.9} />
          <input
            ref={inputRef}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search controls…"
            style={{
              flex: 1,
              minWidth: 0,
              border: "none",
              outline: "none",
              background: "transparent",
              fontSize: 13,
              color: "var(--ink)",
              fontFamily: "var(--font-sans)",
            }}
          />
          <span
            className="mono"
            style={{
              marginLeft: "auto",
              fontSize: 10.5,
              border: "1px solid var(--line-2)",
              borderRadius: 5,
              padding: "1px 5px",
              color: "var(--ink-4)",
            }}
          >
            ⌘K
          </span>
        </div>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 7,
            height: 30,
            padding: "0 12px",
            borderRadius: "var(--r-pill)",
            background: chip.bg,
            color: chip.c,
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            fontWeight: 500,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: 999,
              background: chip.c,
              animation: chip.pulse ? "app-pulse 1.1s ease-in-out infinite" : undefined,
            }}
          />
          {chip.label}
        </span>
      </div>
    </header>
  );
}
