import { SummaryStatusBadge } from "../shared/StatusBadges";
import { formatDateTime } from "../../lib/format";
import type { RunDetail } from "../../types/api";

interface ReturnHeaderProps {
  run: RunDetail;
}

export function ReturnHeader({ run }: ReturnHeaderProps) {
  const quarantined = run.route_totals.QUARANTINE ?? 0;

  return (
    <div className="rounded-md border border-border bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs text-text-muted">Return</p>
          <h1 className="text-xl font-semibold text-text-primary">{run.return_id}</h1>
          <p className="mt-1 text-xs text-text-muted">
            Processed {formatDateTime(run.created_at)}
            {run.scenario_name && ` · ${run.scenario_name}`}
          </p>
        </div>
        <SummaryStatusBadge status={run.summary_status} />
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-4 border-t border-border pt-4 sm:grid-cols-4">
        <div>
          <dt className="text-xs text-text-muted">Items</dt>
          <dd className="font-mono-tabular text-lg font-semibold text-text-primary">
            {run.item_count}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-text-muted">Units received</dt>
          <dd className="font-mono-tabular text-lg font-semibold text-text-primary">
            {run.quantity_received}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-text-muted">Conflicts</dt>
          <dd className="font-mono-tabular text-lg font-semibold text-text-primary">
            {run.conflict_count}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-text-muted">Quarantined</dt>
          <dd
            className={`font-mono-tabular text-lg font-semibold ${quarantined > 0 ? "text-warning" : "text-text-primary"}`}
          >
            {quarantined}
          </dd>
        </div>
      </dl>
    </div>
  );
}
