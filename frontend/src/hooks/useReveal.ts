"use client";

import { useEffect, useRef, useState } from "react";

/* ============================================================
   useReveal — drives the dashboard's count-ups and chart draw-ins.
   Returns a 0→1 progress value that eases in over `duration` once
   `active` is true. Respects prefers-reduced-motion and the
   `enabled` flag (jumps straight to 1). A safety timeout guarantees
   the resting value of 1 even if rAF is throttled.
   ============================================================ */
export function useReveal(active: boolean, enabled = true, duration = 950) {
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | undefined>(undefined);
  const safetyRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    if (!active) return;

    const prefersReduced =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (!enabled || prefersReduced) {
      // Settled in a frame callback rather than the effect body: a synchronous setState
      // there cascades an extra render on every mount.
      rafRef.current = requestAnimationFrame(() => setProgress(1));
      return () => {
        if (rafRef.current) cancelAnimationFrame(rafRef.current);
      };
    }

    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setProgress(eased);
      if (p < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    safetyRef.current = setTimeout(() => setProgress(1), duration + 200);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      if (safetyRef.current) clearTimeout(safetyRef.current);
    };
  }, [active, enabled, duration]);

  // Derived, not stored: an inactive reveal is fully revealed by definition, so
  // deactivating mid-animation cannot strand the value part-way.
  return active ? progress : 1;
}
