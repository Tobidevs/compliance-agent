# Repository Guidelines

## Project Structure & Module Organization

This repository is a full-stack compliance validation app. `backend/app/` contains the FastAPI API layer, including `/api/health`, `/api/upload-policy`, and `/api/stream`. `backend/agent/` contains the LangGraph workflow, prompts, subagents, tools, state types, RAG utilities, and evaluation scripts. Local vector data in `backend/chroma_db/` is not source. `frontend/src/app/` contains Next.js routes and global styles, `frontend/src/components/` contains compliance and UI components, and `frontend/src/lib/` contains shared utilities.

## Build, Test, and Development Commands

- `cd backend && source .venv/bin/activate`: activate the local Python environment.
- `cd backend && pip install -r requirements.txt`: install backend dependencies.
- `cd backend && uvicorn app.main:app --reload --port 8000`: run the API locally.
- `curl http://localhost:8000/api/health`: verify the backend is reachable.
- `cd frontend && npm install`: install frontend dependencies.
- `cd frontend && npm run dev`: run the Next.js dev server on port 3000.
- `cd frontend && npm run build`: create a production frontend build.
- `cd frontend && npm run lint`: run ESLint.

## Coding Style & Naming Conventions

Python code uses 4-space indentation, type hints where useful, snake_case functions and modules, and PascalCase Pydantic/state models. Keep agent node logic small and place reusable integrations in `backend/agent/utils/`. Frontend code uses TypeScript, React components in PascalCase, utility functions in camelCase, and path alias imports through `@/*`. Prefer existing Radix UI wrappers in `frontend/src/components/ui/` before adding new primitives. When editing frontend code, also follow `frontend/AGENTS.md`.

## Testing Guidelines

There is no centralized test runner configured. For backend changes, add focused tests or scripts near the affected agent or API code and document how to run them; existing ad hoc coverage includes `backend/agent/tool_test.py` and evaluation scripts under `backend/agent/evaluation/`. For frontend changes, run `npm run lint` and `npm run build` from `frontend/` before handoff. Name new tests with clear behavior-oriented names, such as `test_stream_error_formats_rate_limits`.

## Commit & Pull Request Guidelines

Git history uses concise, imperative commit subjects, for example `Fix BrainTrust tracing: init order and missing root span`. Keep commits scoped to one logical change. Pull requests should include a short summary, validation steps run, linked issues when available, screenshots for UI changes, and notes for required environment variables or data migrations.

## Security & Configuration Tips

Store secrets in `backend/.env`, never in source. Required backend keys include `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `PINECONE_API_KEY`, `GITHUB_PERSONAL_ACCESS_TOKEN`, and `BRAINTRUST_API_KEY`. Use `NEXT_PUBLIC_API_BASE_URL` for frontend API targeting.
