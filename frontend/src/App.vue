<template>
  <div class="app-frame">
    <header class="app-header">
      <div class="app-header__inner">
        <h1 class="app-header__title">What's Trending On Wiki?</h1>
        <p class="app-header__tagline">
          Pick an hour, run the pipeline, then open each page row below to see what's trending.
        </p>
      </div>
    </header>

    <main class="app-main">
    <div class="field-block">
      <cdx-field>
        <template #label>Select hour</template>
        <cdx-select
          v-model:selected="selectedHour"
          :menu-items="hourMenuItems"
          default-label="Choose an hour"
          aria-label="Select hour"
        />
      </cdx-field>
    </div>

    <div class="run-controls">
      <cdx-field class="topk-field">
        <template #label>Top k pages</template>
        <cdx-text-input
          v-model="topKPages"
          input-type="number"
          aria-label="Top k pages"
          placeholder="All"
        />
      </cdx-field>
      <cdx-button
        action="progressive"
        weight="primary"
        :disabled="!canRun"
        @click="handleRun"
      >
        Run analysis
      </cdx-button>
      <span v-if="isRunInProgress" class="run-status" aria-live="polite">
        <span class="run-status__spinner" aria-hidden="true" />
        Analysis in progress...
      </span>
    </div>

    <section
      v-if="timeline.length > 0"
      aria-label="Run timeline"
      class="timeline-section"
    >
      <h2 class="section-heading">Timeline</h2>
      <div
        class="timeline-scroll"
        :class="{ 'timeline-scroll--constrained': timeline.length > TIMELINE_SCROLL_AFTER }"
      >
        <ul class="timeline">
          <li v-for="entry in timeline" :key="entry.id" class="timeline__item">
            <div class="timeline__line">{{ entry.line }}</div>
            <div v-if="entry.sub" class="timeline__sub">{{ entry.sub }}</div>
          </li>
        </ul>
      </div>
    </section>

    <section
      v-if="pageResults.length > 0"
      aria-label="Page results"
      class="page-results-section"
    >
      <h2 class="section-heading">Page results</h2>
      <p class="page-results-hint">
        <strong>Dropdown menus:</strong> each analyzed page is one row — click the title bar
        to expand the summary. Inside, <strong>each subsection</strong> (What’s new, section anchors, …) is another
        collapsible menu. Factual sentences use Wikipedia-style <strong>[1]</strong> markers; full sources are listed in
        <strong>References</strong> at the bottom of each page card.
      </p>
      <ul class="page-results">
        <li v-for="item in pageResults" :key="item.title" class="page-results__item">
          <details class="page-result">
            <summary class="page-result__summary">
              <span class="page-result__summary-main">
                <span class="page-result__summary-title">{{ displayTitle(item.title) }}</span>
                <span class="page-result__summary-hint details-hint" aria-hidden="true">
                  <span class="details-hint__expand">Expand</span>
                  <span class="details-hint__collapse">Collapse</span>
                </span>
              </span>
              <a
                v-if="item.wikipedia_article_url"
                class="cdx-link page-result__summary-link"
                :href="item.wikipedia_article_url"
                target="_blank"
                rel="noopener noreferrer"
                @click.stop
              >
                Open Wikipedia article
              </a>
              <span v-if="item.confidence !== undefined" class="page-result__summary-meta">
                confidence {{ item.confidence.toFixed(2) }}
              </span>
            </summary>
            <div class="page-result__inner">
              <div
                v-if="item.summary_html"
                class="page-result__body"
                v-html="item.summary_html"
              />
              <details v-if="item.whats_new_html" class="page-result__nest">
                <summary>
                  What’s new
                  <span class="page-result__nest-hint details-hint" aria-hidden="true">
                    <span class="details-hint__expand">Expand</span>
                    <span class="details-hint__collapse">Collapse</span>
                  </span>
                </summary>
                <div class="page-result__body" v-html="item.whats_new_html" />
              </details>
              <details v-if="item.sections_to_update.length" class="page-result__nest">
                <summary>
                  Sections to update
                  <span class="page-result__nest-hint-muted">· verified anchors</span>
                  <span class="page-result__nest-hint details-hint" aria-hidden="true">
                    <span class="details-hint__expand">Expand</span>
                    <span class="details-hint__collapse">Collapse</span>
                  </span>
                </summary>
                <ul class="page-result__link-list">
                  <li v-for="(sec, i) in item.sections_to_update" :key="i">
                    <a
                      class="cdx-link"
                      :href="sec.section_url"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {{ sec.section_heading || "Section" }}
                    </a>
                  </li>
                </ul>
              </details>
              <details v-if="item.sections_skipped.length" class="page-result__nest page-result__nest--skipped">
                <summary>
                  Sections dropped (not in article section list)
                  <span class="page-result__nest-hint details-hint" aria-hidden="true">
                    <span class="details-hint__expand">Expand</span>
                    <span class="details-hint__collapse">Collapse</span>
                  </span>
                </summary>
                <ul class="page-result__link-list">
                  <li v-for="(row, i) in item.sections_skipped" :key="i">
                    <span class="page-result__skipped-line">
                      {{ row.section_heading || row.section_url || "—" }}
                      <span v-if="row.section_url" class="page-result__skipped-url">{{ row.section_url }}</span>
                    </span>
                  </li>
                </ul>
              </details>
              <details v-if="item.suggested_update_html" class="page-result__nest">
                <summary>
                  Suggested update
                  <span class="page-result__nest-hint details-hint" aria-hidden="true">
                    <span class="details-hint__expand">Expand</span>
                    <span class="details-hint__collapse">Collapse</span>
                  </span>
                </summary>
                <div class="page-result__body" v-html="item.suggested_update_html" />
              </details>
              <details v-if="item.geo_distribution.length || item.geo_signal_summary" class="page-result__nest">
                <summary>
                  Geo signals
                  <span v-if="item.geo_notable_countries.length" class="page-result__nest-hint-muted">
                    · {{ item.geo_notable_countries.length }} notable
                  </span>
                  <span class="page-result__nest-hint details-hint" aria-hidden="true">
                    <span class="details-hint__expand">Expand</span>
                    <span class="details-hint__collapse">Collapse</span>
                  </span>
                </summary>
                <p v-if="item.geo_signal_summary?.status === 'insufficient_baseline'">
                  Insufficient historical baseline for anomaly flags.
                </p>
                <ul v-if="item.geo_distribution.length" class="page-result__link-list">
                  <li v-for="country in item.geo_distribution.slice(0, 8)" :key="country.country_code">
                    <span>{{ country.country_code }} — {{ (country.proportion * 100).toFixed(1) }}%</span>
                    <strong
                      v-if="item.geo_notable_countries.some((row) => row.country_code === country.country_code)"
                    >
                      · Notable
                    </strong>
                  </li>
                </ul>
              </details>
              <section
                v-if="item.citations.length"
                class="page-result__references"
                :aria-labelledby="`${item.citePrefix}-refs-heading`"
              >
                <h3 :id="`${item.citePrefix}-refs-heading`" class="page-result__references-title">References</h3>
                <ol class="page-result__reflist">
                  <li
                    v-for="(c, i) in item.citations"
                    :id="`${item.citePrefix}-ref-${i + 1}`"
                    :key="i"
                    class="page-result__reflist-item"
                  >
                    <a class="cdx-link" :href="c.url" target="_blank" rel="noopener noreferrer">
                      {{ c.title }}
                    </a>
                    <span class="page-result__ref-url">{{ c.url }}</span>
                    <p v-if="c.reliability_note" class="page-result__cite-note">{{ c.reliability_note }}</p>
                  </li>
                </ol>
              </section>
            </div>
          </details>
        </li>
      </ul>
    </section>

    <section
      v-if="eventCandidates.length > 0"
      aria-label="Event candidates"
      class="event-candidates-section"
    >
      <details class="panel-details">
        <summary class="panel-details__summary">
          Event candidates
          <span class="panel-details__hint details-hint" aria-hidden="true">
            <span class="details-hint__expand">Expand</span>
            <span class="details-hint__collapse">Collapse</span>
          </span>
          <span v-if="eventCandidates.length" class="panel-details__count">({{ eventCandidates.length }})</span>
        </summary>
        <ul class="panel-details__list">
          <li v-for="(ev, index) in eventCandidates" :key="`${ev}-${index}`">{{ ev }}</li>
        </ul>
      </details>
    </section>

    <p v-if="error" class="app-error" role="alert">{{ error }}</p>
    </main>

    <footer class="app-footer">
      <p>
        Timeline shows live steps; page rows aggregate the final model output. Structured article data comes from
        Wikimedia Enterprise when credentials are configured.
      </p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { CdxButton, CdxField, CdxSelect, CdxTextInput } from "@wikimedia/codex";
