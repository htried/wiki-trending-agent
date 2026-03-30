# Wiki Trending Agent Design

**Date:** 2026-03-29  
**Status:** Approved

## Goal

Build an agent system that ingests hourly Wikipedia trend data, analyzes why pages are trending using time-bounded web/news evidence and Wikimedia structured content, and presents live progress plus results in a local Codex-based frontend.

## Scope

### Backend

1. Load `data/*.csv` into a relational database.
2. Given a selected hour, query top trending pages.
3. Generate a bounded set of Google-style queries per page.
4. Use Serper API to fetch recent, time-limited news evidence.
5. Use Wikimedia Enterprise Structured Contents API to fetch page content.
6. Optionally run a second-pass search for unresolved pages.
7. Produce concise likely trend reasons and event candidates when evidence is limited.

### Frontend

1. Build a local website using Wikimedia Codex design system.
2. Let users select an hour.
3. Show dynamic run progress as the backend agent executes.
4. Display page-level outputs and synthesized event hypotheses.

## Chosen Architecture (Approach A)

Use a **job-based pipeline** with **live status streaming**:

- FastAPI backend coordinates staged run processing.
- Postgres stores raw trends, run state, and enriched outputs.
- Frontend starts a run and subscribes to server-sent events (SSE) for incremental updates.
- Pipeline is designed for idempotency and partial success.

This approach is preferred because it provides a responsive UX for long-running enrichment while keeping reliability and retries manageable.

## High-Level Components

### Backend service (FastAPI)

- Ingestion command/API for CSV loading.
- Run orchestration service for hour-based analysis jobs.
- Integrations:
  - Serper API client
  - Wikimedia Enterprise Structured Contents client
- SSE event publisher per run.

### Storage (Postgres)

- Source trend rows
- Run lifecycle and stage state
- Page-level enrichment artifacts
- Synthesized explanations and event candidates

### Frontend (React + Codex)

- Hour selector and run controls
- Live timeline/status feed
- Progressive page result cards
- Final run summary and unresolved/low-confidence indicators

## Data Model

- `raw_hourly_trends`
  - Raw CSV fields: `dt`, `project`, `identifier`, `title`, `absolute_views_current`, `absolute_views_zscore`, `views_proportion_current`, `views_proportion_zscore`
  - Indexes on `dt`, `project`, `title`
- `analysis_runs`
  - Run metadata: `id`, `hour`, `status`, `started_at`, `finished_at`, `error_summary`
- `run_pages`
  - Per-run selected pages and ranking metrics
- `page_news_hits`
  - Serper news/search hits with publication time metadata and snippet/source fields
- `page_wiki_content`
  - Structured content payload metadata, retrieval timestamps, version/hash
- `page_reasoning`
  - Trend explanation, confidence, supporting evidence references
- `run_events`
  - Synthesized event hypotheses for unresolved pages

## Run Pipeline Stages

1. **Select pages** for target hour based on configurable ranking logic.
2. **Formulate bounded queries** per page.
3. **Fetch time-limited news/search evidence** from Serper.
4. **Fetch structured wiki content** for each page.
5. **Optional second-pass search** for pages with weak confidence.
6. **Synthesize outputs**:
   - page-level likely reason
   - event candidates for pages lacking enough evidence

Each stage emits run events and can fail independently without aborting all run output.

## API Design

- `POST /ingest/csv`
  - Load CSV data into `raw_hourly_trends`.
- `GET /hours`
  - Return available hours from ingested data.
- `POST /runs`
  - Create run for selected hour with optional limits (`max_pages`, `max_queries_per_page`).
- `GET /runs/{run_id}`
  - Return run status and accumulated outputs.
- `GET /runs/{run_id}/stream`
  - SSE stream of stage updates and page-level progress events.

## Frontend Behavior

- User selects hour and starts a run.
- UI immediately opens a run panel and subscribes to SSE.
- Page rows update progressively as evidence arrives.
- Errors are shown inline at page/stage level with retry options.
- Final state includes concise explanations, confidence markers, and event hypotheses.

## Reliability and Safety

- Per-stage timeout and retry limits.
- Idempotent writes by `(run_id, page, source/stage)`.
- Structured logging keyed by `run_id`.
- Partial results preserved on failure.
- Explicit "insufficient evidence" outcomes to avoid hallucinated certainty.

## Configuration

- `DATABASE_URL`
- `SERPER_API_KEY`
- `WIKIMEDIA_ENTERPRISE_API_KEY`
- Optional knobs:
  - max pages per run
  - max queries per page
  - lookback/recency window
  - timeout/retry settings

## Testing Strategy

- Unit tests:
  - top-page selection queries
  - query generation limits
  - synthesis fallback behavior
- Integration tests:
  - mocked Serper and Wikimedia clients
  - run lifecycle and stage transitions
  - SSE event ordering and payload shape
- Frontend tests:
  - hour selection and run creation
  - incremental status rendering
  - partial failure and recovery UX

## Non-Goals (v1)

- Perfect causal attribution for every page.
- Distributed queue infra from day one.
- Multi-project Wikipedia support beyond current ingested scope.
- Authentication/authorization for local-first UI.
