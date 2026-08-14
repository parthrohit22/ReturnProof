import { useState } from "react";
import { useParams } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";

import { useReconciliation } from "../lib/api/queries";
import { LoadingState } from "../components/shared/LoadingState";
import { ErrorState } from "../components/shared/ErrorState";
import { EmptyState } from "../components/shared/EmptyState";
import { Panel } from "../components/shared/Panel";
import { ReturnHeader } from "../components/layout/ReturnHeader";
import { SourceEvidencePanel } from "../components/evidence/SourceEvidencePanel";
import { ConflictCard } from "../components/conflicts/ConflictCard";
import { SupplierTimeline } from "../components/timeline/SupplierTimeline";
import { RoutingAllocation } from "../components/routing/RoutingAllocation";
import { InvariantPanel } from "../components/routing/InvariantPanel";
import { CommercialOutcome } from "../components/decision/CommercialOutcome";
import { DecisionMatrix } from "../components/decision/DecisionMatrix";
import { RuleCard } from "../components/decision/RuleCard";
import { AuditExplorer } from "../components/audit/AuditExplorer";
import { RawJsonViewer } from "../components/audit/RawJsonViewer";

const TABS = ["Overview", "Evidence", "Decision", "Audit"] as const;
type Tab = (typeof TABS)[number];

export function ReturnWorkspace() {
  const { id } = useParams<{ id: string }>();
  const { data: run, isLoading, isError, error, refetch } = useReconciliation(id);
  const [tab, setTab] = useState<Tab>("Overview");
  const [activeItemId, setActiveItemId] = useState<string | null>(null);

  if (isLoading) return <LoadingState label="Loading saved reconciliation…" />;
  if (isError) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!run) return null;

  const items = run.audit_report.items;
  const item = items.find((candidate) => candidate.item_id === activeItemId) ?? items[0];
  if (!item) {
    return (
      <EmptyState
        icon={CheckCircle2}
        title="No items in this reconciliation"
        description="The audit report for this return contains no warehouse items."
      />
    );
  }

  const rawSupplierEvents = Array.isArray(
    (run.input_payload as { supplier_events?: unknown })?.supplier_events,
  )
    ? ((run.input_payload as { supplier_events: Array<{ event_id?: string; received_at?: string }> })
        .supplier_events)
    : [];

  return (
    <div className="flex flex-col gap-4">
      <ReturnHeader run={run} />

      {items.length > 1 && (
        <div className="flex gap-1.5">
          {items.map((candidate) => (
            <button
              key={candidate.item_id}
              type="button"
              onClick={() => setActiveItemId(candidate.item_id)}
              aria-pressed={candidate.item_id === item.item_id}
              className={`rounded px-3 py-1.5 text-sm font-medium ${
                candidate.item_id === item.item_id
                  ? "bg-accent text-text-inverse"
                  : "bg-surface-sunken text-text-secondary hover:text-text-primary"
              }`}
            >
              {candidate.item_id}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-1 border-b border-border">
        {TABS.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setTab(option)}
            aria-current={tab === option ? "page" : undefined}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              tab === option
                ? "border-accent text-accent"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            {option}
          </button>
        ))}
      </div>

      {tab === "Overview" && (
        <div className="flex flex-col gap-4">
          <Panel title="Conflicts" description={`${item.conflicts.length} detected for this item`}>
            {item.conflicts.length === 0 ? (
              <EmptyState
                icon={CheckCircle2}
                title="No conflicts detected"
                description="The available source evidence does not contain a material disagreement."
              />
            ) : (
              <div className="flex flex-col gap-3">
                {item.conflicts.map((conflict) => (
                  <ConflictCard
                    key={conflict.conflict_id}
                    conflict={conflict}
                    evidence={item.evidence}
                    resolvedFields={item.resolved_fields}
                  />
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Physical routing">
            <RoutingAllocation
              allocations={item.allocations}
              totalReceived={item.allocations.reduce((sum, a) => sum + a.quantity, 0)}
            />
          </Panel>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Panel title="Commercial outcome">
              <CommercialOutcome commercial={item.commercial_decision} />
            </Panel>
            <Panel title="Inventory accounting">
              <InvariantPanel
                invariants={item.invariants}
                allocations={item.allocations}
                quantityReceived={item.allocations.reduce((sum, a) => sum + a.quantity, 0)}
              />
            </Panel>
          </div>
        </div>
      )}

      {tab === "Evidence" && (
        <div className="flex flex-col gap-4">
          <Panel title="Source evidence">
            <SourceEvidencePanel evidence={item.evidence} />
          </Panel>
          <Panel title="Supplier timeline">
            <SupplierTimeline evidence={item.evidence} rawSupplierEvents={rawSupplierEvents} />
          </Panel>
        </div>
      )}

      {tab === "Decision" && (
        <div className="flex flex-col gap-4">
          <Panel title="Decision matrix" description="What each source claimed, and what won">
            <DecisionMatrix resolvedFields={item.resolved_fields} evidence={item.evidence} />
          </Panel>
          <Panel title="Rules applied" description="Only rules that actually fired on this item">
            {item.rules_applied.length === 0 ? (
              <p className="text-sm text-text-muted">No rules were needed for this item.</p>
            ) : (
              <div className="flex flex-col gap-1.5">
                {item.rules_applied.map((ruleId) => (
                  <RuleCard key={ruleId} ruleId={ruleId} />
                ))}
              </div>
            )}
          </Panel>
        </div>
      )}

      {tab === "Audit" && (
        <div className="flex flex-col gap-4">
          <Panel title="Evidence audit" description="Every claim considered, filterable by status">
            <AuditExplorer evidence={item.evidence} />
          </Panel>
          <RawJsonViewer title="Raw audit report" data={run.audit_report} />
          <RawJsonViewer title="Raw input payload" data={run.input_payload} />
        </div>
      )}
    </div>
  );
}
