import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ReturnsQueue } from "../routes/ReturnsQueue";
import { renderWithProviders, mockFetch } from "./testUtils";

describe("API error recovery", () => {
  it("shows a recoverable error state when the API is unreachable, then recovers on retry", async () => {
    let callCount = 0;
    const fetchMock = vi.fn(async () => {
      callCount += 1;
      if (callCount === 1) {
        throw new TypeError("Failed to fetch");
      }
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    renderWithProviders(<ReturnsQueue />);

    expect(await screen.findByText(/could not reach the returnproof api/i)).toBeInTheDocument();
    const retryButton = screen.getByRole("button", { name: /try again/i });

    await user.click(retryButton);

    await waitFor(() => {
      expect(screen.getByText(/no reconciliations yet/i)).toBeInTheDocument();
    });
  });

  it("shows an empty state distinct from an error when there are genuinely no runs", async () => {
    mockFetch([
      { method: "GET", match: /\/reconciliations$/, respond: () => ({ status: 200, body: [] }) },
    ]);

    renderWithProviders(<ReturnsQueue />);

    expect(await screen.findByText(/no reconciliations yet/i)).toBeInTheDocument();
  });
});
