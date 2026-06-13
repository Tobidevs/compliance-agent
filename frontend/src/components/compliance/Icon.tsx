import * as React from "react";

/* Lucide-matched 2px geometric icon set used across the compliance UI. */
type IconName =
  | "check" | "x" | "chevronDown" | "chevronRight" | "arrowRight" | "minus"
  | "alert" | "shield" | "search" | "git" | "file" | "folder" | "layers"
  | "dot" | "spark";

const PATHS: Record<IconName, React.ReactNode> = {
  check: <polyline points="20 6 9 17 4 12" />,
  x: <><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></>,
  chevronDown: <polyline points="6 9 12 15 18 9" />,
  chevronRight: <polyline points="9 6 15 12 9 18" />,
  arrowRight: <><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></>,
  minus: <line x1="5" y1="12" x2="19" y2="12" />,
  alert: <><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></>,
  shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />,
  search: <><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></>,
  git: <><circle cx="12" cy="12" r="3" /><line x1="3" y1="12" x2="9" y2="12" /><line x1="15" y1="12" x2="21" y2="12" /></>,
  file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></>,
  folder: <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.5l-2-2H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2Z" />,
  layers: <><polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" /></>,
  dot: <circle cx="12" cy="12" r="4" fill="currentColor" stroke="none" />,
  spark: <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" />,
};

export function Icon({
  name,
  size = 16,
  className = "",
  style,
}: {
  name: IconName;
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}) {
  const merged: React.CSSProperties = {
    width: size,
    height: size,
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.75,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    ...style,
  };
  return (
    <svg viewBox="0 0 24 24" className={className} style={merged} aria-hidden="true">
      {PATHS[name]}
    </svg>
  );
}
