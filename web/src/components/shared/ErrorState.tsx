import { AlertOctagon, RotateCcw } from "lucide-react";

import { ApiError } from "../../types/api";

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}

/**
 * A single, consistent way to present "something went wrong" with a
 * concrete recovery action, used for API failures across the app.
 */
export function ErrorState({ error, onRetry, title = "Something went wrong" }: ErrorStateProps) {
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : "An unexpected error occurred.";

  return (
    <div className="flex flex-col items-center gap-2 rounded-md border border-danger-border bg-danger-surface px-6 py-10 text-center">
      <AlertOctagon size={28} className="text-danger" aria-hidden="true" />
      <p className="text-sm font-medium text-text-primary">{title}</p>
      <p className="max-w-sm text-sm text-text-secondary">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 inline-flex items-center gap-1.5 rounded border border-border-strong bg-surface px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-sunken"
        >
          <RotateCcw size={14} aria-hidden="true" />
          Try again
        </button>
      )}
    </div>
  );
}
