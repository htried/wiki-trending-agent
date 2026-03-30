import { render, screen, waitFor } from "@testing-library/vue";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import App from "../App.vue";

class FakeEventSource {
  private handlers = new Map<string, (event: MessageEvent) => void>();

  addEventListener(type: string, handler: (event: MessageEvent) => void): void {
    this.handlers.set(type, handler);
  }

  close(): void {}

  emit(type: string, payload: object): void {
    const handler = this.handlers.get(type);
    if (handler) {
      handler(new MessageEvent(type, { data: JSON.stringify(payload) }));
    }
  }
}

test("shows run progress updates", async () => {
  const user = userEvent.setup();
  const eventSource = new FakeEventSource();
  const eventSourceMock = vi.fn(() => eventSource);
  vi.stubGlobal("EventSource", eventSourceMock);
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ hours: ["2026-03-29T12:00:00"] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ run_id: "run-1", status: "queued" }),
      }),
  );

  render(App);
  const hourControl = await screen.findByLabelText(/select hour/i);
  await user.click(hourControl);
  const hourLabel = "2026-03-29T12:00:00";
  await waitFor(() => {
    expect(screen.getByText(hourLabel)).toBeInTheDocument();
  });
  await user.click(screen.getByText(hourLabel));

  const topKInput = screen.getByLabelText(/top k pages/i);
  await user.clear(topKInput);
  await user.type(topKInput, "3");

  await user.click(screen.getByRole("button", { name: /run analysis/i }));

  await waitFor(() => expect(eventSourceMock).toHaveBeenCalledTimes(1));
  const fetchMock = vi.mocked(fetch);
  const runCall = fetchMock.mock.calls[1];
  expect(runCall[0]).toContain("/runs");
  expect(String((runCall[1] as RequestInit).body)).toContain('"top_k_pages":3');

  eventSource.emit("RUN_STARTED", { run_id: "run-1", status: "running" });

  expect(await screen.findByText(/run started/i)).toBeInTheDocument();
  vi.unstubAllGlobals();
});
