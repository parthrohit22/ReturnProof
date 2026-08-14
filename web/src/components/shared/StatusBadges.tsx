import { Badge } from "./Badge";
import {
  evidenceStatusStyles,
  provenanceStyles,
  routeStyles,
  summaryStatusStyles,
} from "./statusStyles";
import type { EvidenceStatus, Provenance, Route } from "../../types/audit";
import type { SummaryStatus } from "../../types/api";

export function RouteBadge({ route, size }: { route: Route; size?: "sm" | "md" }) {
  return <Badge status={routeStyles[route]} size={size} />;
}

export function EvidenceStatusBadge({
  status,
  size,
}: {
  status: EvidenceStatus;
  size?: "sm" | "md";
}) {
  return <Badge status={evidenceStatusStyles[status]} size={size} />;
}

export function ProvenanceBadge({
  provenance,
  size,
}: {
  provenance: Provenance;
  size?: "sm" | "md";
}) {
  return <Badge status={provenanceStyles[provenance]} size={size} />;
}

export function SummaryStatusBadge({
  status,
  size,
}: {
  status: SummaryStatus;
  size?: "sm" | "md";
}) {
  return <Badge status={summaryStatusStyles[status]} size={size} />;
}
