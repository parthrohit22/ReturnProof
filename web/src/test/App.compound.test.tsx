import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "../App";
import { renderWithProviders, mockFetch } from "./testUtils";
import examplesList from "./fixtures/examples_list.json";
import compoundFailurePayload from "./fixtures/compound_failure_payload.json";
import compoundFailureRun from "./fixtures/compound_failure_run.json";
import compoundUnresolvedPayload from "./fixtures/compound_unresolved_payload.json";
import compoundUnresolvedRun from "./fixtures/compound_unresolved_run.json";

describe("resolvable compound failure flow", () => {
  it("loads the scenario, runs it, and shows the resolved decision", async () => {
    mockFetch([
      { method: "GET", match: /\/examples$/, respond: () => ({ status: 200, body: examplesList }) },
      {
        method: "GET",
        match: /\/examples\/compound_failure$/,
        respond: () => ({ status: 200, body: compoundFailurePayload }),
      },
      {
        method: "POST",
        match: /\/reconciliations/,
        respond: () => ({ status: 201, body: compoundFailureRun }),
      },
      {
        method: "GET",
        match: /\/reconciliations\/.+/,
        respond: () => ({ status: 200, body: compoundFailureRun }),
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(<App />, ["/returns/new"]);

    await user.click(await screen.findByRole("button", { name: /compound failure/i }));
    await user.click(await screen.findByRole("button", { name: /run reconciliation/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "RET-2026-001" })).toBeInTheDocument();
    });

    // Overview tab: physical routing and commercial separation visible immediately
    expect(screen.getByText("Resolved", { exact: true })).toBeInTheDocument();
    expect(screen.getAllByText("Scrap").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Restock").length).toBeGreaterThan(0);
    expect(screen.getByText("2026-10")).toBeInTheDocument();
    expect(screen.getByText("PASS")).toBeInTheDocument();

    // Evidence tab: corrupted warehouse batch, corroborated supplier batch, superseded event
    await user.click(screen.getByRole("button", { name: "Evidence" }));
    expect(screen.getByText("BA?9O2")).toBeInTheDocument();
    expect(screen.getAllByText("Corrupted").length).toBeGreaterThan(0);
    expect(screen.getAllByText("BA1902").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Corroborated").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Superseded").length).toBeGreaterThan(0);
  });
});

describe("unresolved compound failure flow", () => {
  it("loads the scenario, runs it, and shows a defensible quarantine", async () => {
    mockFetch([
      { method: "GET", match: /\/examples$/, respond: () => ({ status: 200, body: examplesList }) },
      {
        method: "GET",
        match: /\/examples\/compound_unresolved$/,
        respond: () => ({ status: 200, body: compoundUnresolvedPayload }),
      },
      {
        method: "POST",
        match: /\/reconciliations/,
        respond: () => ({ status: 201, body: compoundUnresolvedRun }),
      },
      {
        method: "GET",
        match: /\/reconciliations\/.+/,
        respond: () => ({ status: 200, body: compoundUnresolvedRun }),
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(<App />, ["/returns/new"]);

    await user.click(await screen.findByRole("button", { name: /compound unresolved/i }));
    await user.click(await screen.findByRole("button", { name: /run reconciliation/i }));

    await waitFor(() => {
      expect(screen.getByText("Requires review")).toBeInTheDocument();
    });

    expect(screen.getAllByText("Quarantine").length).toBeGreaterThan(0);
  });
});
