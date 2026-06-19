# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working Conventions

- **Do not use git worktrees.** Make any file changes directly in the current working directory. Only use a worktree if I explicitly ask for one. (Background-session worktree isolation is disabled for this repo via `.claude/settings.json` → `"worktree": {"bgIsolation": "none"}`.)
- **Do not add verbose comments.** Make one line comments unless absolutely necessary.

## Project Overview

A full-stack compliance validation application that uses a LangGraph multi-agent workflow to assess whether a GitHub repository meets regulatory/compliance controls. The active control library combines the **SOC 2** and **GDPR** frameworks (surfaced in the UI as "SOC 2 & GDPR"). The backend drives an LLM agent pipeline; the frontend streams real-time results over SSE.

## Development Commands

### Backend (FastAPI + LangGraph)

```bash
cd backend
source .venv/bin/activate            # activate virtualenv
pip install -r requirements.txt      # install deps
uvicorn app.main:app --reload --port 8000   # dev server
curl http://localhost:8000/api/health        # health check
python agent/scripts/data_ingestion.py        # (re)seed the control corpus — see below
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev      # dev server on :3000
npm run build    # production build
npm run lint
```

### Environment

Backend requires `backend/.env` with:
- `OPENAI_API_KEY` — GPT model for policy extraction/validation
- `ANTHROPIC_API_KEY` — Claude (Haiku/Sonnet) for sub-agents
- `PINECONE_API_KEY` — hybrid vector search + reranking of the control corpus
- `GITHUB_PERSONAL_ACCESS_TOKEN` — code retrieval via MCP
- `LANGSMITH_API_KEY` / `LANGSMITH_ENDPOINT` — tracing
- `CHROMA_PERSIST_DIR` — local Chroma path for policy-document RAG (default: `./chroma_db`)

Frontend reads `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://127.0.0.1:8000`).

## Architecture

### Control corpus (recently refactored)

The regulation control library lives in **Pinecone** (index `compliance-frameworks`, namespace `SOC2&GDPR`), seeded from `agent/scripts/SOC2_GDPR_Controls_v3.csv` by `agent/scripts/data_ingestion.py`. The CSV uses v3 field names — `criterion_text`, `testing_approach`, plus `points_of_focus`, `source_code_relevance`, `source_code_signal`. Rather than embedding `criterion_text` alone, ingestion composes a natural-language **`embedding_text`** per control (`build_embedding_text`: category, title/id/framework, requirement, points of focus, keywords, implementation signals) and embeds *that* (dense + sparse); the composite is also stored as metadata so reranking ranks on the same surface. `format_regulation_results` maps the v3 fields back to stable internal keys (`requirement`, `testing_criteria`, `evidence_indicator`) so downstream code is unaffected.

`REGULATION_NAMESPACE = "SOC2&GDPR"` in `utils/regulation_rag_service.py` is the single source of truth, imported by both ingestion and retrieval and decoupled from the free-text `framework` label. The pipeline's primary retrieval path is `RegulationRAGService.get_controls_for_categories`, which **exhaustively** returns every control in the requested categories via `PineconeClient.fetch_by_filter` (a metadata-scoped `{"category": {"$eq": …}}` search, sized so no control is truncated); `query_regulations` remains for free-text semantic search. Either way the filter is exact-match, so **frontend scope strings must exactly match the CSV `category` values** (the 12 categories: Logical and Physical Access Controls, System Operations, Change Management, Risk Mitigation, Availability, Processing Integrity, Data Processing Principles, Privacy by Design and Default, Security of Processing, Data Subject Rights, Breach Notification, PII Handling and Logging).

### Backend Agent Pipeline (`backend/agent/`)

The core is a **LangGraph graph** in `agent.py`; nodes live in `nodes.py`. The active path is `START → artifact_extraction → … → END` (the `extraction`/`policy_validation` nodes exist but their edges are commented out). Flow:

1. **`artifact_extraction`** (`artifact_extractor_node`) — concurrently (a) fetches all controls for the requested `source_code_categories` via `get_controls_for_categories` and (b) lists the target repo's files via GitHub MCP (`utils/github_mcp.py`). Retrieved controls are grouped into **clusters keyed by `category`** (`clusters.group_controls_into_clusters`).
2. **`evidence_subagent_dispatch` → `evidence_subagent`** — a conditional edge fans out one `Send` **per cluster**; each runs the evidence sub-agent (`subagents.py`, a small `StateGraph` of gather → conclude using tools in `tools.py`) to search code/policies. Results accumulate into `evidence_items` (an `operator.add` reducer — never re-return the full list, or items double).
3. **`prepare_validation_subagents`** merges evidence back into clusters (`update_clusters_with_evidence`), then **`validation_subagent_dispatch` → `validation_subagent`** fans out per cluster again, scoping evidence by `regulation_id` and producing a `ValidationBatch` of `ControlValidation`s (structured output from Sonnet).
4. **`combine_validation_results`** — flattens all batches into the final `validation_results`.

State flows through `ComplianceAgentState` (`state.py`). Key fields: `framework`, `category`, `source_code_categories`, `regulations`, `clusters`, `artifact_paths`, `evidence_items`, `validation_results`. Models are tiered in `nodes.py`: GPT for policy steps, Haiku for cheap extraction, Sonnet for final validation. Nodes emit live progress via `get_stream_writer()` (`status`/`updates` events).

### API Layer (`backend/app/`)

- `main.py` — FastAPI app + CORS (allows `localhost:3000`).
- `api.py` — routes: `POST /api/upload-policy` (ingest PDF into Chroma), `POST /api/stream` (run workflow, **SSE** with `status`/`token`/`update`/`error`/`done` events), `GET /api/health`. Note: the singular `category` in the request is overridden with `source_code_categories[0]`, so the pipeline is driven by the scope list, not the single dropdown.

### Frontend (`frontend/src/`)

`app/page.tsx` orchestrates the run; UI is split into `components/compliance/` (`screens.tsx` = intake form with `FRAMEWORKS`/`SCOPE_OPTIONS`, `results.tsx`, `charts.tsx`, `primitives.tsx`, `Icon.tsx`). It connects to the SSE `/api/stream` endpoint, updates incrementally, and renders donut charts, severity mix, confidence rings, a filterable control explorer, and a reasoning/evidence detail panel. `SCOPE_OPTIONS` must stay in sync with the CSV categories above. See `frontend/AGENTS.md` — this is a non-standard Next.js; read `node_modules/next/dist/docs/` before using Next.js APIs.

### Key Types & Tools

- `state.py` — `ComplianceAgentState`; `ControlValidation` (`status` pass/fail/partial/error, `severity`, `confidence`, `findings`, `evidence_snippets`); `EvidenceResult`.
- `prompts.py` — sub-agent system prompts. `tools.py` — `think`, `conclude_evidence`, `finished_gathering_evidence` plus GitHub/RAG search. `clusters.py` — grouping + evidence merge logic.
