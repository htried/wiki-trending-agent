# Geo Signals Design

**Date:** 2026-03-31  
**Status:** Approved

## Goal

Add a page-level geo visualization feature that surfaces country-level pageview distribution and flags notable country signals based on historical baselines, while keeping the current LLM agent workflow unchanged.

## Decisions

- **Primary UX:** Approach A (recommended) - add a nested `Geo signals` panel inside each page result card.
- **Flag logic:** baseline-aware anomaly detection (not static threshold-only).
- **LLM integration:** display-only for v1; no prompt/tool/event changes to agent reasoning.
- **Granularity:** countries only in v1 (no derived region grouping yet).

## Architecture

### Data ingestion and storage

- Extend CSV ingestion to parse the new `geo_distribution` column.
- Store parsed country shares as structured JSON on each `raw_hourly_trends` record.
- Keep raw country-share pairs as canonical source data.

### Baseline computation

- For each `(title, country_code)`, compute historical baseline from prior rows in local DB (excluding current hour).
- Use configurable lookback (for example, prior 14 days or prior N samples).
- Compute baseline `mean`, `stddev`, and `sample_count`.

### Notable signal rule

Flag a country for a page only when all conditions hold:

1. Baseline sample count meets minimum threshold (for example `n >= 5`).
2. Current share meets a minimum share floor (to avoid tiny-noise alerts).
3. Current share z-score vs baseline meets anomaly threshold (for example `z >= 2.0`).

## Frontend UX

Within each page result card:

- Add nested collapsible section: `Geo signals`.
- Show top countries sorted by share descending (for example top 8 with optional "show all").
- Render horizontal country bars with percentage labels.
- Render per-country `Notable` badges when flagged by backend.
- Add compact page summary chip in header, e.g. `Geo: 2 notable countries`.

User-facing copy must clarify that:

- Geo distribution reflects yesterday's distribution and may lag current-hour dynamics.
- Flags are relative to historical baseline in the local dataset.

## Run payload additions

Extend final per-page payload with:

- `geo_distribution`: list of country/share pairs for the current page-hour.
- `geo_notable_countries`: country anomaly rows including current share, baseline mean, z-score, and sample count.
- `geo_signal_summary`: aggregate summary for quick scan (notable count, strongest anomaly).

## Error handling and resiliency

- If historical baseline is insufficient: show `Insufficient historical baseline` and do not emit notable flags.
- If `geo_distribution` parsing fails for a row: skip geo rendering for that page and show a soft UI warning.
- If baseline computation fails unexpectedly for a page: return geo payload with safe defaults and no notable flags.

## Testing strategy

### Backend

- Unit tests for ingestion parsing of `geo_distribution` (valid/malformed/empty).
- Unit tests for baseline stats and anomaly flag thresholds.
- Integration test ensuring run payload includes geo fields for analyzed pages.

### Frontend

- Unit tests for `Geo signals` rendering, notable badge display, and sorting.
- UI tests for empty/malformed/insufficient-baseline states.
- Regression test confirming existing timeline/page result flow still works unchanged.

## Non-goals (v1)

- Region-level grouping and choropleth map rendering.
- Modifying LLM prompts, tools, or reasoning event model with geo signals.
- Real-time country trend attribution beyond available historical local dataset.
