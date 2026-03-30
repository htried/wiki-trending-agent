import { type ReactElement, useEffect, useMemo, useState } from "react";

import { fetchHours, startRun, subscribeToRun, type RunEvent } from "./api";
import EventCandidates from "./components/EventCandidates";
import HourSelector from "./components/HourSelector";
import PageResultsList from "./components/PageResultsList";
import RunControls from "./components/RunControls";
import RunTimeline from "./components/RunTimeline";

export default function App(): ReactElement {
  const [hours, setHours] = useState<string[]>([]);
  const [selectedHour, setSelectedHour] = useState("");
  const [topKPages, setTopKPages] = useState("");
  const [error, setError] = useState("");
  const [timeline, setTimeline] = useState<string[]>([]);
  const [pageResults, setPageResults] = useState<Array<{ title: string; reason: string }>>([]);
  const [eventCandidates, setEventCandidates] = useState<string[]>([]);

  useEffect(() => {
    fetchHours()
      .then(setHours)
      .catch((err: Error) => {
        setError(err.message);
      });
  }, []);

  const canRun = useMemo(() => selectedHour.length > 0, [selectedHour]);

  const mapEventLabel = (event: RunEvent): string => {
    if (event.type === "RUN_STARTED") return "Run started";
    if (event.type === "RUN_COMPLETED") return "Run completed";
    if (event.type === "RUN_ERROR") return "Run error";
    return event.type.toLowerCase().replaceAll("_", " ");
  };

  const handleRunEvent = (event: RunEvent): void => {
    setTimeline((prev) => [...prev, mapEventLabel(event)]);

    if (event.type === "REASONING_DONE") {
      const title = String(event.payload.page_title ?? "Unknown page");
      const reason = String(event.payload.reason ?? "No reason available");
      setPageResults((prev) => [...prev, { title, reason }]);
    }
    if (event.type === "EVENTS_SYNTHESIZED") {
      const eventName = String(event.payload.event_name ?? "Unspecified event");
      setEventCandidates((prev) => [...prev, eventName]);
    }
  };

  const handleRun = async (): Promise<void> => {
    setError("");
    setTimeline([]);
    setPageResults([]);
    setEventCandidates([]);

    try {
      const parsedTopK = topKPages.trim() === "" ? undefined : Number.parseInt(topKPages, 10);
      const run = await startRun(selectedHour, Number.isNaN(parsedTopK ?? NaN) ? undefined : parsedTopK);
      subscribeToRun(run.run_id, handleRunEvent);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to run analysis";
      setError(message);
    }
  };

  return (
    <main>
      <header className="app-header">
        <h1>Wiki Trending Agent</h1>
      </header>
      <HourSelector hours={hours} selectedHour={selectedHour} onSelect={setSelectedHour} />
      <RunControls
        disabled={!canRun}
        topKPages={topKPages}
        onTopKPagesChange={setTopKPages}
        onRun={handleRun}
      />
      <RunTimeline events={timeline} />
      <PageResultsList results={pageResults} />
      <EventCandidates events={eventCandidates} />
      {error ? <p role="alert">{error}</p> : null}
    </main>
  );
}
