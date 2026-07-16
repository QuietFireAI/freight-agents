# SWARM.md - Framework Manifest + Swarm-Level Decisions (v0.1 (ratified 2026-07-11))

Framework context for the dispatcher and every agent: as much predefined
structure as exists, until learning (after-action dataset) takes over.
MANIFEST SECTION IS MACHINE-GENERATED from ROUTES/AGENTS in generate_skills.py
 -  regenerate via gen_meta.py; hand-edits here will be overwritten and are a
defect, not a change.

## Manifest (generated)
- Agents: 15 (00-dispatcher + 14 spokes)
- Routes: 31 entries, 31 distinct intents
- Playbooks: P01-P10 (playbooks/)
- Layer stack: MANNERS.md → DISPATCHER_CORE.md → identity/ → DECISIONS.md
  (per agent) → playbooks/ → agent SKILL.md files
- Track principle: the ROUTE-SPACE IS CLOSED. Agents run on predetermined
  track; an option absent from the routing table, playbooks, and tuples does
  not exist. Trains request routes; only the hub lines switches. Content-space
  is BOUNDED (manners, compliance verdicts) but not closed - generative freight
  is why inspection exists (05's paper-is-proof discipline, verify_swarm, after-action).
- Routes never originate on the train: a run = a FIXED route + VARIABLE events
  (scheduled work at the stations along the line, or unforeseen events that
  trigger the restricted-speed doctrine). Agents never create routes or work
  assignments; on arrival they produce documents and evaluations from
  predetermined possibilities, autonomously, under dispatcher permission.
- Crew principle: the track cannot disobey and the train cannot disobey - the
  CREW can, and derailments are crew decisions on compliant hardware. In this
  swarm the model is the crew, not the train. Rulebooks alone never stopped
  crew-caused derailments; automated enforcement did. Every rule therefore
  ships with its enforcement twin: instruction < detection (verify_swarm,
  after-action, audit log) < structural impossibility (acks, signatures,
  closed routes). Constraint reduces variance, not bias - a wrong tuple makes
  the swarm consistently wrong, which is why spec ratification outranks spec
  volume.
- Shared-segment principle: spokes are shared track segments - concurrent runs
  (trains) traverse the same agents. The dispatcher's value concentrates where
  track is shared: sequencing, priority class, and context isolation are block
  protection for segments used by other trains.
- Spokes:
- 01 Load Intake Agent
- 02 Load Pipeline Agent
- 03 Carrier Vetting Agent
- 04 Communication Agent
- 05 Document Collection Agent
- 06 Carrier Assignment Agent
- 07 Track & Trace Agent
- 08 Accessorials & Detention Agent
- 09 Claims & OSD Agent
- 10 Carrier Pay Records Agent
- 11 Shipper Invoicing Agent
- 12 Compliance & Deadlines Agent
- 13 Freight Records Agent
- 14 Daily Operations Agent
- Intents: `accessorial.record`, `adjust.authority`, `carrier.vet.request`, `carrier.vet.result`, `carrierpay.record`, `claim.intake`, `claim.package`, `clarification.request`, `compliance.hold`, `config.update`, `deadline.alert`, `detention.record`, `doc.received`, `doc.request`, `escalation.*`, `integrity.violation`, `interaction.log`, `invoice.record`, `load.assign`, `load.captured`, `message.reply`, `message.request`, `message.send`, `pay.authority`, `ratecon.authority`, `ratecon.record`, `record.request`, `record.response`, `report.package`, `track.request`, `track.status`

## Swarm-level decision tuples (predictable scenarios, pre-deliberated)
- (two playbooks match one trigger, run neither; clarification.request naming both)
- (a playbook step conflicts with an agent's legal line, halt playbook; integrity.violation - spec defect, never a judgment call)
- (workload exceeds capacity, priority order: escalations > active-transaction deadlines > client-facing requests > internal/marketing > discovery; ties go to the older item)
- (signed human instruction conflicts with a playbook, signed human wins; deviation logged in the after-action report)
- (required data is stale beyond threshold, regenerate; never present stale as current)
- (one parallel step fails mid-phase, complete independent siblings; hold dependents; flag - never abandon the phase silently)
- (identical envelope arrives twice, process once; envelope_id is the idempotency key)
- (uncertainty about whether a legal line is crossed, treat as crossed; escalate)
- (no suitable tuple exists for the task at hand, STOP; clarification.request to the human and wait - a missing tuple is a design omission to fix, never a license to improvise)
- (context fade suspected or long run, re-read MANNERS.md and own SKILL.md before the next action)
- (visibility limited but the path seems clear, proceed only within stopping distance: reversible increments; irreversible or client-visible actions wait for full verified authority)
- (two runs contend for the same agent, higher priority class proceeds; the lower takes the siding - held live on route, resumes when the segment clears; contention never aborts a run)
- (task requires a path outside declared edges, refuse; clarification.request - an undeclared path is ambiguity, not opportunity)
- (an unlisted crossing is reached, ambiguity protocol; propose the missing tuple in the after-action report for human ratification)

Status: v0.1 RATIFIED 2026-07-11 - manifest verified against generator data at generation
time; not runtime-tested.
