import { RouteBadge } from "../shared/StatusBadges";
import { toneClasses, routeStyles } from "../shared/statusStyles";
import type { Allocation } from "../../types/audit";

interface RoutingAllocationProps {
  allocations: Allocation[];
  totalReceived: number;
}

const BAR_TONE_BG: Record<Allocation["route"], string> = {
  RESTOCK: "bg-success",
  SCRAP: "bg-danger",
  QUARANTINE: "bg-warning",
};

export function RoutingAllocation({ allocations, totalReceived }: RoutingAllocationProps) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <div
          className="flex h-3 w-full overflow-hidden rounded-full bg-surface-sunken"
          role="img"
          aria-label={allocations
            .map((allocation) => `${allocation.quantity} ${routeStyles[allocation.route].label}`)
            .join(", ")}
        >
          {allocations.map((allocation, index) => (
            <div
              key={index}
              className={BAR_TONE_BG[allocation.route]}
              style={{ width: `${(allocation.quantity / totalReceived) * 100}%` }}
            />
          ))}
        </div>
        <p className="mt-1 text-xs text-text-muted">{totalReceived} units received</p>
      </div>

      <ul className="flex flex-col gap-2">
        {allocations.map((allocation, index) => {
          const tone = toneClasses[routeStyles[allocation.route].tone];
          return (
            <li
              key={index}
              className={`rounded-md border px-3 py-2.5 ${tone.border} ${tone.surface}`}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="font-mono-tabular text-lg font-semibold text-text-primary">
                    {allocation.quantity}
                  </span>
                  <RouteBadge route={allocation.route} />
                  {allocation.best_before_bucket && (
                    <span className="rounded bg-surface px-1.5 py-0.5 font-mono-tabular text-xs text-text-secondary">
                      {allocation.best_before_bucket}
                    </span>
                  )}
                </div>
              </div>
              <p className="mt-1.5 text-xs text-text-secondary">{allocation.reason}</p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
