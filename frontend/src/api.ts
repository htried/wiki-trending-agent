export async function fetchHours(baseUrl = "http://localhost:8000"): Promise<string[]> {
  const response = await fetch(`${baseUrl}/hours`);
  if (!response.ok) {
    throw new Error(`Failed to fetch hours (${response.status})`);
  }
  const payload = (await response.json()) as { hours: string[] };
  return payload.hours;
}

export type RunStartResponse = {
  run_id: string;
  status: string;
};

export type RunEvent = {
  type: string;
  payload: Record<string, unknown>;
};

export async function startRun(
  hour: string,
  topKPages?: number,
  baseUrl = "http://localhost:8000",
): Promise<RunStartResponse> {
  const payload: { hour: string; top_k_pages?: number } = { hour };
  if (topKPages !== undefined) {
    payload.top_k_pages = topKPages;
  }
  const response = await fetch(`${baseUrl}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to start run (${response.status})`);
  }

  return (await response.json()) as RunStartResponse;
}

export function subscribeToRun(
  runId: string,
  onEvent: (event: RunEvent) => void,
  baseUrl = "http://localhost:8000",
): EventSource {
  const stream = new EventSource(`${baseUrl}/runs/${runId}/stream`);
  const eventTypes = [
    "RUN_STARTED",
    "PAGES_SELECTED",
    "PAGE_ANALYSIS_STARTED",
    "AGENT_TOOL_CALL",
    "AGENT_TOOL_RESULT",
    "AGENT_REASONING",
    "NEWS_FETCHED",
    "WIKI_FETCHED",
    "REASONING_DONE",
    "EVENTS_SYNTHESIZED",
    "RUN_COMPLETED",
    "RUN_ERROR",
  ];

  for (const eventType of eventTypes) {
    stream.addEventListener(eventType, (event) => {
      const payload = JSON.parse((event as MessageEvent).data) as Record<string, unknown>;
      onEvent({ type: eventType, payload });
      if (eventType === "RUN_COMPLETED" || eventType === "RUN_ERROR") {
        stream.close();
      }
    });
  }

  return stream;
}
