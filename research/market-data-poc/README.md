# Portfolio Architect Tactical Tilt PoC 0.3.0

A deliberately standalone research prototype for the proposed optional **Tactical Tilt (TT)** recommendation-enhancement layer.

Version 0.3.0 keeps the v0.2.x tactical scoring and calibration model intact and adds the first **cadence-aware persistence / strategic-review governance** PoC. The new persistence path is intentionally separate from scoring so that we can test memory, recovery, cadence, and human-review semantics before any production Portfolio Architect integration.

## Product boundary

Tactical Tilt is optional by design. Portfolio Architect must remain fully useful without an Alpha Vantage key or any market-data service. Missing, stale, incomplete, mixed-timestamp, or failed market context makes TT **neutral** and must never make core PA unhealthy or non-actionable.

TT is secondary by design. Strategic allocation, PA policy, provider/cash/funding constraints, execution economics, and advisory-only semantics remain authoritative. An overweight or otherwise ineligible target remains outside tactical purchase ranking even if its recent drawdown is extreme.

Persistent weakness is a different problem from a temporary dent. v0.3.0 therefore adds a governance boundary:

- temporary qualified weakness may remain a tactical opportunity;
- repeated unresolved weakness across independent PA planning cycles may become a tactical watch;
- cadence-adjusted persistence may trigger **strategic review due**;
- once strategic review is due, TT becomes neutral for that target;
- PA may present evidence and request human review;
- PA must **never** automatically replace a target, sell it, or infer strategic thesis failure from price action alone.

The human PA user remains authoritative over any strategic target change.

## What v0.3.0 changes

- preserves the v0.2.0 rebound-aware signal, candidate gate, rebound suppression, and additive scoring formula;
- preserves the v0.2.2 tactical-bonus-ceiling calibration semantics and provisional 150% research reference;
- bumps the research prototype version to 0.3.0 without changing scoring arithmetic;
- adds `tactical_persistence_poc.py` for replaying planning-cycle histories;
- adds `examples/persistence_scenarios.json` with weekly, monthly, quarterly, yearly, and recovery scenarios;
- adds cadence-aware research thresholds so there is **no universal N-cycle rule**;
- requires both cycle-count persistence **and** elapsed wall-clock persistence for strategic-review escalation;
- adds transparent market-history support to qualify a stressed cycle;
- explicitly separates **qualified weakness** from whether TT actually selected that target for a purchase;
- treats recovery as an episode boundary so separate market dents do not accumulate forever;
- suppresses tactical bonus for a target once `strategic_review_due` is reached;
- keeps strategic review advisory and records `automatic_target_replacement=false` and `automatic_sell=false`;
- expands offline regression coverage for cadence, recovery, evidence qualification, and human-authority boundaries.

The Market Data PoC 0.1.2 acquisition files remain unchanged.

# Part A — stateless Tactical Tilt scoring

## Allocation input contract

`allocation_state.json` schema 1 contains:

- `contribution_eur`;
- one row per target with ISIN, name, `target_pct`, and `current_value_eur`;
- `buy_enabled`;
- `planner_eligible` — a research boundary standing in for “PA has already decided this target is otherwise valid to buy”.

The PoC calculates strategic deficit against the **post-contribution current-plan portfolio value**. Only buy-enabled, planner-eligible, post-contribution-underweight targets become candidates.

The local `allocation_state.json` remains git-ignored.

## Market-context coherence gate

TT activates only when every strategically eligible candidate has:

- `status=ok`;
- EUR currency;
- XETRA region;
- valid 5-day return, 20-day return, drawdown and `as_of` date;
- age no greater than the configured calendar-age ceiling, default 4 days;
- the **same `as_of` date** across all candidates.

Any eligible-candidate failure makes Tactical Tilt neutral globally. The 4-calendar-day rule remains a PoC simplification, not a final exchange-calendar policy.

## Tactical signal — unchanged from v0.2.0

All signals are normalized to 0…1 and remain transparent research constants:

