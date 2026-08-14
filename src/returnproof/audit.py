"""Audit record shapes. Pure data, no decision logic lives here.

Human-readable and machine-readable output are both rendered from the same
ItemAuditRecord, cli.py never maintains a second copy of the decision.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from returnproof.allocation import Allocation, InvariantCheck, RejectedAlternative
from returnproof.conflicts import Conflict
from returnproof.enums import Condition
from returnproof.evidence import EvidenceClaim
from returnproof.policies import ResolvedField


class ResolvedSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition: Condition
    batch_code: str | None
    best_before_bucket: str | None


class CommercialDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credit_eligible: bool | None
    credit_quantity: int | None
    reason: str
    rules_applied: list[str]


class AllocationExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int
    route: str
    reason: str
    best_before_bucket: str | None
    rejected_alternatives: list[RejectedAlternative]


class ItemAuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    sku: str
    resolved: ResolvedSummary
    conflicts: list[Conflict]
    evidence: list[EvidenceClaim]
    resolved_fields: list[ResolvedField]
    rules_applied: list[str]
    allocations: list[Allocation]
    commercial_decision: CommercialDecision
    invariants: list[InvariantCheck]
    reasoning: list[str]
    rejected_alternatives: list[AllocationExplanation]


class ReturnSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_count: int
    conflict_count: int
    invariants_passed: bool


class ReturnAuditReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    return_id: str
    items: list[ItemAuditRecord]
    summary: ReturnSummary
