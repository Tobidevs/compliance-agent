"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";

import { Icon, type IconName } from "@/components/icons";
import { useReview } from "@/context/ReviewProvider";
import { useTheme } from "@/context/ThemeProvider";

type NavItem = { href: string; label: string; icon: IconName };

const WORKFLOW: NavItem[] = [
  { href: "/", label: "New review", icon: "fileText" },
  { href: "/run", label: "Live run", icon: "activity" },
  { href: "/results", label: "Results", icon: "layers" },
];

const LIBRARY: NavItem[] = [
  { href: "#", label: "Control catalog", icon: "grid" },
  { href: "#", label: "Evidence vault", icon: "folder" },
  { href: "#", label: "Settings", icon: "settings" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const { loading, hasResults } = useReview();

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  const navStyle = (active: boolean): React.CSSProperties => ({
    display: "flex",
    alignItems: "center",
    gap: 12,
    width: "100%",
    padding: "9px 12px",
    borderRadius: "var(--r-sm)",
    border: "none",
    cursor: "pointer",
    fontSize: 13.5,
    fontFamily: "var(--font-sans)",
    fontWeight: active ? 600 : 500,
    transition: "background 140ms, color 140ms",
    background: active ? "var(--side-2)" : "transparent",
    color: active ? "var(--side-ink)" : "var(--side-ink-2)",
    textDecoration: "none",
  });

  const themeBtn = (on: boolean): React.CSSProperties => ({
    flex: 1,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    height: 30,
    borderRadius: 7,
    border: "none",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 500,
    fontFamily: "var(--font-sans)",
    transition: "all 140ms",
    background: on ? "var(--brand)" : "transparent",
    color: on ? "#fff" : "var(--side-ink-2)",
  });

  return (
    <aside
      style={{
        width: 248,
        flexShrink: 0,
        height: "100vh",
        background: "var(--side)",
        display: "flex",
        flexDirection: "column",
        borderRight: "1px solid var(--side-line)",
      }}
    >
      <div style={{ padding: "20px 18px 18px", display: "flex", alignItems: "center", gap: 11 }}>
        <span
          style={{
            width: 30,
            height: 30,
            borderRadius: 8,
            background: "var(--brand)",
            display: "grid",
            placeItems: "center",
            flexShrink: 0,
            boxShadow: "0 4px 12px -2px rgba(249,115,22,0.5)",
            color: "#fff",
          }}
        >
          <Icon name="shield" size={17} strokeWidth={2} />
        </span>
        <div style={{ lineHeight: 1.15 }}>
          <p style={{ margin: 0, fontSize: 14.5, fontWeight: 600, color: "var(--side-ink)" }}>Compliance Agent</p>
          <p
            style={{
              margin: 0,
              fontFamily: "var(--font-mono)",
              fontSize: 9.5,
              letterSpacing: "0.16em",
              color: "var(--side-ink-2)",
              textTransform: "uppercase",
            }}
          >
            Command Center
          </p>
        </div>
      </div>

      <div style={{ padding: "6px 12px", display: "flex", flexDirection: "column", gap: 2 }}>
        <p
          style={{
            margin: "14px 10px 7px",
            fontFamily: "var(--font-mono)",
            fontSize: 9.5,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: "var(--side-ink-2)",
          }}
        >
          Workflow
        </p>

        {WORKFLOW.map((item) => {
          const active = isActive(item.href);
          const showPulse = item.href === "/run" && loading;
          const showDot = item.href === "/results" && hasResults;
          return (
            <Link key={item.label} href={item.href} className="app-nav" style={navStyle(active)}>
              <Icon name={item.icon} size={17} />
              <span style={{ flex: 1, textAlign: "left" }}>{item.label}</span>
              {showPulse ? (
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: 999,
                    background: "var(--brand)",
                    animation: "app-pulse 1.1s ease-in-out infinite",
                  }}
                />
              ) : showDot || active ? (
                <span style={{ width: 5, height: 5, borderRadius: 999, background: "var(--brand)" }} />
              ) : null}
            </Link>
          );
        })}

        <p
          style={{
            margin: "18px 10px 7px",
            fontFamily: "var(--font-mono)",
            fontSize: 9.5,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: "var(--side-ink-2)",
          }}
        >
          Library
        </p>
        {LIBRARY.map((item) => (
          <div
            key={item.label}
            title="Coming soon"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "9px 12px",
              borderRadius: "var(--r-sm)",
              color: "var(--side-ink-2)",
              fontSize: 13.5,
              cursor: "default",
            }}
          >
            <Icon name={item.icon} size={17} />
            <span style={{ flex: 1 }}>{item.label}</span>
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: "auto",
          padding: "14px 14px 16px",
          borderTop: "1px solid var(--side-line)",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", background: "var(--side-2)", borderRadius: "var(--r-sm)", padding: 3 }}>
          <button type="button" onClick={() => setTheme("light")} style={themeBtn(theme === "light")}>
            <Icon name="sun" size={14} strokeWidth={1.9} />
            Light
          </button>
          <button type="button" onClick={() => setTheme("dark")} style={themeBtn(theme === "dark")}>
            <Icon name="moon" size={14} strokeWidth={1.9} />
            Dark
          </button>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 4px 0" }}>
          <span
            style={{
              width: 30,
              height: 30,
              borderRadius: 999,
              background: "var(--brand-100)",
              color: "var(--brand-700)",
              display: "grid",
              placeItems: "center",
              fontSize: 12,
              fontWeight: 600,
              fontFamily: "var(--font-mono)",
            }}
          >
            AR
          </span>
          <div style={{ lineHeight: 1.2, minWidth: 0 }}>
            <p
              style={{
                margin: 0,
                fontSize: 12.5,
                fontWeight: 500,
                color: "var(--side-ink)",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              A. Reyes
            </p>
            <p style={{ margin: 0, fontSize: 11, color: "var(--side-ink-2)" }}>Lead Auditor</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
