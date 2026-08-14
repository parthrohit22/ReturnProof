import { GitCompareArrows } from "lucide-react";

import { EvidenceStatusBadge } from "../shared/StatusBadges";
import { formatFieldName, formatValue } from "../../lib/format";
import type { Conflict, EvidenceClaim, ResolvedField } from "../../types/audit";

interface ConflictCardProps {
  conflict: Conflict;
  evidence: EvidenceClaim[];
  resolvedFields: ResolvedField[];
}

const CONFLICT_LABELS: Record<Conflict["type"], string> = {
  CONDITION_DISAGREEMENT: "Condition disagreement",
  BATCH_MISMATCH: "Batch mismatch",
  QUANTITY_OR_ELIGIBILITY_DISPUTE: "Quantity or eligibility dispute",
  SUPPLIER_STATE_AMBIGUOUS: "Supplier state ambiguous",
};

export function ConflictCard({ conflict, evidence, resolvedFields }: ConflictCardProps) {
  const involvedClaims = conflict.claim_ids
    .map((id) => evidence.find((claim) => claim.claim_id === id))
    .filter((claim): claim is EvidenceClaim => claim !== undefined);

  const warehouseClaims = involvedClaims.filter((claim) => claim.source === "WAREHOUSE");
  const supplierClaims = involvedClaims.filter((claim) => claim.source === "SUPPLIER");

  const involvedFieldNames = new Set(involvedClaims.map((claim) => claim.field));
  const resolution = resolvedFields.find((field) => involvedFieldNames.has(field.field));

  return (
    <div className="rounded-md border border-warning-border bg-surface">
      <header className="flex items-center gap-2 border-b border-border bg-warning-surface px-3 py-2">
        <GitCompareArrows size={15} className="text-warning" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-text-primary">
          {CONFLICT_LABELS[conflict.type]}
        </h3>
      </header>
      <div className="p-3">
        <p className="text-sm text-text-secondary">{conflict.description}</p>
        {(warehouseClaims.length > 0 || supplierClaims.length > 0) && (
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {warehouseClaims.length > 0 && (
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
                  Warehouse
                </p>
                <ul className="mt-1 flex flex-col gap-1">
                  {warehouseClaims.map((claim) => (
                    <li key={claim.claim_id} className="flex items-center justify-between gap-2">
                      <span className="text-xs text-text-secondary">
                        {formatFieldName(claim.field)}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="font-mono-tabular text-xs text-text-primary">
                          {formatValue(claim.value)}
                        </span>
                        <EvidenceStatusBadge status={claim.status} size="sm" />
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {supplierClaims.length > 0 && (
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
                  Supplier
                </p>
                <ul className="mt-1 flex flex-col gap-1">
                  {supplierClaims.map((claim) => (
                    <li key={claim.claim_id} className="flex items-center justify-between gap-2">
                      <span className="text-xs text-text-secondary">
                        {formatFieldName(claim.field)}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="font-mono-tabular text-xs text-text-primary">
                          {formatValue(claim.value)}
                        </span>
                        <EvidenceStatusBadge status={claim.status} size="sm" />
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        {resolution && (
          <div className="mt-3 border-t border-border pt-2">
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
              Resolution
            </p>
            <p className="mt-0.5 text-xs text-text-secondary">{resolution.reason}</p>
          </div>
        )}
      </div>
    </div>
  );
}
