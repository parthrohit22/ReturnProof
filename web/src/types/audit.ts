/**
 * Mirrors returnproof's audit output shapes exactly (audit.py, allocation.py,
 * conflicts.py, evidence.py, policies.py, enums.py). These types describe
 * what the engine already decided, nothing here is computed in the browser.
 */

export type Condition = "GOOD" | "DAMAGED_SALVAGEABLE" | "DAMAGED_UNSAFE" | "UNKNOWN";

export type Route = "RESTOCK" | "SCRAP" | "QUARANTINE";

export type SupplierInstruction = "RESTOCK" | "SCRAP" | "QUARANTINE";

export type BatchValidity = "VALID" | "SUSPECT" | "CORRUPTED" | "MISSING";

export type EvidenceSource = "WAREHOUSE" | "SUPPLIER" | "DERIVED";

export type EvidenceStatus =
  | "ACCEPTED"
  | "CORROBORATED"
  | "SUSPECT"
  | "CORRUPTED"
  | "SUPERSEDED"
  | "UNRESOLVED"
  | "REJECTED";

export type Provenance = "DIRECT" | "CORROBORATED" | "INFERRED" | "UNRESOLVED";

export type EvidenceField =
  | "condition"
  | "damage_type"
  | "batch_code"
  | "best_before"
  | "quantity_received"
  | "acknowledged_quantity"
  | "credit_eligible"
  | "credit_quantity"
  | "instruction";

export type ConflictType =
  | "CONDITION_DISAGREEMENT"
  | "BATCH_MISMATCH"
  | "QUANTITY_OR_ELIGIBILITY_DISPUTE"
  | "SUPPLIER_STATE_AMBIGUOUS";

export interface EvidenceClaim {
  claim_id: string;
  item_id: string;
  field: EvidenceField;
  value: unknown;
  source: EvidenceSource;
  status: EvidenceStatus;
  authority: Provenance;
  reason: string;
  source_reference: string;
  timestamp: string | null;
}

export interface Conflict {
  conflict_id: string;
  type: ConflictType;
  item_id: string;
  description: string;
  claim_ids: string[];
}

export interface ResolvedField {
  field: EvidenceField;
  value: unknown;
  winning_source: EvidenceSource | null;
  provenance: Provenance;
  reason: string;
  rules_applied: string[];
  accepted_claim_ids: string[];
  rejected_claim_ids: string[];
}

export interface RejectedAlternative {
  route: Route;
  reason: string;
}

export interface Allocation {
  quantity: number;
  route: Route;
  reason: string;
  best_before_bucket: string | null;
  context: string;
}

export interface InvariantCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export interface AllocationExplanation {
  quantity: number;
  route: string;
  reason: string;
  best_before_bucket: string | null;
  rejected_alternatives: RejectedAlternative[];
}

export interface ResolvedSummary {
  condition: Condition;
  batch_code: string | null;
  best_before_bucket: string | null;
}

export interface CommercialDecision {
  credit_eligible: boolean | null;
  credit_quantity: number | null;
  reason: string;
  rules_applied: string[];
}

export interface ItemAuditRecord {
  item_id: string;
  sku: string;
  resolved: ResolvedSummary;
  conflicts: Conflict[];
  evidence: EvidenceClaim[];
  resolved_fields: ResolvedField[];
  rules_applied: string[];
  allocations: Allocation[];
  commercial_decision: CommercialDecision;
  invariants: InvariantCheck[];
  reasoning: string[];
  rejected_alternatives: AllocationExplanation[];
}

export interface ReturnSummary {
  item_count: number;
  conflict_count: number;
  invariants_passed: boolean;
}

export interface ReturnAuditReport {
  return_id: string;
  items: ItemAuditRecord[];
  summary: ReturnSummary;
}
