import { describe, expect, it } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { NewReconciliation } from "../routes/NewReconciliation";
import { renderWithProviders, mockFetch } from "./testUtils";

describe("new reconciliation validation UX", () => {
  it("shows structured validation errors from the API and lets the operator fix them", async () => {
    mockFetch([
      {
        method: "POST",
        match: /\/reconciliations/,
        respond: () => ({
          status: 422,
          body: {
            error: "validation_error",
            message: "The return payload is invalid.",
            details: [
              {
                path: "supplier_events.1.credit_quantity",
                message: "Input should be greater than or equal to 0",
              },
              {
                path: "warehouse_report.items.0.damaged_quantity",
                message: "Cannot exceed quantity received",
              },
            ],
          },
        }),
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(<NewReconciliation />, ["/returns/new"]);

    await user.click(screen.getByRole("button", { name: /paste or upload json/i }));
    fireEvent.change(screen.getByLabelText(/return shipment json/i), {
      target: { value: '{"return_id": "RET-BAD"}' },
    });
    await user.click(screen.getByRole("button", { name: /run reconciliation/i }));

    expect(await screen.findByText(/unable to process return/i)).toBeInTheDocument();
    expect(screen.getByText("supplier_events.1.credit_quantity")).toBeInTheDocument();
    expect(screen.getByText("Input should be greater than or equal to 0")).toBeInTheDocument();
    expect(screen.getByText("warehouse_report.items.0.damaged_quantity")).toBeInTheDocument();

    // Operator can still edit the JSON after the error is shown.
    const textarea = screen.getByLabelText(/return shipment json/i);
    expect(textarea).toBeEnabled();
  });

  it("catches invalid JSON before ever calling the API", async () => {
    const fetchMock = mockFetch([
      { method: "GET", match: /\/examples$/, respond: () => ({ status: 200, body: { examples: [] } }) },
    ]);
    const user = userEvent.setup();
    renderWithProviders(<NewReconciliation />, ["/returns/new"]);

    await user.click(screen.getByRole("button", { name: /paste or upload json/i }));
    fireEvent.change(screen.getByLabelText(/return shipment json/i), {
      target: { value: "{not valid json" },
    });
    await user.click(screen.getByRole("button", { name: /run reconciliation/i }));

    expect(await screen.findByText(/isn't valid json/i)).toBeInTheDocument();
    const postCalls = fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
    expect(postCalls).toHaveLength(0);
  });
});
