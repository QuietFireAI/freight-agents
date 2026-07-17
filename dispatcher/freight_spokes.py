"""Real spokes for the freight-brokerage vertical - no no-op lambdas.

Built one agent at a time against the ratified content in each agent's
SKILL.md and DECISIONS.md (freight-agents-blueprint, ratified 2026-07-11).
Each spoke does deterministic real work on the payload, submits its OWN
thought trace (agent-open-mind's ingest is part of the spoke contract),
and reacts by sending follow-on envelopes over the hub.

Built so far: 13 (Freight Records - system of record) and 01 (Load Intake).
13 is built first/alongside 01 because 01's dedupe round-trip has a hard
dependency on it, same reason listing's P11 demo needed 14-CRM alongside 01.
"""
from __future__ import annotations

from .core import Envelope

# Confidence vocabulary is swarm-wide and closed - exactly these three.
SOURCE_VERIFIED = "source_verified"
STATED_BY_PARTY = "stated_by_party"
UNKNOWN = "unknown"

# Fields the intake checklist requires present (with a source) before a
# tender is COMPLETE. This is the completeness gate named in 01's job
# component #2. Not configurable per-deployment - it's the swarm-standard
# checklist named in the identity content itself.
REQUIRED_FIELDS = ("origin", "destination", "appointment_window",
                    "commodity", "weight", "equipment")

# Legal-line trigger phrases for rate/capacity requests (01 SKILL.md S3).
# Deliberately broad and conservative per "if classification is uncertain,
# treat it as over the line" - a false-positive escalation costs a human
# a look; a false negative crosses the legal line silently.
_RATE_TRIGGER_WORDS = ("rate", "quote", "price", "$", "capacity",
                       "guarantee capacity", "can you commit")


def _env(frm, to, intent, ctx, payload, confidence=UNKNOWN):
    return Envelope(from_agent=frm, to_agent=to, intent=intent,
                    client_context_id=ctx, payload=payload,
                    confidence=confidence,
                    provenance={"source": f"spoke-{frm}",
                                "captured_at": "runtime",
                                "verbatim_available": True})


