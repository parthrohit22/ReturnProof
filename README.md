# ReturnProof

Evidence-driven reconciliation for partial stock returns, built for the LEC AI
AI Engineering Intern build assessment. The brief and the design proposal
this was built from are kept in `ASSESSMENT.md` and `ROADMAP.md` in this
repository, alongside `AGENTS.md` and `EVALUATION.md` for anyone who wants
the full working context behind the decisions below.

## Overview

A stock return comes with two reports that were never meant to agree. The
warehouse physically inspects the goods and writes down what it sees. The
supplier issues a credit note based on what it expects to be true about the
batch, the eligibility, and the value. Neither report is reliable on its
own. Warehouse scans get corrupted under bad lighting. Supplier systems send
corrections that arrive out of order, or don't want to pay out more credit
than they have to.

ReturnProof takes both reports for a return shipment and produces, for every
item, a routing decision (restock, scrap, or quarantine), a best-before
bucket, a commercial credit decision, and a full audit trail explaining
which piece of evidence won each individual decision and why. It runs
entirely offline, with no LLM anywhere in the decision path.

## Key Idea

The obvious approaches both fail. Trusting the warehouse always means
restocking stock with a corrupted batch code because the warehouse "saw
it first." Trusting the supplier always means accepting a RESTOCK
instruction on cartons the warehouse has just photographed as crushed and
leaking. Trusting whichever source "sounds more confident" isn't a
decision rule at all.

ReturnProof resolves conflicts at the level of the individual claim, not
the source. The warehouse and the supplier are never assigned a trust
score. Instead, each field on each item (condition, batch code,
best-before, quantity, credit eligibility) has its own authority policy,
and every claim is validated, corroborated, or rejected on its own merits.
The same item can have the warehouse win the condition decision while the
supplier wins the batch decision, because that's genuinely how much each
source actually knows about that specific field.

## Architecture

Input flows through one pipeline, described in `reconciler.py`, and every
stage's output is retained in the audit record rather than discarded once
it's been used.

- `models.py` and `enums.py` hold the input schema and the shared
  vocabulary (conditions, routes, evidence statuses).
- `validation.py` classifies warehouse batch codes as valid, suspect,
  corrupted, or missing, without ever silently rewriting one.
- `evidence.py` turns warehouse and supplier fields into individually
  tagged claims, each carrying a source, a status, and a reason.
- `temporal.py` resolves which supplier event is current when several
  exist for the same item, using business event time, never network
  arrival order.
- `conflicts.py` detects disagreement between the two sources without
  resolving it.
- `policies.py` is where every decision rule lives. This is the one file
  a reviewer should read to understand how ReturnProof decides anything.
- `allocation.py` splits an item's received quantity across routes and
  checks that nothing was lost or invented along the way.
- `audit.py` and `reconciler.py` assemble the per-item and per-return
  audit record that both the human-readable and JSON output are rendered
  from.
- `cli.py` is a thin Typer/Rich presentation layer over that one
  pipeline. It never makes a decision of its own.

## Decision Rules

Every rule below is implemented in `policies.py`, `conflicts.py`, or
`allocation.py`, and every rule ID that fires on an item shows up in that
item's audit output.

| Rule | Name | What it does |
| --- | --- | --- |
| R001 | PHYSICAL_CONDITION_AUTHORITY | Warehouse direct observation has authority over supplier routing preference for physical condition. |
| R002 | INVALID_EVIDENCE_LOSES_AUTHORITY | A corrupted or suspect claim can't win a decision just because of who sent it. |
| R003 | BATCH_CORROBORATION | A supplier batch can resolve a bad warehouse batch, but only once it's checked against independent product metadata. |
| R004 | SUPPLIER_TEMPORAL_ORDERING | Supplier state is resolved by business event time or version, never by message arrival order. |
| R005 | PHYSICAL_SAFETY_OVERRIDE | Confirmed unsafe physical damage blocks a restock, no matter what the supplier instructed. |
| R006 | QUANTITY_CONSERVATION | Scrap plus restock plus quarantine has to equal exactly what the warehouse received. |
| R007 | UNCERTAINTY_ESCALATION | Unresolved identity, safety, or disposition routes the affected stock to quarantine instead of guessing. |
| R008 | COMMERCIAL_OPERATIONAL_SEPARATION | Credit eligibility never decides physical routing, and physical routing never decides credit eligibility. |

Field authority itself isn't one of these eight rules, it's the table at
the top of `policies.py` that R001 to R008 are built on. Condition, damage
type, and physical quantity default to the warehouse. Acknowledged
quantity, credit eligibility, and credit quantity default to the supplier.
Batch code, best-before, and the physical route have no default owner at
all, they're resolved from evidence each time.