- short-term weakness: full scale at -5% over 5 trading sessions;
- medium-term weakness: full scale at -10% over 20 sessions;
- drawdown: full scale at -10% from the 20-session closing high;
- multi-window score: 25% short weakness + 35% medium weakness + 40% drawdown;
- rebound penalty: starts above +2% over 5 sessions and reaches full suppression at +8%;
- rebound-aware score: multi-window score × (1 - rebound penalty).

These constants are hypotheses to compare, **not** production policy.

## Reference additive model — unchanged from v0.2.2

```text
score = strategic_deficit_eur + tactical_bonus_ceiling_eur × rebound_aware_signal
```

The tactical bonus ceiling is an EUR-equivalent score addition at signal 1.0. It is not itself a direct maximum strategic sacrifice.

For a challenger versus the allocation-only leader:

```text
effective strategic gap capacity
    = tactical bonus ceiling
    × max(challenger signal - baseline signal, 0)
```

The provisional research reference remains **150% of one contribution**, not production policy.

## Run scoring

```powershell
python .\tactical_tilt_poc.py score `
  --allocation .\examples\allocation_state.example.json `
  --market-context .\examples\market_context_2026-09-14.json `
  --evaluation-date 2026-09-15
```

To test another ceiling explicitly:

```powershell
python .\tactical_tilt_poc.py score `
  --allocation .\examples\allocation_state.example.json `
  --market-context .\examples\market_context_2026-09-14.json `
  --evaluation-date 2026-09-15 `
  --tactical-bonus-ceiling-pct 150
```

`--tilt-budget-pct` remains accepted as a compatibility alias.

Outputs:

```text
output\tactical_tilt\tactical_tilt.json
output\tactical_tilt\tactical_tilt_report.txt
```

## Run calibration

```powershell
python .\tactical_tilt_poc.py calibrate `
  --allocation .\allocation_state.json `
  --market-context .\output\market_context.json `
  --evaluation-date 2026-09-15
```

Default tactical-bonus-ceiling sweep:

```text
0,25,50,75,100,125,150,175,200 % of contribution
```

Calibration outputs:

```text
output\tactical_tilt\calibration.json
output\tactical_tilt\calibration_report.txt
```

# Part B — cadence-aware persistence

## Why persistence is cycle-based

Market data may refresh every day, but repeated daily observations from one decline are not independent strategic evidence. v0.3.0 therefore advances governance state **only once per PA planning cycle**.

The persistence PoC intentionally does not accept a stream of daily market observations as governance events. A cycle record can contain the latest market evidence, but only the cycle itself increments the episode.

This means:

```text
3 weekly stressed cycles  !=  3 monthly stressed cycles
3 monthly stressed cycles !=  3 yearly stressed cycles
```

Cycle count and elapsed wall-clock persistence are evaluated together.

## Stress qualification — research constants

A cycle advances an active weakness episode only when both conditions hold:

```text
rebound-aware tactical signal >= 0.35
AND
(20-session return <= -3% OR drawdown from 20-session high <= -5%)
```

This deliberately requires a material TT signal plus supporting medium-horizon market evidence. These thresholds are research hypotheses only. They are **not** the final production definition of strategic stress.

Whether TT actually selected the asset for the contribution is recorded only as evidence. Selection does **not** control persistence: a target can remain strategically concerning even when another asset won the purchase decision.

## Cadence-aware research thresholds

v0.3.0 uses this first replay policy:

| Frequency | Tactical watch | Strategic review due |
| --- | ---: | ---: |
| Weekly | 4 stressed cycles **and** 21 elapsed days | 9 stressed cycles **and** 56 elapsed days |
| Monthly | 2 stressed cycles **and** 28 elapsed days | 3 stressed cycles **and** 56 elapsed days |
| Quarterly | 2 stressed cycles | 2 stressed cycles **and** 75 elapsed days |
| Yearly | 2 stressed cycles | 2 stressed cycles **and** 330 elapsed days |

The day floors deliberately tolerate calendar variation while preserving the intended order of magnitude. These are **PoC calibration constants**, not frozen product policy.