class Spoke13FreightRecords:
    """The load file: append-only per-load record, verbatim lookups,
    rate/margin need-to-know custody enforced at the record.

    DECISIONS.md tuples implemented directly:
      - two entries conflict on a material fact -> both stand, conflict
        flagged to the requester (never silently reconciled). Fixed
        2026-07-17: had zero implementing code - "both stand" was
        trivially true (append-only never overwrites) but nothing was
        ever actually flagged. Generic detection now: any payload key
        with a differing value across entries for a load is surfaced as
        a conflict in record.response - not guessing at which specific
        fields count as "material," which would mean inventing domain
        rules this agent has no authority to invent.
      - a request would cross the rate/margin custody line -> refuse,
        scope named (never approximate)
      - corrections are new entries referencing the corrected entry_id;
        originals never change (append-only, MANNERS #3 + #10)

    NOT implemented, found during review 2026-07-17 - genuine structural
    gaps, not guessed at:
      - retention conflicts with an open claim/dispute, the hold wins ->
        there is no retention/expiration policy anywhere in this class at
        all (records are pure in-memory, append-only, never pruned) - so
        there's nothing for a claim/dispute hold to conflict WITH yet.
        This tuple describes behavior for a retention mechanism that
        doesn't exist; building a fake one to satisfy the tuple would be
        worse than naming the gap honestly.
      - storage write unconfirmed -> not done until re-verified - this
        class has no real persistent storage layer (a Python dict write
        cannot meaningfully "fail" the way a real database/file write
        can); this tuple describes a real storage backend's failure mode
        that doesn't exist in the current in-memory implementation.
    """

    def __init__(self, hub):
        self.hub = hub
        # load_key -> list of entries (append-only; never mutated/deleted)
        self.records: dict[str, list[dict]] = {}
        self._entry_seq = 0
        hub.register("13", self.handle)

    def _new_entry_id(self) -> str:
        self._entry_seq += 1
        return f"E{self._entry_seq:06d}"

    def _append(self, load_key: str, kind: str, env: Envelope,
                scope: str = "general") -> str:
        """scope: 'shipper' or 'carrier' gates rate/margin exposure at
        answer-time; 'general' is visible to any legitimate requester."""
        entry_id = self._new_entry_id()
        entry = {"entry_id": entry_id, "kind": kind,
                 "envelope_id": env.envelope_id, "from_agent": env.from_agent,
                 "payload": env.payload, "scope": scope,
                 "corrects": None}
        self.records.setdefault(load_key, []).append(entry)
        return entry_id

    def _load_key(self, env: Envelope) -> str:
        # client_context_id is the swarm-wide scoping key (client isolation,
        # MANNERS #7); freight load records are keyed on it directly.
        return env.client_context_id

    def handle(self, env: Envelope):
        load_key = self._load_key(env)

        if env.intent == "record.request":
            # Fail closed: an unspecified requester_scope must NOT default
            # to unrestricted access. The prior default was "general",
            # which collided with the unrelated entry-scope label
            # "general" and matched neither the carrier- nor shipper-block
            # check - meaning an unspecified requester silently saw
            # everything, including rate/margin data. Now: unspecified
            # scope is blocked from BOTH carrier- and shipper-scoped
            # entries by default.
            requester_scope = env.payload.get("requester_scope", "unspecified")
            dedupe_key = env.payload.get("dedupe_key")
            entries = self.records.get(load_key, [])

            if dedupe_key is not None:
                # Agent 01's dedupe use: does this load_key already have a
                # captured-load entry? Answered from the record, not
                # inference. load.captured itself goes to 02, not 13 - what
                # 13 actually sees is 01's interaction.log carrying
                # kind='load.captured' in its payload; check THAT, not a
                # literal 'load.captured' entry kind that never lands here.
                known = any(e["kind"] == "interaction.log"
                           and e["payload"].get("kind") == "load.captured"
                           for e in entries)
                self.hub.ingest_spoke_trace(
                    "13", env.envelope_id,
                    thought=f"dedupe lookup load_key={load_key!r}: "
                            f"{'HIT - prior load.captured entry exists' if known else 'MISS - no prior entry'}",
                    result=f"known={known}")
                self.hub.send(_env("13", env.from_agent, "record.response",
                                   load_key, {"known": known},
                                   confidence=SOURCE_VERIFIED))
                return

            # General record lookup: rate/margin custody line enforced HERE,
            # at the record, not left to the requester's discretion.
            # Allow-list, not deny-list: a scoped entry (shipper/carrier)
            # is visible ONLY to a requester explicitly identified as that
            # same scope. Anything else - including "unspecified" - is
            # blocked from BOTH. "general"-scoped entries (non-rate-bearing)
            # remain visible to everyone regardless of requester_scope.
            visible = []
            blocked_count = 0
            for e in entries:
                if e["scope"] in ("shipper", "carrier") and e["scope"] != requester_scope:
                    blocked_count += 1
                    continue
                visible.append(e)

            if blocked_count:
                self.hub.ingest_spoke_trace(
                    "13", env.envelope_id,
                    thought=f"requester_scope={requester_scope!r} crosses "
                            f"rate/margin custody line on {blocked_count} "
                            f"entr{'y' if blocked_count == 1 else 'ies'}; "
                            f"legal line - not a judgment call, refusing "
                            f"those entries with scope named",
                    result=f"refused={blocked_count}, returned={len(visible)}")
            else:
                self.hub.ingest_spoke_trace(
                    "13", env.envelope_id,
                    thought=f"load_key={load_key!r}: {len(visible)} entries, "
                            f"none absent from requester_scope={requester_scope!r}",
                    result=f"returned={len(visible)}")

            # tuple: two entries conflict on a material fact -> both stand,
            # conflict flagged to the requester. Fixed 2026-07-17: this had
            # zero implementing code - the class docstring claimed it but
            # nothing ever compared entries for disagreement. "Both stand"
            # was trivially true (append-only never overwrites), but
            # nothing was ever actually FLAGGED. Generic detection: any
            # payload key appearing with a different value across multiple
            # entries for this load is a conflict - not guessing at which
            # specific fields count as "material," which would mean
            # inventing domain rules this agent has no authority to invent.
            # The requester judges relevance; the record's job is surfacing
            # the disagreement, never silently picking one value.
            conflicts: dict[str, list[dict]] = {}
            seen: dict[str, list[dict]] = {}
            for e in visible:
                for k, v in e["payload"].items():
                    if not isinstance(v, (str, int, float, bool)) or v is None:
                        continue
                    seen.setdefault(k, []).append(
                        {"value": v, "entry_id": e["entry_id"], "kind": e["kind"]})
            for k, occurrences in seen.items():
                distinct_values = {o["value"] for o in occurrences}
                if len(distinct_values) > 1:
                    conflicts[k] = occurrences
            if conflicts:
                self.hub.ingest_spoke_trace(
                    "13", env.envelope_id,
                    thought=f"load_key={load_key!r}: conflicting values "
                            f"found for {sorted(conflicts)} across entries - "
                            f"both/all stand, flagging to the requester "
                            f"rather than silently reconciling",
                    result=f"conflicts_flagged={sorted(conflicts)}")

            absent = len(entries) == 0
            self.hub.send(_env(
                "13", env.from_agent, "record.response", load_key,
                {"entries": visible, "absent": absent,
                 "scope_refused": blocked_count, "conflicts": conflicts},
                confidence=SOURCE_VERIFIED))
            return

        if env.intent == "interaction.log":
            self._append(load_key, "interaction.log", env)
            self.hub.ingest_spoke_trace(
                "13", env.envelope_id,
                thought="append-only interaction entry; no interpretation "
                        "applied to what was logged",
                result="logged")
            return

        # Audit-receiver role: every other artifact intent 13 is IN-receiver
        # for (carrier.vet.result, doc.received, ratecon.record, track.status,
        # detention.record, accessorial.record, claim.package,
        # carrierpay.record, invoice.record) lands here as an append-only
        # record. Rate-bearing intents are scoped 'shipper' or 'carrier' per
        # the margin custody line named in section 2/3; everything else is
        # 'general'.
        rate_bearing = {"ratecon.record": "carrier",
                        "carrierpay.record": "carrier",
                        "invoice.record": "shipper"}
        scope = rate_bearing.get(env.intent, "general")
        entry_id = self._append(load_key, env.intent, env, scope=scope)
        self.hub.ingest_spoke_trace(
            "13", env.envelope_id,
            thought=f"audit receiver: {env.intent} appended as {entry_id} "
                    f"(scope={scope}); originals never change, corrections "
                    f"would be new entries referencing this one",
            result=f"appended={entry_id}")