## Conflict Types

`conflicts.py` detects the three required kinds of disagreement, plus one
more an adversarial review surfaced as worth naming in its own right. Each
shows up by name in an item's `conflicts` list with the specific claims
involved.

**CONDITION_DISAGREEMENT.** Either direction. The warehouse reports
anything other than GOOD (damaged, or condition unknown) while the current
supplier event instructs RESTOCK, or the warehouse reports GOOD while the
supplier instructs SCRAP. Both are flagged, not just the first, treating
only one direction as a conflict would itself be a hidden bias toward
whichever source that choice favored. Demonstrated in
`examples/simple_condition_conflict.json`.

**BATCH_MISMATCH.** The warehouse batch code is unusable, or the warehouse
and supplier batch codes disagree once both are normalized. Demonstrated
in `examples/batch_corruption.json`.

**QUANTITY_OR_ELIGIBILITY_DISPUTE.** Really three distinct disputes kept
deliberately apart, not folded into one number. Received quantity against
acknowledged quantity is a receiving-count disagreement. Damaged quantity
against credit quantity is a commercial-scope disagreement, they describe
different things and are never assumed to be the same number under two
names. And a supplier event can be internally inconsistent (crediting more
than it acknowledges receiving) independent of anything the warehouse
said, that's flagged too, it just never affects physical routing.
Demonstrated in `examples/quantity_dispute.json`.

**SUPPLIER_STATE_AMBIGUOUS.** Two or more supplier events tie on ordering
(same version, or same event_timestamp with no version) with genuinely
conflicting content. See Failure Modes below, this is what happens instead
of picking a winner by array position or event id.

## Failure Modes

**Warehouse batch corruption.** `validation.py` classifies a batch code as
VALID, SUSPECT, CORRUPTED, or MISSING against a default two-letters-plus-
four-to-six-digits format (a demo convention, not a real supplier's
format, see Limitations). A SKU can override the default entirely with
its own `batch_pattern` regex in product metadata, `2026-A-771` is
CORRUPTED under the default grammar but VALID under a SKU-specific
pattern that expects it. Under the default grammar, non-alphanumeric noise
like `BA?9O2` or `B72$9#` is CORRUPTED outright, nothing about it can be
safely repaired. A code like `BA729I` is SUSPECT, the `I` sits where a
digit belongs and could be an OCR misread of `1`. In that case a
normalized candidate (`BA7291`) is computed and recorded, but it stays a
candidate. It only becomes the resolved value if it's independently
confirmed, either by an exact supplier match plus product metadata, or by
matching known batch data on its own. The raw value the warehouse actually
scanned is preserved untouched either way, and if the warehouse and
supplier batches are both individually well-formed but disagree, neither
wins by default, resolution falls to whichever one (if either) matches
known batch metadata, otherwise the field stays UNRESOLVED.

**Out-of-order supplier events.** `temporal.py` treats `event_timestamp`
as the business state and `received_at` as pure audit metadata that never
drives a decision. If every event for an item carries a `version`, version
order wins. Otherwise event time wins. An event that arrives at the
warehouse system after a newer one doesn't get to overwrite it, and the
ordering is computed by sorting on that key, not by trusting whatever
order the events happened to show up in an array. Two events can also
legitimately tie on that key: if they agree on every decision-relevant
field it's treated as one event delivered twice (deduplicated, not a
conflict), if they disagree, supplier state is reported unresolved
(SUPPLIER_STATE_AMBIGUOUS) rather than picked by whichever `event_id`
happens to sort last. A duplicate `event_id` carrying different content on
each copy is rejected as malformed input outright, it's ambiguous which
copy is real. Demonstrated in `examples/out_of_order_supplier.json`, and
checked directly by the determinism and tie-handling tests in
`tests/test_temporal_ordering.py`, `tests/test_adversarial.py`, and
`tests/test_compound_failure.py`.

## Compound Failure

`examples/compound_failure.json` is the one scenario that has to work for
this assessment to mean anything, both failure modes hit the same item at
once.

The warehouse scans batch `BA?9O2` for a milk return, unreadable noise,
classified CORRUPTED. Two supplier events exist for the same item. One
instructs SCRAP with an event time of 13:55 but arrives at 14:05. The
other instructs RESTOCK with an event time of 14:02 but arrives at 13:58,
before the SCRAP message that logically came first. Ordering by arrival
would wrongly land on the stale SCRAP event. ReturnProof orders by event
time instead, accepts the RESTOCK event as current, and marks the SCRAP
event SUPERSEDED with the reason recorded in its evidence claim.

