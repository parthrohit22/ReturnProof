import { Banknote } from "lucide-react";

import { formatValue } from "../../lib/format";
import type { CommercialDecision } from "../../types/audit";

interface CommercialOutcomeProps {
  commercial: CommercialDecision;
}

export function CommercialOutcome({ commercial }: CommercialOutcomeProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-text-muted">Credit eligible</p>
          <p className="mt-0.5 text-lg font-semibold text-text-primary">
            {formatValue(commercial.credit_eligible)}
          </p>
        </div>
        <div>
          <p className="text-xs text-text-muted">Credit quantity</p>
          <p className="mt-0.5 font-mono-tabular text-lg font-semibold text-text-primary">
            {formatValue(commercial.credit_quantity)}
          </p>
        </div>
      </div>
      <p className="flex items-start gap-1.5 rounded-md bg-surface-sunken px-3 py-2 text-xs text-text-secondary">
        <Banknote size={14} className="mt-0.5 shrink-0 text-text-muted" aria-hidden="true" />
        Commercial credit is resolved independently of physical routing. {commercial.reason}.
      </p>
    </div>
  );
}
