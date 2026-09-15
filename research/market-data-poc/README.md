# Portfolio Architect Tactical Tilt PoC 0.4.0

A deliberately standalone research prototype for the proposed optional **Tactical Tilt (TT)** recommendation-enhancement layer.

Version 0.4.0 keeps the established tactical scorer, calibration model, cadence-aware persistence thresholds, and v0.3.1 state contract intact, then adds **historical cadence replay**. Real daily market history can now be converted into synthetic PA planning cycles and replayed through the same rebound-aware signal and persistence governance used by the earlier fixtures. The purpose is threshold calibration against actual market behavior, not historical performance prediction.

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

## What v0.4.0 changes

- preserves the v0.2.x rebound-aware tactical scoring and v0.2.2 tactical-bonus-ceiling semantics unchanged;
- preserves the v0.3.0 stress qualification and cadence thresholds unchanged;
- preserves the v0.3.1 idempotency, execution-independence, no-tactical-debt, cadence-segmentation, target-replacement, and restart/replay contracts unchanged;
- adds `tactical_history_poc.py`;
- adds provider-neutral canonical daily OHLCV history schema 1;
- adds `history-fetch`, using the already-resolved Alpha Vantage symbol identities and the same rolling-24h provider guard as Market Data PoC 0.1.2;
- adds `history-import-csv`, so historical replay is not coupled to Alpha Vantage acquisition;
- adds `history-replay` across weekly, monthly, quarterly, and yearly synthetic PA cycle schedules;
- maps a cycle to the last completed trading session on or before the cycle date, never to future data;
- reuses the exact existing `tactical_signals()` implementation and v0.3.x stress qualification;
- derives between-cycle recovery only after a configurable number of consecutive non-stress trading sessions (default 5);
- reports insufficient historical coverage instead of extrapolating or guessing;
- keeps historical execution out of scope: daily prices are evidence, planning cycles advance governance, and human target authority remains unchanged.

The Market Data PoC acquisition path remains version 0.1.2. `TIME_SERIES_DAILY outputsize=compact` can provide a recent real-history calibration window. Alpha Vantage currently documents `outputsize=full` for this endpoint as a premium entitlement, so v0.4.0 also provides the provider-neutral CSV import path for longer histories.

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

# Part C — idempotent persistence state contract

v0.3.1 adds a second persistence harness around the v0.3.0 cadence model. The purpose is not to change when a target becomes stressed; it is to make sure repeated HA updates, restarts, later execution evidence, cadence changes, and target replacement cannot corrupt that state.

## Cycle identity

Every governance observation is identified by:

```text
plan_id
cycle_effective_date
plan_frequency
target_id
isin
```

For one configured `plan_id` / `target_id` role, only one governance observation may occupy a PA cycle date. Replaying the exact observation is a no-op. A conflicting second governance payload for the same cycle is rejected rather than counted twice.

## Execution independence and no tactical debt

Execution evidence is intentionally **audit-only**. v0.3.1 can record whether the previous TT-influenced recommendation was followed, but that field does not affect stress qualification, cycle counts, strategic-review escalation, or future tactical score.

The contract is explicit:

```text
previous recommendation followed?     audit only
previous recommendation ignored?      audit only
previous recommendation partly done?  audit only
unexecuted tactical amount owed?       never
next-cycle scoring input               current authoritative portfolio state
```

A later transaction-reconciliation feature may explain what happened, but TT correctness does not depend on execution evidence.

## Cadence changes

Changing plan frequency does not reinterpret old observations. Instead, the active governance history is segmented:

```text
old monthly segment -> retained historical evidence
frequency changes
new weekly/quarterly/yearly segment -> starts clean under its own cadence policy
```

This is deliberately conservative PoC behavior. A later production design may choose to surface prior-segment evidence during strategic review, but old monthly cycles must never become weekly cycles merely because configuration changed.

## Target replacement

A deliberate instrument change inside the same strategic target role ends the old asset segment. The old ISIN's evidence remains auditable, but the replacement ISIN starts with a clean active persistence episode. Price weakness from the retired instrument cannot be inherited as tactical stress by the replacement.

## Restart/replay safety

The research state is a canonical event log. Save/reload must reconstruct the same derived governance state, and replaying the same event batch must leave the persisted state byte-for-byte unchanged.

Run the contract harness:

```powershell
python .\tactical_persistence_poc.py state-replay `
  --events .\examples\persistence_contract_events.json
