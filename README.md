# Wiki Trending Agent

Local LLM agent system for identifying why Wikipedia pages are trending in a selected hour.

## What this repo includes

- `backend`: FastAPI service for ingestion, LLM tool-calling run orchestration, and SSE step updates
- `frontend`: React app (with Wikimedia Codex) for selecting an hour and viewing live run progress
- `data`: hourly CSV files (in main workspace) used for ingestion

## Quick start (local)

### Backend

1. Create and activate a Python environment.
2. Install backend deps:

```bash
pip install -e backend
```

3. Run backend:

```bash
uvicorn wiki_trending_agent.main:app --reload
```

### Frontend

1. Install frontend deps:

```bash
cd frontend && npm install
```

2. Start frontend:

```bash
npm run dev
```

## Environment variables

Copy `.env.example` and populate values:

- `DATABASE_URL`
- `SERPER_API_KEY`
- `WIKIMEDIA_ENTERPRISE_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (optional, defaults to `gpt-4.1-mini`)

Without `OPENAI_API_KEY`, the backend runs a fallback non-LLM analysis path and emits low-confidence outputs.

## Tests

Backend:

```bash
python3 -m pytest backend/tests -v
```

Frontend:

```bash
cd frontend && npm test -- --run
```

## Docker compose (optional)

```bash
docker compose up --build
```