class Spoke01LoadIntake:
    """Captures shipper load tenders; never quotes, never promises capacity.

    DECISIONS.md tuples implemented directly:
      - two weights stated -> capture both with sources, discrepancy travels
      - ambiguous appointment window -> record verbatim, flag unconfirmed
        (resolution downstream via comms lane - 01 has no edge to 04)
      - commodity outside configured scope -> hold and escalate (config,
        not judgment)
      - rate 'as agreed' reference -> capture the reference verbatim only,
        never resolve to a number
    """

    def __init__(self, hub, service_scope: set[str] | None = None,
                 hazmat_in_scope: bool = False):
        self.hub = hub
        self.pending: dict[str, dict] = {}
        # service_scope: commodities this deployment is configured to accept.
        # None/empty is NOT "accept everything" - it's "nothing configured
        # yet", which means every commodity is out of scope until set. This
        # matches "scope is config, not a judgment call" - the agent does
        # not default to permissive.
        self.service_scope = service_scope or set()
        self.hazmat_in_scope = hazmat_in_scope
        hub.register("01", self.handle)

    def _legal_line_hit(self, payload: dict) -> str | None:
        """Returns the verbatim trigger text if this tender crosses the
        legal line, else None. Checked BEFORE anything else - the legal
        line is not a judgment call and doesn't wait on completeness."""
        note = str(payload.get("notes", "")) + " " + str(payload.get("request", ""))
        low = note.lower()
        for w in _RATE_TRIGGER_WORDS:
            if w in low:
                return note.strip()
        return None

    def handle(self, env: Envelope):
        if env.intent == "load.signal":
            payload = env.payload
            ctx = env.client_context_id

            # --- Legal line first, unconditionally ---
            trigger = self._legal_line_hit(payload)
            if trigger:
                self.hub.ingest_spoke_trace(
                    "01", env.envelope_id,
                    thought=f"tender contains rate/capacity language: "
                            f"{trigger!r} - broker's territory (06, signed "
                            f"authority only); legal line, not a judgment "
                            f"call - escalating verbatim, not proceeding",
                    result="escalated: legal_line")
                self.hub.escalate("escalation.legal_line",
                                  {"client_context_id": ctx,
                                   "trigger": trigger, "agent": "01"})
                return

            # --- Commodity scope gate ---
            commodity = payload.get("commodity")
            is_hazmat = bool(payload.get("hazmat"))
            out_of_scope = (commodity is not None
                           and commodity not in self.service_scope)
            hazmat_blocked = is_hazmat and not self.hazmat_in_scope
            if out_of_scope or hazmat_blocked:
                reason = ("hazmat outside configured service scope"
                          if hazmat_blocked else
                          f"commodity {commodity!r} outside configured "
                          f"service scope {sorted(self.service_scope)}")
                self.hub.ingest_spoke_trace(
                    "01", env.envelope_id,
                    thought=f"{reason} - scope is config, not a judgment "
                            f"call; holding and escalating rather than "
                            f"accepting",
                    result="escalated: legal_line (scope)")
                self.hub.escalate("escalation.legal_line",
                                  {"client_context_id": ctx,
                                   "trigger": reason, "agent": "01"})
                return

            # --- Capture fields with per-field source, dual-weight tuple,
            #     ambiguous-window tuple, verbatim-rate-reference tuple ---
            captured: dict = {}
            gaps: list[str] = []

            for f in ("origin", "destination", "commodity", "equipment"):
                v = payload.get(f)
                if v in (None, ""):
                    gaps.append(f)
                else:
                    captured[f] = {"value": v, "source": STATED_BY_PARTY}

            # weight: dual-weight tuple - capture BOTH if stated, don't
            # pick one. payload may carry 'weight' (single) or 'weights'
            # (list) when the shipper stated more than one.
            weights = payload.get("weights")
            if weights:
                captured["weight"] = {"value": list(weights),
                                       "source": STATED_BY_PARTY,
                                       "note": "multiple weights stated; "
                                               "both captured, discrepancy "
                                               "travels with the load"}
            elif payload.get("weight") not in (None, ""):
                captured["weight"] = {"value": payload["weight"],
                                       "source": STATED_BY_PARTY}
            else:
                gaps.append("weight")

            # appointment window: ambiguous-window tuple
            window = payload.get("appointment_window")
            if window in (None, ""):
                gaps.append("appointment_window")
            else:
                is_ambiguous = bool(payload.get("appointment_window_ambiguous"))
                captured["appointment_window"] = {
                    "value": window, "source": STATED_BY_PARTY,
                    "confirmed": not is_ambiguous}
                if is_ambiguous:
                    captured["appointment_window"]["note"] = (
                        "verbatim capture of an ambiguous window; "
                        "confirmation via the comms lane is owed downstream "
                        "- 01 has no direct edge to 04")

            # special-handling flags, exactly as stated (never inferred)
            captured["special_handling"] = {
                "hazmat": is_hazmat,
                "temp_control": bool(payload.get("temp_control")),
                "high_value": bool(payload.get("high_value")),
                "source": STATED_BY_PARTY}

            # rate 'as agreed' reference: verbatim only, never resolved
            if payload.get("rate_reference"):
                captured["rate_reference_verbatim"] = str(
                    payload["rate_reference"])

            if gaps:
                self.hub.ingest_spoke_trace(
                    "01", env.envelope_id,
                    thought=f"tender incomplete: missing {gaps} - a field "
                            f"without provenance is unknown, never assumed "
                            f"from lane history; holding rather than "
                            f"forwarding a partial tender",
                    result=f"held: gaps={gaps}")
                self.hub.send(_env(
                    "01", "queue", "clarification.request", ctx,
                    {"reason": "incomplete tender", "gaps": gaps,
                     "captured_so_far": captured}))
                return

            self.pending[ctx] = captured
            self.hub.ingest_spoke_trace(
                "01", env.envelope_id,
                thought="tender complete; dedupe against Freight Records "
                        "before forwarding - a duplicate tender double-"
                        "counts the pipeline",
                result="record.request issued")
            self.hub.send(_env(
                "01", "13", "record.request", ctx,
                {"dedupe_key": ctx}))
            return

        if env.intent == "record.response":
            load = self.pending.pop(env.client_context_id, None)
            if load is None:
                # No pending capture for this context - correlate-or-flag,
                # never guess (SKILL.md 4.3: uncorrelated response flagged).
                self.hub.ingest_spoke_trace(
                    "01", env.envelope_id,
                    thought=f"record.response for ctx="
                            f"{env.client_context_id!r} has no matching "
                            f"pending capture - cannot correlate, flagging "
                            f"rather than guessing",
                    result="flagged: uncorrelated response")
                self.hub.send(_env(
                    "01", "queue", "clarification.request",
                    env.client_context_id,
                    {"reason": "uncorrelated record.response",
                     "envelope_id": env.envelope_id}))
                return
            load["duplicate"] = env.payload["known"]
            self.hub.ingest_spoke_trace(
                "01", env.envelope_id,
                thought=f"dedupe answer known={env.payload['known']}; "
                        f"forwarding complete captured tender to Load "
                        f"Pipeline (02)",
                result="load.captured issued")
            self.hub.send(_env(
                "01", "02", "load.captured", env.client_context_id, load,
                confidence=STATED_BY_PARTY))
            self.hub.send(_env(
                "01", "13", "interaction.log", env.client_context_id,
                {"kind": "load.captured", "duplicate": load["duplicate"]}))
