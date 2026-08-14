import {
  AlertCircle,
  AlertTriangle,
  Ban,
  CheckCircle2,
  Clock,
  Eye,
  HelpCircle,
  ShieldCheck,
  Sparkles,
  XCircle,
  type LucideIcon,
} from "lucide-react";

import type { EvidenceStatus, Provenance, Route } from "../../types/audit";
import type { SummaryStatus } from "../../types/api";

export type Tone = "success" | "danger" | "warning" | "information" | "neutral";

export interface StatusStyle {
  label: string;
  tone: Tone;
  icon: LucideIcon;
}

export const toneClasses: Record<Tone, { surface: string; border: string; text: string }> = {
  success: {
    surface: "bg-success-surface",
    border: "border-success-border",
    text: "text-success",
  },
  danger: {
    surface: "bg-danger-surface",
    border: "border-danger-border",
    text: "text-danger",
  },
  warning: {
    surface: "bg-warning-surface",
    border: "border-warning-border",
    text: "text-warning",
  },
  information: {
    surface: "bg-information-surface",
    border: "border-information-border",
    text: "text-information",
  },
  neutral: {
    surface: "bg-neutral-surface",
    border: "border-neutral-border",
    text: "text-neutral",
  },
};

export const routeStyles: Record<Route, StatusStyle> = {
  RESTOCK: { label: "Restock", tone: "success", icon: CheckCircle2 },
  SCRAP: { label: "Scrap", tone: "danger", icon: XCircle },
  QUARANTINE: { label: "Quarantine", tone: "warning", icon: AlertTriangle },
};

export const evidenceStatusStyles: Record<EvidenceStatus, StatusStyle> = {
  ACCEPTED: { label: "Accepted", tone: "success", icon: CheckCircle2 },
  CORROBORATED: { label: "Corroborated", tone: "success", icon: ShieldCheck },
  SUSPECT: { label: "Suspect", tone: "warning", icon: AlertCircle },
  CORRUPTED: { label: "Corrupted", tone: "danger", icon: XCircle },
  SUPERSEDED: { label: "Superseded", tone: "neutral", icon: Clock },
  REJECTED: { label: "Rejected", tone: "danger", icon: Ban },
  UNRESOLVED: { label: "Unresolved", tone: "warning", icon: HelpCircle },
};

export const provenanceStyles: Record<Provenance, StatusStyle> = {
  DIRECT: { label: "Direct", tone: "information", icon: Eye },
  CORROBORATED: { label: "Corroborated", tone: "success", icon: ShieldCheck },
  INFERRED: { label: "Inferred", tone: "neutral", icon: Sparkles },
  UNRESOLVED: { label: "Unresolved", tone: "warning", icon: HelpCircle },
};

export const summaryStatusStyles: Record<SummaryStatus, StatusStyle> = {
  RESOLVED: { label: "Resolved", tone: "success", icon: CheckCircle2 },
  REQUIRES_REVIEW: { label: "Requires review", tone: "warning", icon: AlertTriangle },
};
