# Wiki Trending Agent

Local LLM agent system for identifying why Wikipedia pages are trending in a selected hour.

## What this repo includes

- `backend`: FastAPI service for ingestion, LLM tool-calling run orchestration, and SSE step updates
- `frontend`: Vue 3 app using Wikimedia Codex Vue components for selecting an hour and viewing live run progress
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

Requires **Node.js 20+** (matches Codex engine requirements).

1. Install frontend deps:

```bash
cd frontend && npm install
```

2. Start frontend:

```bash
npm run dev
```

### Ingest CSV data (hours dropdown)

The hour list comes from the database. After starting the backend, ingest the bundled `data/` directory (use an absolute path):

```bash
curl -X POST "http://localhost:8000/ingest/csv?path=/absolute/path/to/wiki-trending-agent/data"
```

## Environment variables

Copy `.env.example` and populate values:

- `DATABASE_URL` — `.env.example` uses **SQLite** so you can run the API without Postgres. Use the commented `postgresql+psycopg://…` URL only when a Postgres server is running (for example `docker compose up postgres`, or full `docker compose up`).
- `SERPER_API_KEY`
- `WIKIMEDIA_ENTERPRISE_USERNAME` (lowercase per [Enterprise login](https://enterprise.wikimedia.com/docs/authentication/#login))
- `WIKIMEDIA_ENTERPRISE_PASSWORD` — used with the [On-demand Structured Contents (beta)](https://enterprise.wikimedia.com/docs/on-demand/#article-structured-contents-beta) API (`POST /v2/structured-contents/{title}` with language filters). If you still see **403 Forbidden** after a successful login, your Enterprise account may not include beta access to Structured Contents; check your plan and the API dashboard.
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

Copy `.env.example` to `.env` and fill API keys; Compose loads `.env` for the backend service (Postgres URL is overridden for the `postgres` hostname).

```bash
docker compose up --build
```
