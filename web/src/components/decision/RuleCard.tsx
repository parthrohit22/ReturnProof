import { useState } from "react";
import { ChevronDown, ChevronRight, ScrollText } from "lucide-react";

import { RULES } from "./rules";

interface RuleCardProps {
  ruleId: string;
}

export function RuleCard({ ruleId }: RuleCardProps) {
  const [open, setOpen] = useState(false);
  const rule = RULES[ruleId];

  return (
    <button
      type="button"
      onClick={() => setOpen((value) => !value)}
      aria-expanded={open}
      className="w-full rounded-md border border-border bg-surface px-3 py-2 text-left hover:bg-surface-sunken"
    >
      <div className="flex items-center gap-2">
        {open ? (
          <ChevronDown size={14} className="text-text-muted" aria-hidden="true" />
        ) : (
          <ChevronRight size={14} className="text-text-muted" aria-hidden="true" />
        )}
        <ScrollText size={14} className="text-text-muted" aria-hidden="true" />
        <span className="font-mono-tabular text-xs font-semibold text-accent">{ruleId}</span>
        <span className="text-sm font-medium text-text-primary">
          {rule?.name ?? "Unknown rule"}
        </span>
      </div>
      {open && rule && (
        <p className="mt-1.5 pl-6 text-xs text-text-secondary">{rule.description}</p>
      )}
    </button>
  );
}
