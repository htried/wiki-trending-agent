# Geo Signals Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add page-level geo signal visualization and baseline-aware country anomaly flags to run outputs without changing the existing LLM agent workflow.

**Architecture:** Persist parsed `geo_distribution` values during ingestion, compute per-page country anomalies from historical baselines during orchestration, and extend per-page result payloads with geo fields. Render the new data in a nested `Geo signals` section in each page card, including notable-country badges and safe fallback states.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pytest, Vue 3 + TypeScript, Wikimedia Codex, Vitest.

---

### Task 1: Extend data model and ingestion for geo distributions

**Files:**
- Modify: `backend/src/wiki_trending_agent/models.py`
- Modify: `backend/src/wiki_trending_agent/services/ingest.py`
- Test: `backend/tests/test_ingest_csv.py`

**Step 1: Write the failing test**

```python
def test_ingests_geo_distribution_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "geo.csv"
    csv_path.write_text(
        "dt,project,identifier,title,absolute_views_current,absolute_views_zscore,views_proportion_current,views_proportion_zscore,geo_distribution\n"
        "2026-03-31 14:00:00.000,en.wikipedia,1,Example,100,1.2,0.1,0.8,\"[[\\\"US\\\",0.7],[\\\"GB\\\",0.3]]\"\n",
        encoding="utf-8",
    )
    # ingest + assert model row stores parsed geo data
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_ingest_csv.py::test_ingests_geo_distribution_column -v`  
Expected: FAIL because geo column is not parsed/persisted.

**Step 3: Write minimal implementation**

```python
# models.py
geo_distribution: Mapped[list[dict[str, float]] | None] = mapped_column(JSON, nullable=True)
```

```python
# ingest.py
def _parse_geo_distribution(raw: str) -> list[dict[str, float]]:
    ...
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_ingest_csv.py::test_ingests_geo_distribution_column -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/wiki_trending_agent/models.py backend/src/wiki_trending_agent/services/ingest.py backend/tests/test_ingest_csv.py
git commit -m "feat: ingest and persist geo distribution data"
```

### Task 2: Implement baseline/anomaly computation service

**Files:**
- Create: `backend/src/wiki_trending_agent/services/geo_signals.py`
- Test: `backend/tests/test_geo_signals.py`

**Step 1: Write the failing test**

```python
def test_detects_notable_country_from_historical_baseline(db_session):
    # seed historical title-country shares
    # current share should exceed z-score threshold
    result = compute_geo_signals_for_page(...)
    assert result["geo_notable_countries"]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_geo_signals.py::test_detects_notable_country_from_historical_baseline -v`  
Expected: FAIL because geo signal service does not exist.

**Step 3: Write minimal implementation**

```python
def compute_geo_signals_for_page(...):
    # compute mean/std/sample_count per country for prior rows
    # apply sample floor + share floor + zscore threshold
    return {"geo_distribution": ..., "geo_notable_countries": ..., "geo_signal_summary": ...}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_geo_signals.py::test_detects_notable_country_from_historical_baseline -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/wiki_trending_agent/services/geo_signals.py backend/tests/test_geo_signals.py
git commit -m "feat: add baseline-aware geo signal detection"
```

### Task 3: Wire geo signals into run outputs

**Files:**
- Modify: `backend/src/wiki_trending_agent/services/orchestrator.py`
- Modify: `backend/src/wiki_trending_agent/main.py` (if response models need updates)
- Test: `backend/tests/test_run_lifecycle.py`

**Step 1: Write the failing test**

```python
def test_run_detail_includes_geo_signal_fields(client, seeded_geo_data):
    run = client.post("/runs", json={"hour": "2026-03-31T14:00:00"}).json()
    detail = client.get(f"/runs/{run['run_id']}").json()
    page = detail["pages"][0]
    assert "geo_distribution" in page
    assert "geo_notable_countries" in page
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_run_lifecycle.py::test_run_detail_includes_geo_signal_fields -v`  
Expected: FAIL because run payload does not include geo fields.

**Step 3: Write minimal implementation**

```python
# orchestrator.py
geo = compute_geo_signals_for_page(...)
result_payload.update(geo)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_run_lifecycle.py::test_run_detail_includes_geo_signal_fields -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/wiki_trending_agent/services/orchestrator.py backend/src/wiki_trending_agent/main.py backend/tests/test_run_lifecycle.py
git commit -m "feat: include geo signals in page run outputs"
```

### Task 4: Render Geo signals section in frontend page cards

**Files:**
- Modify: `frontend/src/App.vue`
- Test: `frontend/src/test/streaming-ui.test.ts` (or existing equivalent test file)

**Step 1: Write the failing test**

```ts
it("renders geo signals panel with notable badges", async () => {
  // seed REASONING_DONE payload with geo fields
  // assert "Geo signals" and "Notable" appear
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run`  
Expected: FAIL because geo panel is not rendered.

**Step 3: Write minimal implementation**

```vue
<details v-if="item.geo_distribution?.length" class="page-result__nest">
  <summary>Geo signals</summary>
  <!-- country bars + notable badges -->
</details>
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run`  
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/App.vue frontend/src/test/streaming-ui.test.ts
git commit -m "feat: render page-level geo signals panel"
```

### Task 5: Add empty/malformed/insufficient-baseline UX coverage

**Files:**
- Modify: `frontend/src/App.vue`
- Test: `frontend/src/test/streaming-ui.test.ts`
- Test: `backend/tests/test_geo_signals.py`

**Step 1: Write the failing tests**

```python
def test_returns_insufficient_baseline_when_samples_too_low():
    result = compute_geo_signals_for_page(...)
    assert result["geo_signal_summary"]["status"] == "insufficient_baseline"
```

```ts
it("shows insufficient baseline message when no reliable anomaly can be computed", async () => {
  // assert fallback copy renders
});
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_geo_signals.py::test_returns_insufficient_baseline_when_samples_too_low -v`  
Run: `cd frontend && npm test -- --run`  
Expected: FAIL until fallback behavior is implemented.

**Step 3: Write minimal implementation**

```python
if sample_count < min_samples:
    return {"geo_notable_countries": [], "geo_signal_summary": {"status": "insufficient_baseline"}}
```

```vue
<p v-if="item.geo_signal_summary?.status === 'insufficient_baseline'">Insufficient historical baseline</p>
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_geo_signals.py -v`  
Run: `cd frontend && npm test -- --run`  
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_geo_signals.py frontend/src/App.vue frontend/src/test/streaming-ui.test.ts
git commit -m "fix: handle geo signal fallback and insufficient baseline states"
```

### Task 6: Final verification and docs update

**Files:**
- Modify: `README.md`

**Step 1: Write the failing doc/test expectation**

```markdown
Add a section describing geo signal interpretation and lag caveat.
```

**Step 2: Run verification commands**

Run: `cd backend && pytest -v`  
Run: `cd frontend && npm test -- --run`  
Run: `cd frontend && npm run build`  
Expected: all pass.

**Step 3: Write minimal documentation update**

```markdown
## Geo signals
- Country distribution uses yesterday's traffic distribution and can lag current-hour dynamics.
- Notable flags are baseline-relative and require minimum historical samples.
```

**Step 4: Re-run targeted checks**

Run: `cd frontend && npm run build`  
Expected: PASS.

**Step 5: Commit**

```bash
git add README.md
git commit -m "docs: describe geo signals behavior and limitations"
```

## Notes for implementation session

- Follow `@test-driven-development` for each task.
- Use `@systematic-debugging` for any failing tests or unexpected runtime behavior.
- Keep v1 scope focused: countries only, display-only integration, no LLM prompt/tool changes.
