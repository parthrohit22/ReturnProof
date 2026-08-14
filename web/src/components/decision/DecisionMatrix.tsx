import { Fragment, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { ProvenanceBadge } from "../shared/StatusBadges";
import { formatFieldName, formatValue } from "../../lib/format";
import type { EvidenceClaim, ResolvedField } from "../../types/audit";

interface DecisionMatrixProps {
  resolvedFields: ResolvedField[];
  evidence: EvidenceClaim[];
}

function findClaim(
  evidence: EvidenceClaim[],
  field: string,
  source: "WAREHOUSE" | "SUPPLIER",
): EvidenceClaim | undefined {
  if (source === "WAREHOUSE") {
    return evidence.find((claim) => claim.field === field && claim.source === "WAREHOUSE");
  }
  return evidence.find(
    (claim) => claim.field === field && claim.source === "SUPPLIER" && claim.status !== "SUPERSEDED",
  );
}

export function DecisionMatrix({ resolvedFields, evidence }: DecisionMatrixProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="border-b border-border bg-surface-sunken text-xs uppercase tracking-wide text-text-muted">
          <tr>
            <th className="w-6 px-2 py-2" />
            <th className="px-3 py-2 font-medium">Decision</th>
            <th className="px-3 py-2 font-medium">Warehouse</th>
            <th className="px-3 py-2 font-medium">Supplier</th>
            <th className="px-3 py-2 font-medium">Resolved</th>
            <th className="px-3 py-2 font-medium">Provenance</th>
          </tr>
        </thead>
        <tbody>
          {resolvedFields.map((field) => {
            const warehouseClaim = findClaim(evidence, field.field, "WAREHOUSE");
            const supplierClaim = findClaim(evidence, field.field, "SUPPLIER");
            const isOpen = expanded === field.field;
            const rejectedClaims = field.rejected_claim_ids
              .map((id) => evidence.find((claim) => claim.claim_id === id))
              .filter((claim): claim is EvidenceClaim => claim !== undefined);

            return (
              <Fragment key={field.field}>
                <tr
                  className="cursor-pointer border-b border-border last:border-b-0 hover:bg-surface-sunken"
                  onClick={() => setExpanded(isOpen ? null : field.field)}
                >
                  <td className="px-2 py-2.5 text-text-muted">
                    {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </td>
                  <td className="px-3 py-2.5 font-medium text-text-primary">
                    {formatFieldName(field.field)}
                  </td>
                  <td className="px-3 py-2.5 font-mono-tabular text-text-secondary">
                    {formatValue(warehouseClaim?.value)}
                  </td>
                  <td className="px-3 py-2.5 font-mono-tabular text-text-secondary">
                    {formatValue(supplierClaim?.value)}
                  </td>
                  <td className="px-3 py-2.5 font-mono-tabular font-medium text-text-primary">
                    {formatValue(field.value)}
                  </td>
                  <td className="px-3 py-2.5">
                    <ProvenanceBadge provenance={field.provenance} size="sm" />
                  </td>
                </tr>
                {isOpen && (
                  <tr className="border-b border-border bg-surface-sunken">
                    <td />
                    <td colSpan={5} className="px-3 py-3">
                      <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
                        Why this won
                      </p>
                      <p className="mt-1 text-sm text-text-secondary">{field.reason}</p>
                      {field.rules_applied.length > 0 && (
                        <p className="mt-2 text-xs text-text-muted">
                          Rules:{" "}
                          <span className="font-mono-tabular text-text-secondary">
                            {field.rules_applied.join(", ")}
                          </span>
                        </p>
                      )}
                      {rejectedClaims.length > 0 && (
                        <div className="mt-3 border-t border-border pt-2">
                          <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
                            Why competing evidence lost
                          </p>
                          <ul className="mt-1 flex flex-col gap-1">
                            {rejectedClaims.map((claim) => (
                              <li key={claim.claim_id} className="text-xs text-text-secondary">
                                <span className="font-medium text-text-primary">
                                  {claim.source === "WAREHOUSE" ? "Warehouse" : "Supplier"}
                                </span>{" "}
                                ({formatValue(claim.value)}): {claim.reason}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
