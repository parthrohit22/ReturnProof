"""Enumerations shared across the reconciliation engine.

Kept in one file because they are the vocabulary every other module reads
against. Changing one of these is a policy change, not a refactor.
"""

from __future__ import annotations

from enum import StrEnum


class Condition(StrEnum):
    """Physical condition of the returned goods, as assessed by the warehouse."""

    GOOD = "GOOD"
    DAMAGED_SALVAGEABLE = "DAMAGED_SALVAGEABLE"
    DAMAGED_UNSAFE = "DAMAGED_UNSAFE"
    UNKNOWN = "UNKNOWN"


class Route(StrEnum):
    """Physical destination for a quantity of stock. Never conflated with credit."""

    RESTOCK = "RESTOCK"
    SCRAP = "SCRAP"
    QUARANTINE = "QUARANTINE"


class SupplierInstruction(StrEnum):
    """What the supplier's credit-note event asked for. A preference, not an order."""

    RESTOCK = "RESTOCK"
    SCRAP = "SCRAP"
    QUARANTINE = "QUARANTINE"


class BatchValidity(StrEnum):
    """Classification of a raw batch code string, independent of its source."""

    VALID = "VALID"
    SUSPECT = "SUSPECT"
    CORRUPTED = "CORRUPTED"
    MISSING = "MISSING"


class EvidenceSource(StrEnum):
    WAREHOUSE = "WAREHOUSE"
    SUPPLIER = "SUPPLIER"
    DERIVED = "DERIVED"


class EvidenceStatus(StrEnum):
    """Lifecycle state of a single evidence claim. Not a global trust score."""

    ACCEPTED = "ACCEPTED"
    CORROBORATED = "CORROBORATED"
    SUSPECT = "SUSPECT"
    CORRUPTED = "CORRUPTED"
    SUPERSEDED = "SUPERSEDED"
    UNRESOLVED = "UNRESOLVED"
    REJECTED = "REJECTED"


class Provenance(StrEnum):
    """How strongly a resolved field value is grounded in evidence. Not a percentage."""

    DIRECT = "DIRECT"
    CORROBORATED = "CORROBORATED"
    INFERRED = "INFERRED"
    UNRESOLVED = "UNRESOLVED"


class EvidenceField(StrEnum):
    """Material fields the engine resolves per item. Each has its own authority policy."""

    CONDITION = "condition"
    DAMAGE_TYPE = "damage_type"
    BATCH_CODE = "batch_code"
    BEST_BEFORE = "best_before"
    QUANTITY_RECEIVED = "quantity_received"
    ACKNOWLEDGED_QUANTITY = "acknowledged_quantity"
    CREDIT_ELIGIBLE = "credit_eligible"
    CREDIT_QUANTITY = "credit_quantity"
    INSTRUCTION = "instruction"


class ConflictType(StrEnum):
    CONDITION_DISAGREEMENT = "CONDITION_DISAGREEMENT"
    BATCH_MISMATCH = "BATCH_MISMATCH"
    QUANTITY_OR_ELIGIBILITY_DISPUTE = "QUANTITY_OR_ELIGIBILITY_DISPUTE"
    SUPPLIER_STATE_AMBIGUOUS = "SUPPLIER_STATE_AMBIGUOUS"
