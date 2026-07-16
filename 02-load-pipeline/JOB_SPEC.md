# Agent 02 - Load Pipeline: Complete Job Description

*Implementation spec, derived strictly from `02-load-pipeline/SKILL.md`,
`02-load-pipeline/DECISIONS.md`, `identity/routes.json`, and `MANNERS.md`.
Nothing below is invented beyond what those four sources establish. Gaps
in the ratified source are named as gaps, not filled in.*

## 1. What this agent is

The load's lifecycle owner, swarm-side. Every load that clears intake (01)
lives here from open to paper-complete close. This agent moves the load's
**paper** through the pipeline - vetting, assignment, tracking, exceptions,
document chase. It never moves the load's **price**. Rate and margin are
signed human acts executed at Agent 06; this agent's job stops at
proposing/routing, never deciding money.

## 2. Job components, in full - what the code must do

### 2.1 Open loads from `load.captured`
- Trigger: `load.captured` from 01.
- Action: open a lifecycle record for the load, keyed on `client_context_id`
  (same load-key convention as 01/13).
- **GAP - fails closed:** the job description says "drive lifecycle state
  per the ratified milestone map." No milestone map exists anywhere in the
  identity content (checked: zero files define one; three references
  assume one exists). Per the loader's own gate principle - absence of an
  expected artifact is reported by name, never silently defaulted - this
  agent's lifecycle-state tracking must **name this gap and hold**, not
  invent a milestone schema. What it CAN do without the map: record that
  the load is open, and drive the concrete, individually-specified actions
  in 2.2-2.5 below, which don't depend on the missing map. What it cannot
  do: report a load's lifecycle "stage" against a milestone taxonomy that
  was never ratified.

### 2.2 Fire carrier vetting and assignment
- Trigger: load is open and ready for a carrier.
- Action: send `carrier.vet.request` to 03 for candidate carrier(s).
- On `carrier.vet.result` (IN from 03): if the result clears vetting, send
  `load.assign` to 06 for the vetted carrier(s).
- **GAP - fails closed:** "per the ratified matching rules" - the source
  for those rules, `config/matching_rules.json`, is an **unratified
  template** (placeholder `rule_id`/`criteria`/`weight` rows, explicit
  status line: "loads fail closed while this line stands"). This agent has
  no legitimate matching weights to rank candidate carriers with. The code
  must refuse to auto-select or rank carriers by any invented weighting
  and must escalate/hold instead - the config's own status line is the
  doctrine, not a suggestion to route around.
- What the code CAN do without ratified weights: forward a vetting
  request for a carrier the agent was given (e.g., by a human or by 03's
  own candidate list), and forward `load.assign` once vetting clears -
  neither of those needs a weighted matching table. What it cannot do is
  autonomously choose BETWEEN multiple candidates by "best match."

### 2.3 Open tracking, surface exceptions
- Trigger: load is dispatched (assigned + rate-con executed, signaled by
  `ratecon.record` IN from 06).
- Action: send `track.request` to 07.
- On `track.status` (IN from 07): if it names an exception (missed check
  call, late status, dark tracking inside a delivery window), escalate to
  the human immediately with the last-known facts - per DECISIONS.md,
  silence is an exception, never an assumption of on-time.
- This component is fully buildable now - no missing config blocks it.

### 2.4 Route OSD exceptions to claims
- Trigger: an overage/shortage/damage fact surfaces in tracking
  (`track.status`) or in paperwork (`doc.received`).
- Action: send `claim.intake` to 09 with the fact, verbatim, sourced.
- Fully buildable now.

### 2.5 Chase closing paperwork; enforce the POD gate
- Action: send `doc.request` to 05 for BOL/POD.
- On `doc.received` (IN from 05): update the load's document inventory.
- **Hard rule, not a judgment call:** a load is never reported delivered
  without the POD artifact in the record. Per DECISIONS.md: "POD absent
  past the chase cadence, the load stays undelivered on the record;
  escalate - paper is the proof." Fully buildable now.

## 3. Legal-line triggers (Section 3, HITL Handoff) - escalate immediately, verbatim, no approximation
1. Any rate or margin commitment request → 06's territory, never pipeline arithmetic.
2. Assigning an unvetted or vetting-failed carrier → the vet gate is absolute, zero exceptions.
3. Declaring delivery without the POD artifact in record.

If classification is uncertain, treat it as over the line (SKILL.md S3,
restated verbatim - this is not softened anywhere in the source).

## 4. Pre-deliberated tuples (DECISIONS.md) the code must implement exactly
1. Load requirements change after assignment (weight, stops) → this is a
   **new fact** delivered to the human AND the carrier via the comms lane
   (04) - the rate-con record itself never silently stretches to absorb it.
2. Tracking goes dark inside a delivery window → exception to the human
   immediately, with last-known facts attached - never assume on-time.
3. Shipper requests mid-transit re-consignment → route to human. A
   destination change is a contract change, not an operational tweak.
4. POD absent past the chase cadence → load stays undelivered on the
   record; escalate. (No numeric "chase cadence" value is specified
   anywhere in the ratified content - another named gap: the trigger
   threshold for "past cadence" needs a real number from Jeff before this
   tuple can fire on a timer rather than only on-demand.)

Root rule restated: no suitable tuple, or an uncertain match, is STOP and
ask the human - never improvise, never pick the nearest tuple.

## 5. Full edge table (identity/routes.json, cross-checked against SKILL.md 4.2 - both agree)

| Direction | Counterparty | Intent |
|---|---|---|
| IN | ← 01 Load Intake | `load.captured` |
| OUT | → 03 Carrier Vetting | `carrier.vet.request` |
| IN | ← 03 Carrier Vetting | `carrier.vet.result` |
| OUT | → 06 Carrier Assignment | `load.assign` |
| IN | ← 06 Carrier Assignment | `ratecon.record` |
| OUT | → 07 Track & Trace | `track.request` |
| IN | ← 07 Track & Trace | `track.status` |
| OUT | → 09 Claims & OSD | `claim.intake` |
| OUT | → 05 Document Collection | `doc.request` |
| IN | ← 05 Document Collection | `doc.received` |
| OUT | → 04 Communication | `message.request` |
| IN | ← 04 Communication | `message.reply` |
| OUT | → 13 Freight Records | `record.request` |
| IN | ← 13 Freight Records | `record.response` |

No other edge is legal. A task needing any other path is an ambiguity
condition - stop, `clarification.request`, never route around it.

## 6. Summary of what blocks full "wired as it should be" status

Two real gaps in the **ratified source**, not in this implementation:

1. `config/matching_rules.json` is an unratified template - carrier
   selection-by-weight cannot be built until Jeff ratifies real
   criteria/weights.
2. The "ratified milestone map" referenced three times in the source
   content does not exist anywhere - lifecycle-stage tracking against a
   named taxonomy cannot be built until one is written and ratified.

Everything else in Sections 2.1-2.5 is fully specified and buildable now.
