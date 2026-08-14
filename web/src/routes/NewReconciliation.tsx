import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PlayCircle } from "lucide-react";

import { Panel } from "../components/shared/Panel";
import { ScenarioSelector } from "../components/intake/ScenarioSelector";
import { JsonInput } from "../components/intake/JsonInput";
import { ShipmentPreviewCard } from "../components/intake/ShipmentPreviewCard";
import { ValidationErrors } from "../components/intake/ValidationErrors";
import { useCreateReconciliation, useExample } from "../lib/api/queries";
import { ApiError } from "../types/api";
import { parseShipmentPreview } from "../types/shipment";

type Mode = "scenario" | "json";

export function NewReconciliation() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("scenario");
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [jsonText, setJsonText] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);

  const { data: exampleContent } = useExample(mode === "scenario" ? selectedScenario : null);
  const createReconciliation = useCreateReconciliation();

  useEffect(() => {
    if (exampleContent) {
      setJsonText(JSON.stringify(exampleContent, null, 2));
    }
  }, [exampleContent]);

  let parsedPayload: unknown = null;
  let livePreview: ReturnType<typeof parseShipmentPreview> = null;
  if (jsonText.trim()) {
    try {
      parsedPayload = JSON.parse(jsonText);
      livePreview = parseShipmentPreview(parsedPayload);
    } catch {
      // Invalid JSON is expected mid-edit, only surface it on submit.
    }
  }

  function handleModeChange(next: Mode) {
    setMode(next);
    setParseError(null);
    createReconciliation.reset();
  }

  function handleRun() {
    setParseError(null);
    let payload: unknown;
    try {
      payload = JSON.parse(jsonText);
    } catch {
      setParseError("This isn't valid JSON. Check for a missing comma or bracket.");
      return;
    }
    createReconciliation.mutate(
      { payload, scenarioName: mode === "scenario" ? selectedScenario : null },
      {
        onSuccess: (run) => navigate(`/returns/${run.id}`),
      },
    );
  }

  const apiError =
    createReconciliation.error instanceof ApiError ? createReconciliation.error : null;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold text-text-primary">New Reconciliation</h1>
        <p className="text-sm text-text-secondary">
          Load a built-in scenario, paste return data, or upload a JSON file.
        </p>
      </div>

      <div className="flex gap-1 rounded-md border border-border bg-surface-sunken p-1 w-fit">
        {(["scenario", "json"] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => handleModeChange(option)}
            aria-pressed={mode === option}
            className={`rounded px-3 py-1.5 text-sm font-medium transition-colors ${
              mode === option
                ? "bg-surface text-text-primary shadow-sm"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            {option === "scenario" ? "Built-in scenario" : "Paste or upload JSON"}
          </button>
        ))}
      </div>

      <Panel title={mode === "scenario" ? "Choose a scenario" : "Return shipment JSON"}>
        {mode === "scenario" ? (
          <ScenarioSelector selected={selectedScenario} onSelect={setSelectedScenario} />
        ) : (
          <JsonInput value={jsonText} onChange={setJsonText} />
        )}
      </Panel>

      {livePreview && (
        <Panel title="Input preview">
          <ShipmentPreviewCard preview={livePreview} />
        </Panel>
      )}

      {parseError && (
        <div className="rounded-md border border-danger-border bg-danger-surface p-3 text-sm text-danger">
          {parseError}
        </div>
      )}

      {apiError?.body && <ValidationErrors errorBody={apiError.body} />}
      {createReconciliation.isError && !apiError?.body && (
        <div className="rounded-md border border-danger-border bg-danger-surface p-3 text-sm text-danger">
          {createReconciliation.error instanceof Error
            ? createReconciliation.error.message
            : "Something went wrong."}
        </div>
      )}

      <div>
        <button
          type="button"
          onClick={handleRun}
          disabled={!jsonText.trim() || createReconciliation.isPending}
          className="flex items-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-text-inverse hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <PlayCircle size={16} aria-hidden="true" />
          {createReconciliation.isPending ? "Processing return…" : "Run reconciliation"}
        </button>
      </div>
    </div>
  );
}
