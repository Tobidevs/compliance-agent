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
  const [reveal, setReveal] = useState(active ? 0 : 1);
  const rafRef = useRef<number | undefined>(undefined);
  const safetyRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    if (!active) {
      setReveal(1);
      return;
    }

    const prefersReduced =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (!enabled || prefersReduced) {
      setReveal(1);
      return;
    }

    setReveal(0);
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setReveal(eased);
      if (p < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    safetyRef.current = setTimeout(() => setReveal(1), duration + 200);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      if (safetyRef.current) clearTimeout(safetyRef.current);
    };
  }, [active, enabled, duration]);

  return reveal;
}
