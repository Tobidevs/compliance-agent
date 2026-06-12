# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A full-stack compliance validation application that uses a LangGraph multi-agent workflow to assess whether a GitHub repository meets regulatory/compliance controls (e.g., SOC 2, ISO 27001). The backend drives an LLM agent pipeline; the frontend streams real-time results.

## Development Commands

### Backend (FastAPI + LangGraph)

```bash
cd backend

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server (port 8000)
uvicorn app.main:app --reload --port 8000

# Health check
curl http://localhost:8000/api/health
```

### Frontend (Next.js)

```bash
cd frontend

# Install dependencies
npm install

# Run development server (port 3000)
npm run dev

# Build for production
npm run build

# Lint
npm run lint
```

### Environment

Backend requires `backend/.env` with:
- `OPENAI_API_KEY` — GPT-4o mini for extraction/validation
- `ANTHROPIC_API_KEY` — Claude for subagents
- `PINECONE_API_KEY` — vector reranking
- `GITHUB_PERSONAL_ACCESS_TOKEN` — code retrieval via MCP
- `LANGSMITH_API_KEY` / `LANGSMITH_ENDPOINT` — LangGraph tracing
- `CHROMA_PERSIST_DIR` — vector DB path (default: `./chroma_db`)

Frontend reads `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://127.0.0.1:8000`).

## Architecture

### Backend Agent Pipeline (`backend/agent/`)

The core is a **LangGraph graph** defined in `agent.py`. Execution flows through these nodes (defined in `nodes.py`):

1. **`artifact_extraction`** — fetches source code files from the target GitHub repo using the GitHub MCP tool (`utils/github_mcp.py`)
2. **`evidence_subagent_dispatch`** → **`evidence_subagent`** — fans out subagents per control cluster to search code/policies for evidence; results accumulated into `ComplianceAgentState.evidence`
3. **`prepare_validation_subagents`** → **`validation_subagent_dispatch`** → **`validation_subagent`** — validates each control against gathered evidence, producing a `ControlValidation` per control
4. **`combine_validation_results`** — aggregates all `ControlValidation` objects into the final output

State between nodes flows through `ComplianceAgentState` (a `TypedDict` in `state.py`). Key fields: `framework`, `regulations`, `policies`, `source_code`, `evidence`, `validation_results`, `clusters`.

Policy documents (PDFs) are chunked and stored in **Chroma** (local) and retrieved via `utils/policy_rag_service.py`. Pinecone is used for reranking retrieved chunks.

### API Layer (`backend/app/`)

- `main.py` — FastAPI app setup, CORS (allows `localhost:3000`)
- `api.py` — three routes:
  - `POST /api/upload-policy` — ingest PDF into Chroma
  - `POST /api/stream` — run compliance workflow, returns **SSE stream** with event types: `status`, `token`, `update`, `error`, `done`
  - `GET /api/health`

### Frontend (`frontend/src/app/page.tsx`)

Single large component (~1400 lines) that:
- Renders the compliance run form (framework, category, repo details, source code scope)
- Connects to the SSE `/api/stream` endpoint and updates state incrementally
- Displays results as donut charts, severity mix, confidence rings, a filterable control explorer, and a detail panel with reasoning/evidence
- Uses Radix UI headless components from `src/components/ui/`

### Key Type Definitions (`backend/agent/state.py`)

- `ComplianceAgentState` — full graph state
- `ControlValidation` — per-control result: `status` (pass/fail/partial/error), `severity`, `confidence`, `findings`, `evidence_snippets`
- `EvidenceResult` — evidence gathered per control cluster

### Subagent / Tool Design (`backend/agent/subagents.py`, `tools.py`, `prompts.py`)

Subagents are spawned with dedicated system prompts from `prompts.py`. Tools available to subagents are defined in `tools.py` and include GitHub search, Chroma RAG search, and policy lookup. Clustering logic for grouping related controls lives in `clusters.py`.
