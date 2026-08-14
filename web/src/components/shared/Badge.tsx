import type { StatusStyle } from "./statusStyles";
import { toneClasses } from "./statusStyles";

interface BadgeProps {
  status: StatusStyle;
  size?: "sm" | "md";
}

/**
 * Every status in ReturnProof renders through this one component. Icon +
 * text carry the meaning, colour reinforces it, never the only signal
 * (accessibility requirement, and colour-only status is genuinely
 * ambiguous for a dense audit table anyway).
 */
export function Badge({ status, size = "md" }: BadgeProps) {
  const classes = toneClasses[status.tone];
  const Icon = status.icon;
  const padding = size === "sm" ? "px-1.5 py-0.5 text-xs gap-1" : "px-2 py-1 text-sm gap-1.5";
  const iconSize = size === "sm" ? 12 : 14;

  return (
    <span
      className={`inline-flex items-center rounded border font-medium ${padding} ${classes.surface} ${classes.border} ${classes.text}`}
    >
      <Icon size={iconSize} aria-hidden="true" />
      {status.label}
    </span>
  );
}
