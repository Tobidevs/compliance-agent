# Compliance Validation Agent — Frontend

Next.js (App Router) dashboard for the SOC 2 & GDPR compliance validation agent.
Drop-in replacement for the previous `frontend/` folder — the backend API contract,
stream protocol, and data types are preserved verbatim.

## Quick start

```bash
npm install
cp .env.local.example .env.local   # point NEXT_PUBLIC_API_BASE_URL at your backend
npm run dev                        # http://localhost:3000
```

Build / run production:

```bash
npm run build
npm start
```

## Backend wiring (unchanged)

- **Endpoint:** `POST ${NEXT_PUBLIC_API_BASE_URL}/api/stream` (defaults to `http://127.0.0.1:8000`).
- **Request body:** `{ framework, category, source_code_categories, repo_owner, repo_name }`.
- **Response:** server-sent events — `data: {json}\n\n` — with `status`, `token`,
  `update` / `updates`, `done`, and `error` event types.
- The stream parser, payload normalization, error formatting, metric math, and
  control sort order are ported unchanged from the original app
  (`src/lib/stream.ts`, `src/lib/compliance-theme.ts`).

> **Scope strings matter.** The values in `src/lib/constants.ts`
> (`FRAMEWORKS`, `CATEGORIES`, `SCOPE_OPTIONS`) must match the backend exactly —
> it filters control retrieval with `category $eq`, so a mismatch returns zero controls.

## Architecture

This is the **Command Center** design: a persistent app shell (sidebar + topbar)
with the flow split across three real routes that share one run via context.

```
src/
  app/
    layout.tsx          ThemeProvider → ReviewProvider → AppShell → route
    page.tsx            "/"          New review (intake form)
    run/page.tsx        "/run"       Live run (stream-driven stepper)
    results/page.tsx    "/results"   Readiness dashboard
    globals.css         design tokens (light + dark), keyframes, print styles
  context/
    ReviewProvider.tsx  form + SSE run + parsed results + routing (the state machine)
    ThemeProvider.tsx   light/dark, persisted to localStorage, sets <html data-theme>
  components/
    shell/              AppShell, Sidebar, Topbar
    compliance/         IntakeForm, RunningView, ResultsDashboard, Gauge, Donut,
                        ControlDetail, Select
    icons.tsx           inline SVG icon set
  hooks/useReveal.ts    count-up / chart draw-in progress (respects reduced-motion)
  lib/
    types.ts            ControlValidation, ValidationFinding, StreamEvent
    compliance-theme.ts status/severity/finding metadata, ordering, computeMetrics
    stream.ts           runComplianceStream + payload parsing/normalization
    constants.ts        framework / category / scope option lists
    export.ts           CSV download, print-to-PDF, copy-summary
    utils.ts            cn() class helper
```

### Flow

1. **`/`** — configure framework, category, scope families, and repo. Submit calls
   `submitReview()`, which `router.push("/run")` and opens the SSE stream.
2. **`/run`** — the stepper advances from real `status` events (`stepIndex` is derived
   from the status tick); the live status message shows under the active step.
3. **`/results`** — on the `done` event the agent's results render: posture gauge,
   outcome donut, severity exposure, findings composition, and a searchable control
   explorer feeding the detail panel. Deep-linking to `/run` or `/results` with no
   active run redirects back to `/`.

## Features

- **Light / dark theme** with persistence (sidebar toggle; respects system preference on first load).
- **⌘K** focuses the control search; the explorer filters live on the results screen.
- **Export report** → CSV download, print-to-PDF (uses the `@media print` stylesheet), or copy summary.
- **Sidebar nav** as real routes. Library items (Catalog, Evidence vault, Settings) are intentional placeholders.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` | Base URL of the compliance backend |

## Notes

- Styling follows the prototype: CSS variables in `globals.css` + inline styles in components.
  No Tailwind utility classes are used in the components (Tailwind's reset/preflight is still loaded).
- Dependencies were trimmed to what this design uses (`clsx`, `tailwind-merge`). The previous
  Radix / lucide / cva packages are no longer imported — re-add them if other tooling needs them.
