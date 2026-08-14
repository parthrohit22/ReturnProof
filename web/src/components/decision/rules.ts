/**
 * Rule text mirrored from src/returnproof/policies.py's RULES dict. Static
 * reference documentation, not a decision, the actual rule IDs that fire
 * on an item always come from the engine's own audit output.
 */
export const RULES: Record<string, { name: string; description: string }> = {
  R001: {
    name: "Physical Condition Authority",
    description:
      "Warehouse direct observation has authority over supplier routing preference for physical condition.",
  },
  R002: {
    name: "Invalid Evidence Loses Authority",
    description: "A corrupted or suspect claim can't win a decision just because of who sent it.",
  },
  R003: {
    name: "Batch Corroboration",
    description:
      "A supplier batch can resolve a bad warehouse batch, but only once checked against independent product metadata.",
  },
  R004: {
    name: "Supplier Temporal Ordering",
    description:
      "Supplier state is resolved by business event time or version, never by message arrival order.",
  },
  R005: {
    name: "Physical Safety Override",
    description:
      "Confirmed unsafe physical damage blocks a restock, no matter what the supplier instructed.",
  },
  R006: {
    name: "Quantity Conservation",
    description:
      "Scrap plus restock plus quarantine has to equal exactly what the warehouse received.",
  },
  R007: {
    name: "Uncertainty Escalation",
    description:
      "Unresolved identity, safety, or disposition routes the affected stock to quarantine instead of guessing.",
  },
  R008: {
    name: "Commercial Operational Separation",
    description:
      "Credit eligibility never decides physical routing, and physical routing never decides credit eligibility.",
  },
};