Independently of that, the supplier's batch code `BA1902` is checked
against the return's product metadata for SKU `MILK-01`, finds a match,
and is accepted as CORROBORATED (R002, R003). Best-before resolves to
`2026-10` from that same corroborated metadata.

Independently again, the warehouse's own physical inspection still stands.
6 of the 24 units are marked DAMAGED_UNSAFE. Those 6 route to SCRAP under
R005 regardless of what either supplier event instructed, because
confirmed unsafe damage isn't something a routing preference gets to
override. The remaining 18 route to RESTOCK under the resolved batch and
best-before bucket. R006 confirms 6 plus 18 equals the 24 units the
warehouse actually received.

The supplier's credit_quantity on the accepted event is 4, not 6 and not
18. That number is kept as its own field, resolved under R008, and it's
deliberately different from both physical quantities in the fixture so the
separation between physical routing and commercial credit is visible in
the output rather than asserted in prose.

None of this needs the two failures to be handled in sequence. Batch
resolution, temporal resolution, condition routing, and credit resolution
each run against their own evidence and would produce the same result if
the other failure weren't present at all.

## Compound Failure, Unresolved

`examples/compound_unresolved.json` is the adversarial counterpart to the
scenario above, same two mandatory failures (corrupted warehouse batch,
out-of-order supplier events), but with the corroborating evidence removed
on purpose. The supplier's batch code doesn't appear anywhere in the
return's product metadata, so there's nothing to corroborate it against.

The result: batch identity stays UNRESOLVED, best-before stays UNRESOLVED,
and all 15 units of physically intact stock go to QUARANTINE rather than
being restocked on an unconfirmed guess. The out-of-order events still
resolve correctly underneath that (the stale SCRAP event is still
correctly marked SUPERSEDED), it just doesn't matter for the final routing
because identity was never established in the first place. This is the
scenario that answers "what happens when the evidence genuinely isn't
enough": not a crash, not a default to either source, a quarantine with
the specific missing evidence on record.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python 3.11 or newer. Everything else is declared in
`pyproject.toml`, and installing pulls in Pydantic, Typer, Rich, and
pytest.

## Running

```bash
returnproof reconcile examples/compound_failure.json
```

or, without the console script on PATH:

```bash
python -m returnproof reconcile examples/compound_failure.json
```

Add `--json` (or `--output json`) for the machine-readable audit record
instead of the Rich terminal report. Both modes render from the same
`ReturnAuditReport`, there's no second copy of the decision logic sitting
behind the JSON flag.

```bash
returnproof reconcile examples/compound_failure.json --json
```

Every fixture under `examples/` runs the same way. `simple_condition_conflict.json`,
`batch_corruption.json`, `out_of_order_supplier.json`, `quantity_dispute.json`,
and `partial_allocation.json` each isolate one behavior described above.
`compound_failure.json` combines all of it into a resolvable decision,
`compound_unresolved.json` combines the same two failures with the
evidence stripped out, so it resolves to a defensible quarantine instead.

## Tests

```bash
pytest
```

86 tests across validation, evidence extraction, temporal ordering,
conflict detection, batch resolution, quantity handling, partial
allocation, the conservation invariant, both compound scenarios, and the
CLI. `tests/test_adversarial.py` and `tests/test_compound_unresolved.py`
hold the cases an adversarial review pass added afterward: permutation
invariance across every ordering of a 3-event set (not just one reversal),
genuinely tied supplier events staying unresolved instead of picking a
winner by event id, duplicate event deliveries collapsing without a false
conflict, two format-valid but conflicting batch codes never resolved by
guessing, an uncorroborated supplier batch against warehouse corruption
staying unresolved even when product metadata exists for the SKU (just not
for that code), a supplier RESTOCK against UNKNOWN condition and a
supplier SCRAP against GOOD condition both being flagged (not just the
damage-vs-RESTOCK direction), and a check that the human and JSON outputs
agree on every material value for the same input. The compound scenario
tests check the reasoning, not just the final numbers, rule IDs, evidence
statuses, and the separation between physical and commercial outcomes are
all asserted directly, along with determinism checks (identical input
reconciled twice, and the same supplier events reconciled in every
possible array order for a 3-event set).

```bash
ruff check src/ tests/
```

## Example Output

Running the compound failure scenario produces a full Rich report per
item. The tail of it looks like this.

```text
CONFLICTS
  ! CONDITION_DISAGREEMENT: warehouse reports condition DAMAGED_UNSAFE but supplier event evt-2
instructs RESTOCK
  ! BATCH_MISMATCH: warehouse batch 'BA?9O2' does not match supplier batch 'BA1902'
  ! QUANTITY_OR_ELIGIBILITY_DISPUTE: warehouse recorded 6 damaged units, supplier credits 4

FINAL ALLOCATION
  6   SCRAP    -        DAMAGED_UNSAFE confirmed by warehouse inspection, unsafe for restock
                         regardless of supplier instruction
  18  RESTOCK  2026-10  intact stock with resolved batch identity and best-before date

COMMERCIAL  credit_eligible=True  credit_quantity=4
INTEGRITY   24 received, 24 allocated  PASS
RULES APPLIED  R001, R002, R003, R004, R005, R006, R008
```

