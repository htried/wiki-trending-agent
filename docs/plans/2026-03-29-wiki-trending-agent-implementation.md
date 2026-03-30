# Wiki Trending Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local FastAPI + React (Codex) system that ingests hourly trend CSVs, runs staged trend-reason analysis jobs, streams progress live, and renders page/event results.

**Architecture:** Use a job-based backend pipeline with persisted run state and SSE progress events. Keep the first version queue-ready but in-process for simplicity; isolate external integrations behind clients so they are easy to mock in tests.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL, pytest, httpx, React + TypeScript + Vite, Wikimedia Codex, EventSource (SSE), Vitest + Testing Library.

---

### Task 1: Scaffold Backend Service

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/wiki_trending_agent/__init__.py`
- Create: `backend/src/wiki_trending_agent/main.py`
- Create: `backend/src/wiki_trending_agent/config.py`
- Create: `backend/src/wiki_trending_agent/db.py`
- Create: `backend/tests/test_health.py`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from wiki_trending_agent.main import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_health.py::test_health_endpoint -v`  
Expected: FAIL because app/routes are not implemented.

**Step 3: Write minimal implementation**

Add FastAPI app with `/health` route in `main.py`, plus configuration + DB session boilerplate.

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_health.py::test_health_endpoint -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/pyproject.toml backend/src/wiki_trending_agent backend/tests/test_health.py
git commit -m "feat: scaffold FastAPI backend with health endpoint"
```

### Task 2: Create DB Schema + Migration Baseline

**Files:**
- Create: `backend/src/wiki_trending_agent/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_schema.py`
- Create: `backend/tests/test_models_schema.py`

**Step 1: Write the failing test**

```python
from wiki_trending_agent.models import AnalysisRun, RawHourlyTrend


def test_model_tables_exist():
    assert RawHourlyTrend.__tablename__ == "raw_hourly_trends"
    assert AnalysisRun.__tablename__ == "analysis_runs"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_models_schema.py::test_model_tables_exist -v`  
Expected: FAIL because models do not exist.

**Step 3: Write minimal implementation**

Define SQLAlchemy models and an initial migration for:
- `raw_hourly_trends`
- `analysis_runs`
- `run_pages`
- `page_news_hits`
- `page_wiki_content`
- `page_reasoning`
- `run_events`

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_models_schema.py::test_model_tables_exist -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/wiki_trending_agent/models.py backend/alembic* backend/tests/test_models_schema.py
git commit -m "feat: add initial database schema for trend analysis pipeline"
```

### Task 3: Implement CSV Ingestion

**Files:**
- Create: `backend/src/wiki_trending_agent/services/ingest.py`
- Modify: `backend/src/wiki_trending_agent/main.py`
- Create: `backend/tests/test_ingest_csv.py`

**Step 1: Write the failing test**

```python
from pathlib import Path
from wiki_trending_agent.services.ingest import ingest_csv_directory


def test_ingests_csv_directory(db_session):
    data_dir = Path("../data")
    count = ingest_csv_directory(db_session, data_dir)
    assert count > 0
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_ingest_csv.py::test_ingests_csv_directory -v`  
Expected: FAIL because ingestion service is missing.

**Step 3: Write minimal implementation**

Implement CSV parser and bulk insert with idempotency guard (unique key on hour/project/identifier/title).

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_ingest_csv.py::test_ingests_csv_directory -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/wiki_trending_agent/services/ingest.py backend/src/wiki_trending_agent/main.py backend/tests/test_ingest_csv.py
git commit -m "feat: add CSV ingestion service and endpoint"
```

### Task 4: Expose Hour Discovery + Trending Selection

**Files:**
- Create: `backend/src/wiki_trending_agent/services/trends.py`
- Modify: `backend/src/wiki_trending_agent/main.py`
- Create: `backend/tests/test_trends_query.py`

**Step 1: Write the failing test**

```python
from wiki_trending_agent.services.trends import get_top_pages_for_hour


def test_select_top_pages_for_hour(db_session, seeded_trend_rows):
    pages = get_top_pages_for_hour(db_session, "2026-03-29 12:00:00", limit=10)
    assert len(pages) == 10
    assert pages[0].title
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_trends_query.py::test_select_top_pages_for_hour -v`  
Expected: FAIL because selection service is missing.

**Step 3: Write minimal implementation**

Add SQL query for top pages per hour (start with descending `absolute_views_zscore` and fallback to `absolute_views_current` when z-score null). Add `GET /hours`.

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_trends_query.py::test_select_top_pages_for_hour -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/wiki_trending_agent/services/trends.py backend/src/wiki_trending_agent/main.py backend/tests/test_trends_query.py
git commit -m "feat: add hour listing and top-page selection logic"
```

### Task 5: Build Integration Clients (Serper + Wikimedia)

**Files:**
- Create: `backend/src/wiki_trending_agent/integrations/serper_client.py`
- Create: `backend/src/wiki_trending_agent/integrations/wikimedia_client.py`
- Create: `backend/tests/test_integrations_clients.py`

**Step 1: Write the failing test**

```python
from wiki_trending_agent.integrations.serper_client import SerperClient


def test_serper_client_builds_time_limited_request():
    client = SerperClient(api_key="test")
    payload = client.build_query_payload("Palm Sunday", "24h")
    assert payload["q"] == "Palm Sunday"
    assert "time" in payload
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_integrations_clients.py::test_serper_client_builds_time_limited_request -v`  
Expected: FAIL because client is missing.

**Step 3: Write minimal implementation**

