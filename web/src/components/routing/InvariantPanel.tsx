import { CheckCircle2, XCircle } from "lucide-react";

import type { Allocation, InvariantCheck } from "../../types/audit";

interface InvariantPanelProps {
  invariants: InvariantCheck[];
  allocations: Allocation[];
  quantityReceived: number;
}

function totalFor(allocations: Allocation[], route: Allocation["route"]): number {
  return allocations
    .filter((allocation) => allocation.route === route)
    .reduce((sum, allocation) => sum + allocation.quantity, 0);
}

export function InvariantPanel({ invariants, allocations, quantityReceived }: InvariantPanelProps) {
  const allocated = allocations.reduce((sum, allocation) => sum + allocation.quantity, 0);
  const allPassed = invariants.every((check) => check.passed);

  const rows: Array<[string, number]> = [
    ["Received", quantityReceived],
    ["Scrap", totalFor(allocations, "SCRAP")],
    ["Restock", totalFor(allocations, "RESTOCK")],
    ["Quarantine", totalFor(allocations, "QUARANTINE")],
    ["Allocated", allocated],
  ];

  return (
    <div className="flex flex-col gap-3">
      <dl className="grid grid-cols-2 gap-x-6 gap-y-1.5 sm:grid-cols-3">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-center justify-between gap-2">
            <dt className="text-xs text-text-secondary">{label}</dt>
            <dd className="font-mono-tabular text-sm font-medium text-text-primary">{value}</dd>
          </div>
        ))}
      </dl>
      <div
        className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium ${
          allPassed
            ? "border-success-border bg-success-surface text-success"
            : "border-danger-border bg-danger-surface text-danger"
        }`}
      >
        {allPassed ? (
          <CheckCircle2 size={16} aria-hidden="true" />
        ) : (
          <XCircle size={16} aria-hidden="true" />
        )}
        {allPassed ? "PASS" : "INVARIANT FAILURE"}
        <span className="font-normal text-text-secondary">
          {invariants.map((check) => check.detail).join(", ")}
        </span>
      </div>
    </div>
  );
}
