import { Link } from "react-router-dom";
import { Inbox, PlusCircle } from "lucide-react";

import { useReconciliations } from "../lib/api/queries";
import { LoadingState } from "../components/shared/LoadingState";
import { ErrorState } from "../components/shared/ErrorState";
import { EmptyState } from "../components/shared/EmptyState";
import { RouteBadge, SummaryStatusBadge } from "../components/shared/StatusBadges";
import type { Route } from "../types/audit";

const ROUTE_ORDER: Route[] = ["SCRAP", "QUARANTINE", "RESTOCK"];

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function ReturnsQueue() {
  const { data: runs, isLoading, isError, error, refetch } = useReconciliations();

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Returns</h1>
          <p className="text-sm text-text-secondary">
            Every reconciliation processed by ReturnProof, most recent first.
          </p>
        </div>
        <Link
          to="/returns/new"
          className="flex items-center gap-1.5 rounded bg-accent px-3 py-1.5 text-sm font-medium text-text-inverse hover:opacity-90"
        >
          <PlusCircle size={15} aria-hidden="true" />
          New Reconciliation
        </Link>
      </div>

      {isLoading && <LoadingState label="Loading reconciliation history…" />}

      {isError && <ErrorState error={error} onRetry={() => refetch()} />}

      {runs && runs.length === 0 && (
        <EmptyState
          icon={Inbox}
          title="No reconciliations yet"
          description="Run an example or submit return data to create the first reconciliation."
          action={
            <Link
              to="/returns/new"
              className="inline-flex items-center gap-1.5 rounded border border-border-strong bg-surface px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-sunken"
            >
              <PlusCircle size={14} aria-hidden="true" />
              New Reconciliation
            </Link>
          }
        />
      )}

      {runs && runs.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-border bg-surface">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-border bg-surface-sunken text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">Return</th>
                <th className="px-4 py-2 font-medium">Processed</th>
                <th className="px-4 py-2 font-medium">Items</th>
                <th className="px-4 py-2 font-medium">Conflicts</th>
                <th className="px-4 py-2 font-medium">Received</th>
                <th className="px-4 py-2 font-medium">Routing</th>
                <th className="px-4 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr
                  key={run.id}
                  className="border-b border-border last:border-b-0 hover:bg-surface-sunken"
                >
                  <td className="px-4 py-2.5">
                    <Link to={`/returns/${run.id}`} className="font-medium text-accent hover:underline">
                      {run.return_id}
                    </Link>
                    {run.scenario_name && (
                      <p className="text-xs text-text-muted">{run.scenario_name}</p>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-text-secondary">
                    {formatTimestamp(run.created_at)}
                  </td>
                  <td className="px-4 py-2.5 font-mono-tabular text-text-secondary">
                    {run.item_count}
                  </td>
                  <td className="px-4 py-2.5 font-mono-tabular text-text-secondary">
                    {run.conflict_count}
                  </td>
                  <td className="px-4 py-2.5 font-mono-tabular text-text-secondary">
                    {run.quantity_received}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {ROUTE_ORDER.filter((route) => run.route_totals[route]).map((route) => (
                        <span key={route} className="flex items-center gap-1">
                          <RouteBadge route={route} size="sm" />
                          <span className="text-xs text-text-muted">{run.route_totals[route]}</span>
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <SummaryStatusBadge status={run.summary_status} size="sm" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
