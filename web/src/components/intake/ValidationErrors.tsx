import { AlertOctagon } from "lucide-react";

import type { ApiErrorBody } from "../../types/api";

interface ValidationErrorsProps {
  errorBody: ApiErrorBody;
}

export function ValidationErrors({ errorBody }: ValidationErrorsProps) {
  const count = errorBody.details.length;

  return (
    <div className="rounded-md border border-danger-border bg-danger-surface p-3 text-sm">
      <div className="flex items-center gap-2 font-medium text-danger">
        <AlertOctagon size={15} aria-hidden="true" />
        Unable to process return
      </div>
      {count > 0 ? (
        <>
          <p className="mt-1 text-xs text-danger">
            {count} validation {count === 1 ? "issue" : "issues"}
          </p>
          <ul className="mt-2 flex flex-col gap-2">
            {errorBody.details.map((detail, index) => (
              <li key={`${detail.path}-${index}`} className="rounded bg-surface px-2.5 py-1.5">
                <p className="font-mono text-xs text-text-primary">{detail.path}</p>
                <p className="text-xs text-text-secondary">{detail.message}</p>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="mt-1 text-xs text-danger">{errorBody.message}</p>
      )}
    </div>
  );
}
