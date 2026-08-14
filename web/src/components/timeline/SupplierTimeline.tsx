import { ArrowDownToLine, Clock3 } from "lucide-react";

import { EvidenceStatusBadge } from "../shared/StatusBadges";
import { formatFieldName, formatTimestamp, formatValue } from "../../lib/format";
import type { EvidenceClaim } from "../../types/audit";

interface RawSupplierEvent {
  event_id?: string;
  received_at?: string;
}

interface SupplierTimelineProps {
  evidence: EvidenceClaim[];
  /** The raw submitted payload, used only to show arrival time (`received_at`)
   * alongside the engine's own business-time ordering. Never used to
   * reorder or reinterpret anything the engine already decided. */
  rawSupplierEvents: RawSupplierEvent[];
}

interface EventGroup {
  eventId: string;
  timestamp: string | null;
  status: EvidenceClaim["status"];
  claims: EvidenceClaim[];
  receivedAt: string | null;
}

export function SupplierTimeline({ evidence, rawSupplierEvents }: SupplierTimelineProps) {
  const supplierClaims = evidence.filter((claim) => claim.source === "SUPPLIER");
  const groups = new Map<string, EventGroup>();

  for (const claim of supplierClaims) {
    const existing = groups.get(claim.source_reference);
    if (existing) {
      existing.claims.push(claim);
      continue;
    }
    const rawEvent = rawSupplierEvents.find((event) => event.event_id === claim.source_reference);
    groups.set(claim.source_reference, {
      eventId: claim.source_reference,
      timestamp: claim.timestamp,
      status: claim.status,
      claims: [claim],
      receivedAt: rawEvent?.received_at ?? null,
    });
  }

  const ordered = Array.from(groups.values()).sort((a, b) =>
    (a.timestamp ?? "").localeCompare(b.timestamp ?? ""),
  );

  if (ordered.length === 0) {
    return <p className="text-sm text-text-muted">No supplier events reported for this item.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
        Business event order
      </p>
      <ol className="flex flex-col gap-2">
        {ordered.map((group) => {
          const instruction = group.claims.find((claim) => claim.field === "instruction");
          return (
            <li
              key={group.eventId}
              className="rounded-md border border-border bg-surface px-3 py-2.5"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Clock3 size={14} className="text-text-muted" aria-hidden="true" />
                  <span className="font-mono-tabular text-sm text-text-primary">
                    {formatTimestamp(group.timestamp)}
                  </span>
                  <span className="text-xs text-text-muted">{group.eventId}</span>
                </div>
                <EvidenceStatusBadge status={group.status} size="sm" />
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-secondary">
                {instruction && (
                  <span>
                    Instruction:{" "}
                    <span className="font-medium text-text-primary">
                      {formatValue(instruction.value)}
                    </span>
                  </span>
                )}
                {group.receivedAt && (
                  <span className="flex items-center gap-1 text-text-muted">
                    <ArrowDownToLine size={12} aria-hidden="true" />
                    Received {formatTimestamp(group.receivedAt)}
                  </span>
                )}
              </div>
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-text-muted hover:text-text-secondary">
                  All fields
                </summary>
                <ul className="mt-1.5 flex flex-col gap-1">
                  {group.claims.map((claim) => (
                    <li key={claim.claim_id} className="flex justify-between text-xs">
                      <span className="text-text-secondary">{formatFieldName(claim.field)}</span>
                      <span className="font-mono-tabular text-text-primary">
                        {formatValue(claim.value)}
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
