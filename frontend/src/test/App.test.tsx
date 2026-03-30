import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import App from "../App";

test("renders hour selector", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ hours: ["2026-03-29T12:00:00"] }),
    }),
  );
  render(<App />);
  expect(await screen.findByLabelText(/select hour/i)).toBeInTheDocument();
  vi.unstubAllGlobals();
});
