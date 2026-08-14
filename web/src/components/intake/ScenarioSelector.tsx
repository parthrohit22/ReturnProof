import { FileJson } from "lucide-react";

import { useExamples } from "../../lib/api/queries";
import { LoadingState } from "../shared/LoadingState";
import { ErrorState } from "../shared/ErrorState";

interface ScenarioSelectorProps {
  selected: string | null;
  onSelect: (name: string) => void;
}

function labelFor(name: string): string {
  return name
    .split("_")
    .map((word) => word[0]?.toUpperCase() + word.slice(1))
    .join(" ");
}

export function ScenarioSelector({ selected, onSelect }: ScenarioSelectorProps) {
  const { data: examples, isLoading, isError, error, refetch } = useExamples();

  if (isLoading) return <LoadingState label="Loading built-in scenarios…" />;
  if (isError) return <ErrorState error={error} onRetry={() => refetch()} />;

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {examples?.map((name) => (
        <button
          key={name}
          type="button"
          onClick={() => onSelect(name)}
          aria-pressed={selected === name}
          className={`flex items-start gap-2 rounded-md border px-3 py-2.5 text-left text-sm transition-colors ${
            selected === name
              ? "border-accent bg-accent-surface"
              : "border-border bg-surface hover:bg-surface-sunken"
          }`}
        >
          <FileJson size={16} className="mt-0.5 shrink-0 text-text-muted" aria-hidden="true" />
          <span>
            <span className="block font-medium text-text-primary">{labelFor(name)}</span>
            <span className="block text-xs text-text-muted">{name}.json</span>
          </span>
        </button>
      ))}
    </div>
  );
}
