import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";

import { ReturnWorkspace } from "../routes/ReturnWorkspace";
import { renderWithProviders, mockFetch } from "./testUtils";
import multiItemReturnRun from "./fixtures/multi_item_return_run.json";

/**
 * HIGH-2 regression: the item switcher must show the correct decision for
 * whichever item is selected, and switching items must not leave the
 * previous item's routing/quantity on screen. multi_item_return.json was
 * built with three distinct quantities (20 / 8 / 12) specifically so a
 * cross-item leak would show up as the wrong number, not just the wrong
 * label.
 */
describe("multi-item item switcher", () => {
  it("shows each item's own decision and never a previous item's leftover state", async () => {
    mockFetch([
      {
        method: "GET",
        match: /\/reconciliations\/.+/,
        respond: () => ({ status: 200, body: multiItemReturnRun }),
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(
      <Routes>
        <Route path="/returns/:id" element={<ReturnWorkspace />} />
      </Routes>,
      [`/returns/${multiItemReturnRun.id}`],
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "RET-2026-008" })).toBeInTheDocument();
    });

    // the shipment overall requires review because one of the three items is quarantined
    expect(screen.getByText("Requires review")).toBeInTheDocument();

    const itemButton = (itemId: string) => screen.getByRole("button", { name: itemId });

    // --- Item A (default selection): clean RESTOCK, no conflicts ---
    expect(screen.getByText("0 detected for this item")).toBeInTheDocument();
    let routingPanel = screen.getByText("Physical routing").closest("section")!;
    expect(within(routingPanel).getByText("20")).toBeInTheDocument();
    expect(within(routingPanel).getAllByText("Restock").length).toBeGreaterThan(0);
    expect(within(routingPanel).queryByText("Scrap")).not.toBeInTheDocument();
    expect(within(routingPanel).queryByText("Quarantine")).not.toBeInTheDocument();

    // --- switch to Item B: unsafe damage, safety override, SCRAP ---
    await user.click(itemButton("YOGURT-22-1"));
    expect(screen.getByText("1 detected for this item")).toBeInTheDocument();
    routingPanel = screen.getByText("Physical routing").closest("section")!;
    expect(within(routingPanel).getByText("8")).toBeInTheDocument();
    expect(within(routingPanel).getAllByText("Scrap").length).toBeGreaterThan(0);
    expect(within(routingPanel).queryByText("20")).not.toBeInTheDocument();
    expect(within(routingPanel).queryByText("Restock")).not.toBeInTheDocument();
    expect(within(routingPanel).queryByText("Quarantine")).not.toBeInTheDocument();

    // commercial credit for item B is fully independent of the SCRAP routing (R008)
    const commercialPanel = screen.getByText("Commercial outcome").closest("section")!;
    expect(within(commercialPanel).getByText("8")).toBeInTheDocument();

    // --- switch to Item C: unresolved identity, QUARANTINE ---
    await user.click(itemButton("SAUCE-99-1"));
    expect(screen.getByText("1 detected for this item")).toBeInTheDocument();
    routingPanel = screen.getByText("Physical routing").closest("section")!;
    expect(within(routingPanel).getByText("12")).toBeInTheDocument();
    expect(within(routingPanel).getAllByText("Quarantine").length).toBeGreaterThan(0);
    expect(within(routingPanel).queryByText("8")).not.toBeInTheDocument();
    expect(within(routingPanel).queryByText("20")).not.toBeInTheDocument();
    expect(within(routingPanel).queryByText("Restock")).not.toBeInTheDocument();
    expect(within(routingPanel).queryByText("Scrap")).not.toBeInTheDocument();

    // --- switch back to Item A: confirm no state stuck from item C ---
    await user.click(itemButton("CEREAL-12-1"));
    expect(screen.getByText("0 detected for this item")).toBeInTheDocument();
    routingPanel = screen.getByText("Physical routing").closest("section")!;
    expect(within(routingPanel).getByText("20")).toBeInTheDocument();
    expect(within(routingPanel).queryByText("12")).not.toBeInTheDocument();
    expect(within(routingPanel).queryByText("Quarantine")).not.toBeInTheDocument();
  });
});