import { computed, onMounted, onUnmounted, ref } from "vue";

import { fetchHours, startRun, subscribeToRun, type RunEvent } from "./api";
import { renderWikiCitedMarkdown } from "./renderMarkdown";

/** After this many timeline rows, the list becomes a fixed-height scroll region. */
const TIMELINE_SCROLL_AFTER = 5;

type Citation = { title: string; url: string; reliability_note?: string };
type SectionToUpdate = { section_heading: string; section_url: string };
type SectionSkipped = { section_heading: string; section_url: string; reason?: string };
type GeoDistributionRow = { country_code: string; proportion: number };
type GeoNotableCountry = {
  country_code: string;
  current_share: number;
  baseline_mean: number;
  zscore: number;
  sample_count: number;
};
type GeoSignalSummary = { status: string; notable_count: number; strongest_country_code?: string | null };

type PageResult = {
  title: string;
  citePrefix: string;
  wikipedia_article_url: string;
  summary_html: string;
  whats_new_html: string;
  suggested_update_html: string;
  sections_to_update: SectionToUpdate[];
  sections_skipped: SectionSkipped[];
  citations: Citation[];
  confidence?: number;
  geo_distribution: GeoDistributionRow[];
  geo_notable_countries: GeoNotableCountry[];
  geo_signal_summary?: GeoSignalSummary;
};