Create HTTP clients with dependency-injected transport for mocking, bounded timeout, and typed response mapping.

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_integrations_clients.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/wiki_trending_agent/integrations backend/tests/test_integrations_clients.py
git commit -m "feat: add Serper and Wikimedia API client wrappers"
```

### Task 6: Implement Run Orchestrator + Persistence

**Files:**
- Create: `backend/src/wiki_trending_agent/services/orchestrator.py`
- Create: `backend/src/wiki_trending_agent/services/reasoning.py`
- Modify: `backend/src/wiki_trending_agent/main.py`
- Create: `backend/tests/test_run_lifecycle.py`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from wiki_trending_agent.main import app


def test_create_run_returns_run_id():
    client = TestClient(app)
    response = client.post("/runs", json={"hour": "2026-03-29T12:00:00Z"})
    assert response.status_code == 201
    assert "run_id" in response.json()
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_run_lifecycle.py::test_create_run_returns_run_id -v`  
Expected: FAIL because runs endpoint and service are missing.

**Step 3: Write minimal implementation**

Add:
- `POST /runs` and `GET /runs/{run_id}`
- staged orchestrator with statuses: `queued`, `running`, `completed`, `failed`, `partial`
- per-page reasoning synthesis using fetched evidence

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_run_lifecycle.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/wiki_trending_agent/services backend/src/wiki_trending_agent/main.py backend/tests/test_run_lifecycle.py
git commit -m "feat: add run orchestration and persisted run lifecycle"
```

### Task 7: Add SSE Streaming for Live Progress

**Files:**
- Create: `backend/src/wiki_trending_agent/services/events.py`
- Modify: `backend/src/wiki_trending_agent/main.py`
- Create: `backend/tests/test_run_stream.py`

**Step 1: Write the failing test**

```python
def test_run_stream_emits_started_event(test_client, seeded_run):
    response = test_client.get(f"/runs/{seeded_run.id}/stream")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_run_stream.py::test_run_stream_emits_started_event -v`  
Expected: FAIL because stream endpoint is missing.

**Step 3: Write minimal implementation**

Implement SSE event generator and endpoint with event types:
- `RUN_STARTED`
- `PAGES_SELECTED`
- `NEWS_FETCHED`
- `WIKI_FETCHED`
- `REASONING_DONE`
- `EVENTS_SYNTHESIZED`
- `RUN_COMPLETED`
- `RUN_ERROR`

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_run_stream.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/wiki_trending_agent/services/events.py backend/src/wiki_trending_agent/main.py backend/tests/test_run_stream.py
git commit -m "feat: stream run progress via server-sent events"
```

### Task 8: Scaffold Frontend with Codex + Hour Picker

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/components/HourSelector.tsx`
- Create: `frontend/src/components/RunControls.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/test/App.test.tsx`

**Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import App from "../App";

test("renders hour selector", () => {
  render(<App />);
  expect(screen.getByText(/select hour/i)).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run`  
Expected: FAIL because app/components are missing.

**Step 3: Write minimal implementation**

Scaffold React app, integrate Codex styles/components, render hour selector from `GET /hours`.

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run`  
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend
git commit -m "feat: scaffold Codex-based React frontend with hour selection"
```

### Task 9: Add Live Run Timeline + Results Rendering

**Files:**
- Create: `frontend/src/components/RunTimeline.tsx`
- Create: `frontend/src/components/PageResultsList.tsx`
- Create: `frontend/src/components/EventCandidates.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api.ts`
- Create: `frontend/src/test/streaming-ui.test.tsx`

**Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import App from "../App";

test("shows run progress updates", async () => {
  render(<App />);
  expect(await screen.findByText(/run started/i)).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/test/streaming-ui.test.tsx`  
Expected: FAIL because stream wiring/UI is missing.

**Step 3: Write minimal implementation**

Wire `POST /runs` + `EventSource(/runs/{run_id}/stream)` and progressively render stage updates, page explanations, and event candidates.

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/test/streaming-ui.test.tsx`  
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat: add live run timeline and progressive result display"
```

### Task 10: Hardening, DX, and End-to-End Verification

**Files:**
- Create: `backend/tests/test_end_to_end_local.py`
- Create: `README.md`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Modify: `backend/src/wiki_trending_agent/config.py`
- Modify: `frontend/src/App.tsx`

**Step 1: Write the failing test**

```python
def test_local_run_happy_path(api_client):
    run = api_client.post("/runs", json={"hour": "2026-03-29T12:00:00Z"})
    assert run.status_code == 201
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_end_to_end_local.py::test_local_run_happy_path -v`  
Expected: FAIL until wiring and fixtures are complete.

**Step 3: Write minimal implementation**

Add robust validation, user-facing errors for missing API keys, local startup docs, and docker-compose for Postgres + services.

**Step 4: Run full verification**

Run:
- `cd backend && pytest -v`
- `cd frontend && npm test -- --run`
- `cd frontend && npm run build`

Expected: All pass.

**Step 5: Commit**

```bash
git add README.md .env.example docker-compose.yml backend frontend
git commit -m "chore: finalize local setup docs and end-to-end validation"
```

## Notes for Implementation Session

- Follow @test-driven-development skill during execution.
- Use @systematic-debugging skill for any failing tests or runtime bugs.
- Keep external API calls mockable; never depend on live Serper/Wikimedia in unit tests.
- Keep query generation bounded by config to control cost and latency.
- Prefer explicit "insufficient evidence" outputs over speculative conclusions.