The important invariant is architectural: a fixed count such as “3 Tactical Tilt wins” must never be applied identically across all plan frequencies.

## Governance states

```text
normal
  no active qualified weakness episode

tactical_opportunity
  qualified weakness exists but persistence is below the cadence watch threshold

tactical_watch
  cadence-adjusted persistence deserves attention but has not crossed review threshold

strategic_review_due
  persistence crossed both cadence-cycle and elapsed-time thresholds
  -> TT tactical bonus multiplier becomes 0 for that target
  -> human strategic review required
  -> no automatic replacement, sale, or purchase action
```

## Recovery and episode boundaries

A non-qualified planning cycle closes the active episode. An explicit `recovered_since_previous_cycle=true` also closes the old episode **before** evaluating the new cycle.

That distinction matters: an asset may recover between monthly cycles and then fall again before the next planning date. v0.3.0 treats that as a **new tactical episode**, not as another tick on an old permanent counter.

Closed episodes remain available as evidence, but they do not keep advancing the current strategic-review state.

## Run the persistence replay

No API keys are needed:

```powershell
python .\tactical_persistence_poc.py replay `
  --scenarios .\examples\persistence_scenarios.json
```

Outputs:

```text
output\tactical_tilt\persistence.json
output\tactical_tilt\persistence_report.txt
```

The supplied fixture demonstrates:

- three weekly stressed cycles remain below strategic review;
- nine unresolved weekly cycles over eight weeks reach strategic review;
- two monthly stressed cycles become a watch;
- three monthly stressed cycles over roughly two months reach strategic review;
- a second unresolved quarterly observation can reach strategic review;
- a second unresolved yearly observation can reach strategic review;
- a recovered episode is closed and later weakness starts again from cycle one;
- recovery between cycles splits episodes even if weakness has returned by the next PA cycle.

## Persistence record shape

The report and JSON preserve evidence such as:

```text
plan_frequency
active episode start / last observed
stressed planning-cycle count
elapsed episode days
latest and peak tactical signal
worst 20-session return
worst drawdown
closed episode count
TT-selected cycle count (evidence only)
final governance state
tactical bonus allowed / multiplier
human strategic review required
automatic target replacement = false
automatic sell = false
```

A future PA implementation should persist equivalent provider-neutral state per strategic target, not per broker position.

# Fresh market data

Generate or refresh market context as before:

```powershell
python .\market_data_poc.py fetch
```

Then run `score` or `calibrate`. Persistence replay is offline in v0.3.0 and uses explicit planning-cycle fixtures so governance behavior remains deterministic and auditable.

# Offline validation

```powershell
python -m unittest discover -s tests -v
python -m py_compile .\market_data_poc.py .\tactical_tilt_poc.py .\tactical_persistence_poc.py
```

The v0.3.0 bundle should report **54 tests passed**:

- 14 existing Market Data tests;
- 25 existing Tactical Tilt scoring/calibration tests;
- 15 new cadence/persistence/governance tests.

# Success criterion for v0.3.0

The persistence PoC succeeds if it demonstrates all of the following without changing the established tactical scorer:

- state advances on independent PA planning cycles rather than daily refreshes;
- stressed-cycle qualification contains explicit market-history evidence;
- weekly/monthly/quarterly/yearly plans have materially different persistence semantics;
- cycle count and wall-clock duration must both be satisfied for strategic review;
- TT selection itself is not required for a target to accumulate stress evidence;
- recovery closes an episode instead of creating a lifetime weakness counter;
- strategic-review escalation neutralizes TT for the affected target;
- strategic-review escalation never automatically replaces, sells, or removes the target;
- human target authority remains explicit and auditable.

# Next research milestone

Do **not** integrate v0.3.0 directly into production PA yet. The next research step should use this replay harness to challenge the frequency thresholds and stress-qualification constants with additional synthetic histories and, over time, real PA-cycle observations. Only after those governance semantics are convincing should TT persistence be designed into PA's durable state/configuration and presentation contracts.