type TimelineEntry = { id: string; line: string; sub?: string };

function displayTitle(title: string): string {
  return title.replaceAll("_", " ");
}

/** Stable id prefix for citation anchors (HTML id safe). */
function citeIdPrefix(title: string, ordinal: number): string {
  const slug = title
    .replaceAll("_", "-")
    .replace(/[^a-zA-Z0-9-]+/g, "-")
    .replace(/^-+/g, "")
    .replace(/-+$/g, "")
    .toLowerCase()
    .slice(0, 40);
  return `r-${ordinal}-${slug || "page"}`;
}

function normalizeCitations(raw: unknown): Citation[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  const out: Citation[] = [];
  for (const c of raw) {
    if (typeof c === "string") {
      out.push({ title: c, url: c });
    } else if (c !== null && typeof c === "object" && "url" in c) {
      const url = String((c as { url: string }).url);
      if (url) {
        const noteRaw = (c as { reliability_note?: string }).reliability_note;
        const entry: Citation = {
          title: String((c as { title?: string }).title || url),
          url,
        };
        if (typeof noteRaw === "string" && noteRaw.trim()) {
          entry.reliability_note = noteRaw.trim();
        }
        out.push(entry);
      }
    }
  }
  return out;
}

function parseSections(raw: unknown): SectionToUpdate[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw
    .filter((s): s is Record<string, unknown> => s !== null && typeof s === "object")
    .map((s) => ({
      section_heading: String(s.section_heading ?? ""),
      section_url: String(s.section_url ?? ""),
    }))
    .filter((s) => s.section_url.length > 0);
}

function parseSectionsSkipped(raw: unknown): SectionSkipped[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw
    .filter((s): s is Record<string, unknown> => s !== null && typeof s === "object")
    .map((s) => ({
      section_heading: String(s.section_heading ?? ""),
      section_url: String(s.section_url ?? ""),
      reason: s.reason !== undefined ? String(s.reason) : undefined,
    }))
    .filter((s) => s.section_heading.length > 0 || s.section_url.length > 0);
}

function parseGeoDistribution(raw: unknown): GeoDistributionRow[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw
    .filter((row): row is Record<string, unknown> => row !== null && typeof row === "object")
    .map((row) => ({
      country_code: String(row.country_code ?? ""),
      proportion: Number(row.proportion ?? 0),
    }))
    .filter((row) => row.country_code.length > 0 && Number.isFinite(row.proportion))
    .sort((a, b) => b.proportion - a.proportion);
}

function parseGeoNotableCountries(raw: unknown): GeoNotableCountry[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw
    .filter((row): row is Record<string, unknown> => row !== null && typeof row === "object")
    .map((row) => ({
      country_code: String(row.country_code ?? ""),
      current_share: Number(row.current_share ?? 0),
      baseline_mean: Number(row.baseline_mean ?? 0),
      zscore: Number(row.zscore ?? 0),
      sample_count: Number(row.sample_count ?? 0),
    }))
    .filter((row) => row.country_code.length > 0)
    .sort((a, b) => b.zscore - a.zscore);
}

