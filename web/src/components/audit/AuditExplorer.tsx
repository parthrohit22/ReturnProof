import { useState } from "react";

import { EvidenceStatusBadge, ProvenanceBadge } from "../shared/StatusBadges";
import { formatFieldName, formatTimestamp, formatValue } from "../../lib/format";
import type { EvidenceClaim, EvidenceStatus } from "../../types/audit";

interface AuditExplorerProps {
  evidence: EvidenceClaim[];
}

const FILTERS: Array<EvidenceStatus | "ALL"> = [
  "ALL",
  "ACCEPTED",
  "CORROBORATED",
  "SUSPECT",
  "CORRUPTED",
  "SUPERSEDED",
  "REJECTED",
  "UNRESOLVED",
];

export function AuditExplorer({ evidence }: AuditExplorerProps) {
  const [filter, setFilter] = useState<EvidenceStatus | "ALL">("ALL");

  const visible = filter === "ALL" ? evidence : evidence.filter((claim) => claim.status === filter);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-1.5">
        {FILTERS.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setFilter(option)}
            aria-pressed={filter === option}
            className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
              filter === option
                ? "bg-accent text-text-inverse"
                : "bg-surface-sunken text-text-secondary hover:text-text-primary"
            }`}
          >
            {option === "ALL" ? "All" : formatFieldName(option.toLowerCase())}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full min-w-[900px] text-left text-xs">
          <thead className="border-b border-border bg-surface-sunken uppercase tracking-wide text-text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">Field</th>
              <th className="px-3 py-2 font-medium">Value</th>
              <th className="px-3 py-2 font-medium">Source</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Provenance</th>
              <th className="px-3 py-2 font-medium">Reason</th>
              <th className="px-3 py-2 font-medium">Reference</th>
              <th className="px-3 py-2 font-medium">Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((claim) => (
              <tr key={claim.claim_id} className="border-b border-border last:border-b-0">
                <td className="px-3 py-2 font-medium text-text-primary">
                  {formatFieldName(claim.field)}
                </td>
                <td className="px-3 py-2 font-mono-tabular text-text-secondary">
                  {formatValue(claim.value)}
                </td>
                <td className="px-3 py-2 text-text-secondary">{formatFieldName(claim.source)}</td>
                <td className="px-3 py-2">
                  <EvidenceStatusBadge status={claim.status} size="sm" />
                </td>
                <td className="px-3 py-2">
                  <ProvenanceBadge provenance={claim.authority} size="sm" />
                </td>
                <td className="max-w-[280px] px-3 py-2 text-text-secondary">{claim.reason}</td>
                <td className="px-3 py-2 font-mono-tabular text-text-muted">
                  {claim.source_reference}
                </td>
                <td className="px-3 py-2 font-mono-tabular text-text-muted">
                  {formatTimestamp(claim.timestamp)}
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-text-muted">
                  No evidence with this status.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
