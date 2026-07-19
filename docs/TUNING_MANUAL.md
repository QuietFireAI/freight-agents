# TUNING_MANUAL - freight-agents (blueprint)

Every configurable parameter, placeholder, and ratification in this identity.
Rule (inherited doctrine): any commit introducing a tunable updates this
manual in the same commit. The working build (freight-agents) syncs this file.

---

## TOP OF LIST - Deliberate placeholders & unratified content (read before deployment)

Full sweep 2026-07-18. If it's not in this table it's ratified content or
real spec.

| Item | Where | Status | What blocks / what to do |
|---|---|---|---|
| Signer identity | `config/authority_signers.json` | **RATIFIED FOR TEST 2026-07-18** — "Dr. Jeff Phillips" is a fictional test persona | Demo/test only. Production MUST replace `signer_login` with a real IdP login; the IdP seam (INTEGRATIONS.md) is a go-live prerequisite for any authority intent. |
| Free-time/accessorial rules | `config/freetime_accessorial_rules.json` | **DOCTRINE RATIFIED / entries deployment content** | Zero-threshold doctrine binding; empty rule table = all money beyond rules = signed. |
| Vetting minimums | `config/vetting_minimums.json` | **DOCTRINE RATIFIED / minimums deployment content** | Standing-is-a-live-fact doctrine binding; load your insurance/authority/safety floors. |
| Matching rules / tracking cadence / DNU list | `config/matching_rules.json`, `config/tracking_cadence.json`, `config/do_not_use_list.json` | **DEPLOYMENT CONTENT** | Owner-ratified versions required before lifecycle playbooks run. |
| Message templates | `config/message_templates.json` | **UNRATIFIED — awaiting owner sign-off per template** | Fill `approved_by` per template. |
| Working-build handler coverage | freight-agents `dispatcher/freight_spokes.py` | **PARTIAL BY DESIGN** | Working repo implements the 01↔13 demo path plus hub/notifier; the other routes are spec-complete with tests pending. Honest gap, named here. |

---

## Ratified (owner: Jeff Phillips, 2026-07-18)

| Parameter | Value | Consumer |
|---|---|---|
| Books reconciliation tolerance | **$0.00**, both carrier-pay and shipper-invoice sides — permeates all blueprints | 10, 11 → `reconciliation.exception` |
| Zero-threshold money doctrine | rule-matching auto with citation; everything else signed, any amount | 08, 10, 11 |
| Standing is a live fact | mid-cycle vetting change fires same turn; ratecons never auto-cancel | 03 (P11, class 1) |
| Incident handoff | verbatim, same-turn, no fault/liability language anywhere | 04/07 (P12, class 1) |

### The $0.00 rule (permeates ALL identity blueprints - owner decision 2026-07-18)

Any variance between posted money and reconciled books, any amount, is a
`reconciliation.exception` routed to the human and the books. No "close
enough" lane. The HITL is notified on every variance.

---

## PROPOSED thresholds — pending owner ratification

Conservative defaults until ratified or amended.

| Parameter | Proposed | Consumer |
|---|---|---|
| Check-call cadence (in transit) | every 4 hours | 07 / tracking_cadence.json |
| Detention alert | 30 min before free time expires | 08 |
| POD chase start | 24 hours post-delivery | 05 (P03) |
| Carrier insurance re-verify | at assignment + any load >14 days after last verify | 03 |
| Invoice submission SLA | 24 hours post-POD | 11 (P07) |
| Claim acknowledgment | 24 hours from intake | 09 (P05) |
| Records-response lead alert / escalation | 10 / 3 days | 12 (P14) |