function parseGeoSignalSummary(raw: unknown): GeoSignalSummary | undefined {
  if (!raw || typeof raw !== "object") {
    return undefined;
  }
  const obj = raw as Record<string, unknown>;
  return {
    status: String(obj.status ?? "ok"),
    notable_count: Number(obj.notable_count ?? 0),
    strongest_country_code: obj.strongest_country_code ? String(obj.strongest_country_code) : null,
  };
}

const hours = ref<string[]>([]);
const selectedHour = ref<string | number | null>(null);
const topKPages = ref<string | number>("");
const error = ref("");
const timeline = ref<TimelineEntry[]>([]);
let timelineCounter = 0;
const pageResults = ref<PageResult[]>([]);
const eventCandidates = ref<string[]>([]);
const activeStream = ref<EventSource | null>(null);
const isRunInProgress = ref(false);

const hourMenuItems = computed(() => hours.value.map((h) => ({ value: h, label: h })));

const canRun = computed(() => selectedHour.value !== null && selectedHour.value !== "");

function appendTimeline(line: string, sub?: string): void {
  timelineCounter += 1;
  const entry: TimelineEntry = { id: `tl-${timelineCounter}`, line };
  const t = sub?.trim();
  if (t) {
    entry.sub = t;
  }
  timeline.value = [...timeline.value, entry];
}

const handleRunEvent = (event: RunEvent): void => {
  const { type, payload } = event;

  switch (type) {
    case "RUN_STARTED":
      isRunInProgress.value = true;
      appendTimeline("Run started");
      break;
    case "PAGES_SELECTED": {
      const pages = payload.pages;
      if (Array.isArray(pages) && pages.length > 0) {
        const lines = pages
          .map((p) => {
            if (!p || typeof p !== "object") return "";
            const o = p as Record<string, unknown>;
            const t = String(o.title ?? "");
            const views = Number(o.absolute_views_current ?? 0);
            const rank = Number(o.rank ?? 0);
            return `#${rank} ${displayTitle(t)} — ${views.toLocaleString()} views`;
          })
          .filter(Boolean);
        appendTimeline(`Selected ${pages.length} pages (ordered by absolute views)`, lines.join("\n"));
      } else {
        appendTimeline(`Selected ${Number(payload.count ?? 0)} pages (ordered by absolute views)`);
      }
      break;
    }
    case "PAGE_ANALYSIS_STARTED":
      appendTimeline(
        `Analyzing: ${displayTitle(String(payload.page_title ?? ""))}`,
        `Rank ${String(payload.rank ?? "")} in this run`,
      );
      break;
    case "AGENT_TOOL_CALL": {
      const tool = String(payload.tool ?? "");
      const page = displayTitle(String(payload.page_title ?? ""));
      const args = payload.args as Record<string, unknown> | undefined;
      let sub = "";
      if (args && tool === "search_news") {
        sub = `Query: ${String(args.query ?? "")} · ${String(args.time_window ?? "")}`;
      } else if (args && tool === "fetch_wiki_content") {
        sub = `${String(args.project ?? "")} · ${String(args.page_title ?? "")}`;
      } else if (args && tool === "fetch_wiki_section_content") {
        const h = String(args.section_heading ?? "").trim();
        const u = String(args.section_url ?? "").trim();
        sub = [h, u].filter(Boolean).join(" · ") || "section body";
      }
      appendTimeline(page ? `[${page}] ${tool}` : tool, sub);
      break;
    }
    case "AGENT_TOOL_RESULT": {
      const tool = String(payload.tool ?? "");
      const page = displayTitle(String(payload.page_title ?? ""));
      let sub = "";
      if (tool === "search_news") {
        sub = `${Number(payload.result_count ?? 0)} news results`;
      } else if (tool === "fetch_wiki_content") {
        const fetchErr = String(payload.fetch_error ?? "").trim();
        const parseErr = String(payload.parse_error ?? "").trim();
        const hint = String(payload.hint ?? "").trim();
        const n = Number(payload.section_count);
        if (fetchErr) {
          sub = `Enterprise request failed: ${fetchErr}`;
        } else if (!payload.has_content) {
          sub = parseErr
            ? `Payload not recognized as article (${parseErr})`
            : "No usable article payload";
          if (hint) {
            sub = `${sub}. ${hint}`;
          }
        } else if (Number.isFinite(n) && n > 0) {
          sub = `Enterprise payload OK · ${n} sections in index`;
        } else {
          sub = "Structured article received (no section index entries)";
        }
      } else if (tool === "fetch_wiki_section_content") {
        if (payload.ok === false) {
          const e = String(payload.error ?? "").trim();
          const h = String(payload.hint ?? "").trim();
          sub = e || "section fetch failed";
          if (h) {
            sub = `${sub} — ${h}`;
          }
        } else {
          sub = `${Number(payload.char_count ?? 0)} characters of section text`;
        }
      }
      appendTimeline(page ? `[${page}] ${tool} done` : `${tool} done`, sub);
      break;
    }
    case "AGENT_REASONING": {
      const page = displayTitle(String(payload.page_title ?? ""));
      const bits = Object.entries(payload)
        .filter(([k]) => k !== "page_title" && k !== "run_id")
        .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
        .join(" · ");
      appendTimeline(page ? `[${page}] Agent note` : "Agent note", bits || "(synthesis)");
      break;
    }
    case "REASONING_DONE": {
      const title = String(payload.page_title ?? "Unknown page");
      const conf =
        typeof payload.confidence === "number" ? `Confidence ${payload.confidence.toFixed(2)}` : "";
      appendTimeline(`Finished: ${displayTitle(title)}`, conf);
      const summarySource = String(payload.summary ?? payload.reason ?? "");
      const citePrefix = citeIdPrefix(title, pageResults.value.length);
      pageResults.value = [
        ...pageResults.value,
        {
          title,
          citePrefix,
          wikipedia_article_url: String(payload.wikipedia_article_url ?? ""),
          summary_html: renderWikiCitedMarkdown(summarySource, citePrefix),
          whats_new_html: renderWikiCitedMarkdown(String(payload.whats_new ?? ""), citePrefix),
          suggested_update_html: renderWikiCitedMarkdown(String(payload.suggested_update ?? ""), citePrefix),
          sections_to_update: parseSections(payload.sections_to_update),
          sections_skipped: parseSectionsSkipped(payload.sections_skipped_not_in_article),
          citations: normalizeCitations(payload.citations),
          confidence: typeof payload.confidence === "number" ? payload.confidence : undefined,
          geo_distribution: parseGeoDistribution(payload.geo_distribution),
          geo_notable_countries: parseGeoNotableCountries(payload.geo_notable_countries),
          geo_signal_summary: parseGeoSignalSummary(payload.geo_signal_summary),
        },
      ];
      break;
    }
    case "EVENTS_SYNTHESIZED": {
      const eventName = String(payload.event_name ?? "Unspecified event");
      eventCandidates.value = [...eventCandidates.value, eventName];
      appendTimeline(`Event candidate: ${eventName}`);
      break;
    }
    case "RUN_COMPLETED":
      isRunInProgress.value = false;
      appendTimeline("Run completed");
      error.value = "";
      break;
    case "RUN_ERROR": {
      isRunInProgress.value = false;
      const detail = String(payload.error ?? "").trim();
      appendTimeline(detail ? `Run error: ${detail}` : "Run error");
      error.value = detail || "Run failed";
      break;
    }
    default:
      appendTimeline(type.toLowerCase().replaceAll("_", " "));
  }
};