```

Outputs:

```text
output\tactical_tilt\persistence_state.json
output\tactical_tilt\persistence_contract.json
output\tactical_tilt\persistence_contract_report.txt
```

The supplied fixture demonstrates exact duplicate replay, later audit enrichment, recommendation non-compliance without tactical debt, cadence segmentation, target replacement, and deterministic restart/replay.

# Part D — historical cadence replay

Historical replay intentionally separates **market evidence** from **governance events**. Daily bars may update the evidence attached to a synthetic cycle and may confirm a recovery between cycles, but only scheduled PA cycles are passed into the persistence state machine.

## Acquire recent real history with the existing Alpha Vantage identity cache

`history-fetch` reuses `output/mapping.json` and the same ignored `output/.alpha_vantage_usage.json` rolling-24h guard used by the Market Data PoC. It does not write the API key.

```powershell
python .\tactical_history_poc.py history-fetch `
  --mapping .\output\mapping.json `
  --output .\output\history\historical_market_data.json `
  --outputsize compact
```

This requires seven provider calls for the current seven-target research set. `compact` returns the latest 100 daily sessions and is enough for a useful recent weekly/monthly calibration window, and often two quarterly observations, but it is normally too short for meaningful yearly persistence calibration. The replay reports insufficient coverage rather than inventing older evidence.

If the Alpha Vantage key has full-history entitlement, use `--outputsize full`.

## Provider-neutral history import

For longer research history from another lawful source, import one consolidated CSV with these columns:

```text
isin,name,symbol,currency,region,date,open,high,low,close,volume
```

`volume` may be empty; the other columns are required. One row represents one completed trading session.

```powershell
python .\tactical_history_poc.py history-import-csv `
  --csv .\my_historical_prices.csv `
  --output .\output\history\historical_market_data.json
```

The importer rejects duplicate session dates, changing identity metadata, invalid prices, and targets with fewer than 21 sessions.

## Replay the history

For the first recent-history experiment on 2026-09-15, a useful common anchor/window is:

```powershell
python .\tactical_history_poc.py history-replay `
  --history .\output\history\historical_market_data.json `
  --anchor 2026-06-15 `
  --start 2026-06-15 `
  --end 2026-09-15
```

Outputs:

```text
output\tactical_tilt\history\historical_replay.json
output\tactical_tilt\history\historical_replay_report.txt
```

For every target and cadence the report includes planning-cycle count, qualified stressed-cycle count, tactical-watch cycles, dates on which `strategic_review_due` was first entered, maximum stressed-cycle episode length, and final state. A review entry is **calibration evidence only**; it is not evidence by itself that the target should have been replaced.

The default between-cycle recovery rule requires 5 consecutive completed sessions that no longer meet qualified-stress conditions. This is another research constant to evaluate against real episodes, not production policy.

# Fresh market data

Generate or refresh market context as before:

```powershell
python .\market_data_poc.py fetch
```

Then run `score` or `calibrate`. The v0.3.x persistence fixtures remain deterministic and offline; v0.4.0 adds the separate historical replay path described above.

# Offline validation

```powershell
python -m unittest discover -s tests -v
python -m py_compile .\market_data_poc.py .\tactical_tilt_poc.py .\tactical_persistence_poc.py .\tactical_history_poc.py
```

The v0.4.0 bundle should report **76 tests passed**:

- 14 Market Data tests;
- 25 Tactical Tilt scoring/calibration tests;
- 25 cadence/persistence/state-contract tests;
- 12 historical acquisition/import/schedule/replay tests.

# Success criterion for v0.4.0

v0.4.0 succeeds if it demonstrates that:

- historical replay uses only market sessions available on or before each synthetic PA cycle;
- historical tactical signals are calculated by the same scorer used by the live PoC;
- daily history never increments governance state directly;
- between-cycle recovery is explicit, bounded, and auditable;
- weekly/monthly/quarterly/yearly schedules reuse the same cadence policy without changing thresholds;
- insufficient history fails closed per cadence;
- Alpha Vantage acquisition remains optional and provider-neutral CSV import can supply the same canonical input;
- strategic-review entries remain evidence for human review, never automatic target replacement or selling.

# Next research milestone

Do **not** integrate v0.4.0 directly into production PA. First run the historical replay against real target history and inspect the dated review episodes. The next version should be driven by those observations: either threshold/recovery calibration if ordinary corrections produce poor governance behavior, or a broader multi-year replay/import step if the recent compact history is insufficient to judge quarterly/yearly behavior. Only after real-history calibration should TT move toward historical allocation-state reconstruction or production integration.
