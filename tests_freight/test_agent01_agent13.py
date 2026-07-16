"""Pressure test for freight Agent 01 (Load Intake) + Agent 13 (Freight
Records) - the first pair built, real spokes, real hub, real identity
routes.json. No stubs, no mocks of the hub/routes/audit machinery.
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, "/home/claude/pillars_pth")

from dispatcher.core import Envelope, Routes, AuditLog
from dispatcher.hub import Hub
from dispatcher.freight_spokes import Spoke01LoadIntake, Spoke13FreightRecords

IDENTITY_ROUTES = os.path.join(os.path.dirname(__file__), "..", "identity",
                               "routes.json")


def make_hub(tmp_path, **kw):
    audit_path = os.path.join(tmp_path, f"audit-{uuid.uuid4().hex[:8]}.jsonl")
    return Hub(Routes(IDENTITY_ROUTES), AuditLog(audit_path), **kw)


def signal(ctx, payload, frm="20"):
    return Envelope(from_agent=frm, to_agent="01", intent="load.signal",
                    client_context_id=ctx, payload=payload,
                    provenance={"source": "spoke-20", "captured_at": "runtime",
                                "verbatim_available": True})


def test_complete_tender_flows_through_to_load_captured(tmp_path):
    hub = make_hub(str(tmp_path))
    Spoke13FreightRecords(hub)
    Spoke01LoadIntake(hub, service_scope={"electronics", "produce"})
    hub.on_turn_start()

    ctx = "load-001"
    hub.send(signal(ctx, {
        "origin": "Columbus, OH", "destination": "Memphis, TN",
        "commodity": "electronics", "weight": 42000,
        "equipment": "dry van", "appointment_window": "08:00-10:00",
    }))

    events = hub.audit.read()
    # NOTE: 'load.captured' targets agent 02, which does not exist yet
    # (built one at a time). It correctly PERSISTS and dead-letters on
    # delivery ("no handler for 02") rather than acking - that's the
    # honest, expected state right now, not a bug. Check persisted, not acked.
    persisted_events = [e for e in events if e["kind"] == "envelope.persisted"]
    intents = [e["intent"] for e in persisted_events]
    dead = [e for e in events if e["kind"] == "dead.letter"]

    assert "record.request" in intents
    assert "load.captured" in intents
    assert "interaction.log" in intents
    assert any(d["reason"] == "no handler for 02" for d in dead), \
        "expected load.captured to dead-letter cleanly (agent 02 not built yet)"

    lc = next(e for e in persisted_events if e["intent"] == "load.captured")
    assert lc["payload"]["origin"]["value"] == "Columbus, OH"
    assert lc["payload"]["duplicate"] is False
    assert lc["payload"]["appointment_window"]["confirmed"] is True


def test_incomplete_tender_holds_and_clarifies(tmp_path):
    hub = make_hub(str(tmp_path))
    Spoke13FreightRecords(hub)
    Spoke01LoadIntake(hub, service_scope={"electronics"})
    hub.on_turn_start()

    ctx = "load-002"
    hub.send(signal(ctx, {"origin": "Columbus, OH", "commodity": "electronics"}))

    events = hub.audit.read()
    clar = [e for e in events if e["kind"] == "envelope.persisted"
           and e["intent"] == "clarification.request"]
    assert len(clar) == 1
    gaps = clar[0]["payload"]["gaps"]
    assert "destination" in gaps and "weight" in gaps
    assert "appointment_window" in gaps
    # must NOT have forwarded to 02
    lc = [e for e in events if e["kind"] == "envelope.persisted"
         and e["intent"] == "load.captured"]
    assert not lc


def test_rate_quote_language_hits_legal_line(tmp_path):
    hub = make_hub(str(tmp_path))
    Spoke13FreightRecords(hub)
    Spoke01LoadIntake(hub, service_scope={"electronics"})
    hub.on_turn_start()

    ctx = "load-003"
    hub.send(signal(ctx, {
        "origin": "Columbus, OH", "destination": "Memphis, TN",
        "commodity": "electronics", "weight": 10000, "equipment": "dry van",
        "appointment_window": "08:00-10:00",
        "notes": "shipper is asking can you commit to a rate today",
    }))

    assert hub.queues["escalation.legal_line"], \
        "rate-language tender did not escalate to legal_line"
    assert not [e for e in hub.audit.read()
               if e["kind"] == "envelope.persisted" and e["intent"] == "load.captured"]


def test_out_of_scope_commodity_escalates_not_accepts(tmp_path):
    hub = make_hub(str(tmp_path))
    Spoke13FreightRecords(hub)
    Spoke01LoadIntake(hub, service_scope={"produce"})  # electronics NOT in scope
    hub.on_turn_start()

    ctx = "load-004"
    hub.send(signal(ctx, {
        "origin": "Columbus, OH", "destination": "Memphis, TN",
        "commodity": "electronics", "weight": 10000, "equipment": "dry van",
        "appointment_window": "08:00-10:00",
    }))

    assert hub.queues["escalation.legal_line"]
    assert "electronics" in hub.queues["escalation.legal_line"][-1]["trigger"]


def test_dual_weight_both_captured_not_resolved(tmp_path):
    hub = make_hub(str(tmp_path))
    Spoke13FreightRecords(hub)
    Spoke01LoadIntake(hub, service_scope={"electronics"})
    hub.on_turn_start()

    ctx = "load-005"
    hub.send(signal(ctx, {
        "origin": "Columbus, OH", "destination": "Memphis, TN",
        "commodity": "electronics", "weights": [41500, 42000],
        "equipment": "dry van", "appointment_window": "08:00-10:00",
    }))

    events = hub.audit.read()
    lc = next(e for e in events if e["kind"] == "envelope.persisted"
             and e["intent"] == "load.captured")
    assert lc["payload"]["weight"]["value"] == [41500, 42000]


def test_duplicate_tender_flagged_by_records(tmp_path):
    hub = make_hub(str(tmp_path))
    Spoke13FreightRecords(hub)
    Spoke01LoadIntake(hub, service_scope={"electronics"})
    hub.on_turn_start()

    payload = {"origin": "Columbus, OH", "destination": "Memphis, TN",
              "commodity": "electronics", "weight": 10000,
              "equipment": "dry van", "appointment_window": "08:00-10:00"}
    ctx = "load-006"
    hub.send(signal(ctx, dict(payload)))
    hub.send(signal(ctx, dict(payload)))  # same ctx again = duplicate

    events = hub.audit.read()
    lcs = [e for e in events if e["kind"] == "envelope.persisted"
          and e["intent"] == "load.captured"]
    assert len(lcs) == 2
    assert lcs[0]["payload"]["duplicate"] is False
    assert lcs[1]["payload"]["duplicate"] is True


def test_rate_margin_custody_line_enforced_at_record(tmp_path):
    hub = make_hub(str(tmp_path))
    recs = Spoke13FreightRecords(hub)
    hub.on_turn_start()
    ctx = "load-007"

    # simulate a shipper-scoped invoice record landing in 13
    hub.send(Envelope(from_agent="11", to_agent="13", intent="invoice.record",
                      client_context_id=ctx, payload={"amount": 5000},
                      provenance={"source": "spoke-11", "captured_at": "runtime",
                                  "verbatim_available": True}))

    # a carrier-scoped requester asks for the record - should be refused/scoped out
    hub.send(Envelope(from_agent="06", to_agent="13", intent="record.request",
                      client_context_id=ctx,
                      payload={"requester_scope": "carrier"},
                      provenance={"source": "spoke-06", "captured_at": "runtime",
                                  "verbatim_available": True}))

    events = hub.audit.read()
    resp = [e for e in events if e["kind"] == "envelope.persisted"
           and e["intent"] == "record.response"][-1]
    assert resp["payload"]["scope_refused"] == 1
    assert resp["payload"]["entries"] == []


def test_all_six_pillars_fire_on_freight_traffic(tmp_path):
    """Same assertion the listing P11 demo makes, done for real: every
    pillar seam must fire on THIS identity's traffic, not just listing's.
    Each of the six is genuinely exercised, not asserted by tautology:
      - before-turn:        hub.on_turn_start()
      - open-mind:          hub._reflect() + analyze_reflections() with a
                             thought/action pair scored as drifted
      - agent-open-mind:    a deliberately empty-thought spoke trace, to
                             prove the taint gate catches it on this hub
      - pre-response-selfcheck: selfcheck_model armed, fires on delivery
      - sleep-marks:        a real build_transfer/receive_transfer/
                             confirm_release crew-change round trip
      - splitvantage:       crosspol_models armed + a drift-flagged
                             reflection, so second_opinion actually runs
    """
    from dispatcher.analysis import analyze_reflections, score_spoke_traces
    from dispatcher.signatures import Ed25519Signer, Ed25519Verifier
    from dispatcher.territory import (build_transfer, receive_transfer,
                                      confirm_release)

    def stub_selfcheck(prompt):
        return "PASS"

    def stub_model_a(prompt):
        return {"model": "stub-a", "response": "maybe fine", "thinking": "uncertain"}

    def stub_model_b(prompt):
        return {"model": "stub-b", "response": "Fine.", "thinking": ""}

    hub = make_hub(str(tmp_path), selfcheck_model=stub_selfcheck,
                   crosspol_models=(stub_model_a, stub_model_b))
    Spoke13FreightRecords(hub)
    Spoke01LoadIntake(hub, service_scope={"electronics"})
    hub.on_turn_start()  # before-turn

    ctx = "load-pillars"
    hub.send(signal(ctx, {
        "origin": "Columbus, OH", "destination": "Memphis, TN",
        "commodity": "electronics", "weight": 10000, "equipment": "dry van",
        "appointment_window": "08:00-10:00",
    }))  # exercises pre-response-selfcheck (armed) on every delivery

    # open-mind + splitvantage: a drift-worthy thought/action pair, same
    # phrasing pattern proven to score >= 0.4 in the listing P11 demo
    hub._reflect(ctx, "I am not sure; the weight might be wrong",
                "Weight confirmed.")
    analyze_reflections(hub)

    # agent-open-mind: deliberately empty thought - THE negative-path
    # exhibit, exercised directly against this hub rather than requiring a
    # standing broken spoke in production code
    hub.ingest_spoke_trace("13", "synthetic-taint-check", thought="",
                           result="deliberately dark trace for pillar proof")
    score_spoke_traces(hub)

    # sleep-marks: a real signed crew-change round trip
    signer = Ed25519Signer()
    xfer = build_transfer(hub, [ctx], signer)
    ack = receive_transfer(hub, xfer, Ed25519Verifier(signer.public_key_bytes()))
    confirm_release(hub, [ctx], ack)

    events = hub.audit.read()
    pillar_events = {k: sum(1 for e in events if e["kind"] == k) for k in
                     ("beforeturn.check", "openmind.drift",
                      "agentopenmind.tainted", "selfcheck.verdict",
                      "sleepmark.captured", "splitvantage.review")}
    assert all(v > 0 for v in pillar_events.values()), (
        f"a pillar did not fire on freight's own traffic: {pillar_events}")