onMounted(() => {
  fetchHours()
    .then((list) => {
      hours.value = list;
    })
    .catch((err: Error) => {
      error.value = err.message;
    });
});

onUnmounted(() => {
  activeStream.value?.close();
  activeStream.value = null;
});

const handleRun = async (): Promise<void> => {
  error.value = "";
  isRunInProgress.value = true;
  timeline.value = [];
  timelineCounter = 0;
  pageResults.value = [];
  eventCandidates.value = [];
  activeStream.value?.close();
  activeStream.value = null;

  const topStr = String(topKPages.value).trim();
  const parsedTopK = topStr === "" ? undefined : Number.parseInt(topStr, 10);
  const topK = Number.isNaN(parsedTopK ?? NaN) ? undefined : parsedTopK;

  try {
    const hour = String(selectedHour.value);
    const run = await startRun(hour, topK);
    activeStream.value = subscribeToRun(run.run_id, handleRunEvent);
  } catch (err) {
    isRunInProgress.value = false;
    error.value = err instanceof Error ? err.message : "Failed to run analysis";
  }
};
</script>

<style scoped>
.run-status {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  color: #54595d;
  font-size: 0.9rem;
}

.run-status__spinner {
  width: 0.9rem;
  height: 0.9rem;
  border: 2px solid #c8ccd1;
  border-top-color: #36c;
  border-radius: 50%;
  animation: run-spin 0.8s linear infinite;
}

@keyframes run-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
