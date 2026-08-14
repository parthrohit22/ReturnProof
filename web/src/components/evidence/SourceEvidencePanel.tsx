import { Truck, Warehouse } from "lucide-react";

import { EvidenceStatusBadge } from "../shared/StatusBadges";
import { formatFieldName, formatValue } from "../../lib/format";
import type { EvidenceClaim } from "../../types/audit";

interface EvidenceColumnProps {
  title: string;
  icon: typeof Warehouse;
  claims: EvidenceClaim[];
}

function EvidenceColumn({ title, icon: Icon, claims }: EvidenceColumnProps) {
  return (
    <div className="flex-1 rounded-md border border-border bg-surface">
      <header className="flex items-center gap-2 border-b border-border px-3 py-2">
        <Icon size={15} className="text-text-muted" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
      </header>
      <dl className="divide-y divide-border">
        {claims.length === 0 && (
          <p className="px-3 py-3 text-xs text-text-muted">No evidence reported.</p>
        )}
        {claims.map((claim) => (
          <div key={claim.claim_id} className="flex items-center justify-between gap-3 px-3 py-2">
            <dt className="text-xs text-text-secondary">{formatFieldName(claim.field)}</dt>
            <dd className="flex items-center gap-2">
              <span className="font-mono-tabular text-sm text-text-primary">
                {formatValue(claim.value)}
              </span>
              <EvidenceStatusBadge status={claim.status} size="sm" />
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

interface SourceEvidencePanelProps {
  evidence: EvidenceClaim[];
}

/**
 * Fields are shown side by side for scanning, not implied to share
 * identical semantics, quantity_received and acknowledged_quantity are
 * genuinely different facts and are labelled as such (see lib/format).
 */
export function SourceEvidencePanel({ evidence }: SourceEvidencePanelProps) {
  const warehouseClaims = evidence.filter((claim) => claim.source === "WAREHOUSE");
  const currentSupplierClaims = evidence.filter(
    (claim) => claim.source === "SUPPLIER" && claim.status !== "SUPERSEDED",
  );

  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <EvidenceColumn title="Warehouse" icon={Warehouse} claims={warehouseClaims} />
      <EvidenceColumn title="Supplier (current)" icon={Truck} claims={currentSupplierClaims} />
    </div>
  );
}
