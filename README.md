# freight-agents - freight brokerage vertical for the DispatcherAgents runtime

An **identity side-load**: everything vertical-specific for a 15-agent
freight-brokerage swarm, loadable into the content-neutral
[dispatcher-agents](https://github.com/QuietFireAI/dispatcher-agents) runtime.
The runtime never contains vertical text; this repo never contains transport
code. That split is the architecture.

**Status: v0.1 ratified 2026-07-11 - owner sign-off. Not runtime-hardened. No
licensed legal, FMCSA-compliance, or transportation-law review has been
performed.**

## What this is for

Operations support for a freight brokerage or dispatch office: tender
capture with special-handling flags as stated, absolute-gate carrier vetting,
rule-matched assignment on signed rate confirmations, cadenced track and
trace with exact facility timestamps, rule-cited detention and accessorial
math, deadline-tracked cargo-claim packages, POD-gated carrier settlements,
contract-cited shipper invoicing, the compliance clock engine, an append-only
load file, and the daily books.

What it never does - the five absolute lines (identity/IDENTITY-freight-brokerage-agent.md):

1. No unsigned money, no unsigned trucks - the broker commits, the swarm
   proposes from rules.
2. The vet gate is absolute - unknown blocks; entity mismatches are the
   double-brokering signal.
3. Never pressure hours - HOS pressure is a safety violation, not dispatch.
4. Paper is the proof - no POD, no delivery; documents move verbatim.
5. Claims carry facts, never fault - packages inside the clock, misses
   escalated before they land.

## Layout

| Path | What it is |
|---|---|
| `identity/routes.json` | The closed track: 31 (intent, senders, receivers) routes - single source of truth |
| `identity/priority.json` | JIT playbook priority classes (ratified 2026-07-11) |
| `identity/IDENTITY-freight-brokerage-agent.md` | The identity declaration |
| `00-dispatcher/ ... 14-daily-operations/` | 15 agent SKILL.md + DECISIONS.md (tuple layer) |
| `playbooks/P01 ... P10` | Deployment playbooks: tender-to-dispatch through EOD books |
| `SWARM.md` | Framework manifest + swarm-level tuples |
| `MANNERS.md` | Conduct constants, hash-registered at boot attestation |
| `TUPLE_INDEX.md` | Generated drill-down: tuple → agent → playbooks |
| `generate_skills.py` / `gen_meta.py` / `gen_playbooks.py` / `gen_tuple_index.py` | Generators - data tables are the spec; files are build artifacts |
| `verify_swarm.py` | Enforcement: tuple legality, edge completeness, regression - exit 0 = clean |

## Verify

```bash
python3 verify_swarm.py    # 0 failures, 0 warnings expected
```

## Load into the runtime

```bash
git clone https://github.com/QuietFireAI/dispatcher-agents.git
git clone https://github.com/QuietFireAI/freight-agents.git
cd dispatcher-agents && pip install -e ".[pillars,crypto,dev]"
```

```python
from dispatcher.loader import load_identity
ident = load_identity("/path/to/freight-agents")
```

The loader is fail-closed: no routes.json, no track, no load. It audits the
priority table's status on every load - never silently.

## Sibling identities

- [listing-agents](https://github.com/QuietFireAI/listing-agents) - real-estate listing vertical (ratified)
- [claim-agents](https://github.com/QuietFireAI/claim-agents) - insurance claims vertical (ratified)
- [reservation-agents](https://github.com/QuietFireAI/reservation-agents) - park/resort reservations vertical (ratified)
- medbilling-agents, mortgage-agents, property-mgmt-agents, practice-agents - prior drop
- enrollment-agents, hr-agents - this drop's siblings

## License

Proprietary - see LICENSE (placeholder pending legal review).
