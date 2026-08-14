import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";

import { ReturnWorkspace } from "../routes/ReturnWorkspace";
import { renderWithProviders, mockFetch } from "./testUtils";
import compoundFailureRun from "./fixtures/compound_failure_run.json";

describe("commercial and physical separation", () => {
  it("shows credit quantity as a distinct number from the scrap quantity, with an explanation", async () => {
    mockFetch([
      {
        method: "GET",
        match: /\/reconciliations\/.+/,
        respond: () => ({ status: 200, body: compoundFailureRun }),
      },
    ]);

    renderWithProviders(
      <Routes>
        <Route path="/returns/:id" element={<ReturnWorkspace />} />
      </Routes>,
      [`/returns/${compoundFailureRun.id}`],
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "RET-2026-001" })).toBeInTheDocument();
    });

    // 6 units physically scrapped, but the supplier's credit figure (4) is
    // shown as its own independent number, not derived from the scrap
    // quantity, this is the whole point of R008.
    expect(screen.getByText(/commercial credit is resolved independently/i)).toBeInTheDocument();

    const commercialSection = screen.getByText("Commercial outcome").closest("section");
    expect(commercialSection).not.toBeNull();
    expect(commercialSection?.textContent).toContain("4");

    const routingSection = screen.getByText("Physical routing").closest("section");
    expect(routingSection?.textContent).toContain("6");
    expect(routingSection?.textContent).toContain("18");
  });
});