`--json` produces the same decision as a `ReturnAuditReport` document,
with every evidence claim, resolved field, conflict, allocation, and
rejected alternative available for a downstream system to consume.

## Design Decisions

**Core logic is deterministic.** No LLM sits in the decision path. Given
the same input, ReturnProof always produces the same routing, the same
batch resolution, and the same rule set, and that's checked directly in
the test suite rather than assumed. If a natural-language explanation
layer gets added later, it would only be allowed to phrase an
already-determined decision, never make one.

**Physical and commercial decisions are kept apart on purpose.** An item
can be scrapped physically and still carry a nonzero credit_quantity, or
be restocked while credit_eligible is false. Coupling the two would let a
supplier's financial incentive quietly steer where stock physically goes,
which is exactly the failure mode the assessment brief calls out.

**Quarantine represents uncertainty, not a third default.** It's what
happens when identity or safety can't be established from the evidence
available, not a fallback picked because neither RESTOCK nor SCRAP felt
right. Every quarantine allocation carries the specific reason evidence
was insufficient.

**Supplier arrival order is ignored on purpose.** `received_at` exists
only as audit metadata. Using it to order supplier state would mean a
network delay could silently overwrite a newer decision with a stale one,
which is the exact bug the out-of-order failure mode is built to catch.

**Invalid evidence loses authority locally, not globally.** A corrupted
warehouse batch doesn't make the supplier's batch automatically correct,
it only opens the door for the supplier's value to be checked against
independent product metadata. If that check fails, the field stays
unresolved rather than falling back to whichever source still has a
value.

## Limitations

The default batch code format (two letters, four to six digits) and the
OCR confusion map used for SUSPECT repair candidates are both invented for
this exercise. `ProductMetadata.batch_pattern` lets a SKU override the
default with its own regex, so the grammar isn't hardcoded globally, but
no repair-candidate generation exists for a custom pattern (the digit
positions of an arbitrary format aren't known), and a real deployment
would still need the actual supplier's batch grammar rather than either
of these.

Supplier disposition instructions are only specially handled in the two
directions that matter most: RESTOCK against damaged/unknown condition,
and SCRAP against confirmed-good condition. A supplier QUARANTINE
preference against warehouse-confirmed GOOD stock isn't separately
handled, it currently proceeds to RESTOCK if identity is resolved. Adding
every combination of the 4-condition by 3-instruction matrix wasn't worth
the complexity for the two directions that carry real risk (destroying
good stock, or restocking unsafe/unidentified stock).

There's no warehouse system integration, no supplier API integration, and
no persistence. Input is a single JSON document per return, and output is
printed or returned in-process, nothing is written to a database or
queued anywhere.

Product metadata in the examples is a small hand-written list of known
batches per SKU. A real catalog integration would need to handle SKUs
with large batch histories and probably fuzzy matching rather than exact
string comparison.

There's no probabilistic model anywhere. Every confidence signal in the
output is a category (DIRECT, CORROBORATED, INFERRED, UNRESOLVED), not a
number, because a fabricated percentage would be less honest than no
number at all.

There's no human review workflow. QUARANTINE is the terminal state
ReturnProof produces for uncertain stock, what happens to it after that is
outside this system.

## What I Would Do Next

Configurable policies, so the field-authority table and the batch format
in `validation.py` could be swapped per deployment without touching code.

A persistence layer for the audit trail, most likely the append-only
JSONL ledger sketched in the original proposal (`record_hash`,
`previous_hash`, `input_hash`, canonical JSON plus SHA-256), so a decision
can be proven to have used specific evidence after the fact, not just
logged.

A human review queue for QUARANTINE items, since right now that state is
a defensible stopping point but not a workflow.

Webhook ingestion for supplier events instead of a single JSON document
per return, which would also be where idempotency and event signatures
would need to get solved properly.

Real batch master-data integration in place of the small hand-written
product metadata list.

An optional natural-language explanation layer that narrates an
already-resolved `ItemAuditRecord`, strictly downstream of the decision,
never upstream of it.

Property-based tests over the allocation and temporal-ordering logic,
particularly around the conservation invariant, on top of the fixed-case
tests that exist now.

Policy versioning and decision replay, so a past decision could be
re-run against the policy version that was actually in effect when it was
made.
