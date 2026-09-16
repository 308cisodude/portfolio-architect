# Portfolio Architect Tactical Tilt PoC 0.4.4

A deliberately standalone research prototype for the proposed optional **Tactical Tilt (TT)** recommendation-enhancement layer.

Version 0.4.4 keeps the established tactical scorer, calibration model, stress qualification, cadence thresholds, idempotent state contract, v0.4.3 cadence-independent recovery behavior, and historical replay semantics unchanged. It hardens **historical data acquisition** for multi-year calibration by adding an explicit adjusted-price basis. Alpha Vantage adjusted history is converted into internally consistent adjusted OHLC using the provider's adjusted close, so historical split/dividend discontinuities cannot masquerade as Tactical Tilt drawdowns.

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

## What v0.4.4 changes

- preserves the v0.2.x rebound-aware tactical scoring and v0.2.2 tactical-bonus-ceiling semantics unchanged;
- preserves the v0.3.x stress qualification, cadence thresholds, idempotency, execution-independence, no-tactical-debt, cadence-segmentation, target-replacement, and restart/replay contracts unchanged;
- preserves the v0.4.0 historical replay, v0.4.1 episode forensics, v0.4.2 confirmed-recovery-only closure, and v0.4.3 cadence-independent recovery behavior unchanged;
- adds `--price-basis adjusted` to `history-fetch`;
- uses Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED` only when adjusted history is explicitly requested;
- derives adjusted open/high/low from the daily `adjusted_close / raw_close` factor, with adjusted close as the canonical close;
- retains volume exactly as supplied because TT does not currently use volume;
- records `price_basis`, `quote_type`, adjustment method, and provider function in the canonical history file and replay reports;
- keeps `--price-basis raw` as the default, preserving the proven v0.4.3 fetch behavior and avoiding accidental premium-endpoint calls;
- lets provider-neutral CSV imports explicitly declare `--price-basis adjusted` when their OHLC is already adjusted;
- remains backward-compatible with existing schema-1 raw history files that predate the `price_basis` field.

The existing 100-session raw file remains valid for reproducing the v0.4.3 recovery results. The adjusted path is intended for the upcoming **multi-year calibration dataset**, not as a reason to re-fetch recent history unnecessarily.

The Market Data PoC acquisition path remains version 0.1.2. Live/regular EOD Tactical Tilt input is unchanged; v0.4.4 changes only the historical-research acquisition layer.

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

An active weakness episode closes only when recovery is confirmed (`recovered_since_previous_cycle=true`) or when an explicit lifecycle boundary segments the state. A merely non-qualified planning cycle does **not** prove recovery. If no recovery is confirmed, the episode remains unresolved, its wall-clock age continues through that PA cycle, and its stressed-cycle count does not increment.

That distinction matters for choppy declines: stress → one borderline/non-qualified PA cycle → stress is still one unresolved market episode unless the configured daily-session recovery rule was satisfied in between. Conversely, an asset may genuinely recover between monthly cycles and then fall again before the next planning date; confirmed recovery closes the old episode **before** evaluating the new cycle, so later weakness starts a new tactical episode rather than extending an old permanent counter.

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
- confirmed market-session recovery splits episodes even if weakness has returned by the next PA cycle.

## Persistence record shape

The report and JSON preserve evidence such as:

```text
plan_frequency
active episode start / last stressed / last observed
stressed planning-cycle count
unresolved non-stress planning-cycle count
elapsed unresolved episode days
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

Historical replay intentionally separates **market evidence** from **governance events**. Daily bars may update the evidence attached to a synthetic cycle and may confirm recovery through a continuous completed-session run across PA-cycle boundaries, but only scheduled PA cycles are passed into the persistence state machine. The current cycle's completed market session may be the session that completes recovery; this does not make the daily session a governance event.

## Acquire Alpha Vantage history with an explicit price basis

`history-fetch` reuses `output/mapping.json` and the same ignored `output/.alpha_vantage_usage.json` rolling-24h guard used by the Market Data PoC. It does not write the API key.

The existing raw path remains the default and is unchanged:

```powershell
python .\tactical_history_poc.py history-fetch `
  --mapping .\output\mapping.json `
  --output .\output\history\historical_market_data.json `
  --outputsize compact
```

For **multi-year calibration**, request adjusted history explicitly:

```powershell
python .\tactical_history_poc.py history-fetch `
  --mapping .\output\mapping.json `
  --output .\output\history\historical_market_data.json `
  --outputsize full `
  --price-basis adjusted
```

The adjusted path requests `TIME_SERIES_DAILY_ADJUSTED`. Alpha Vantage supplies raw daily OHLC plus adjusted close; v0.4.4 derives an internally consistent adjusted OHLC basis for each session:

```text
adjustment_factor = adjusted_close / raw_close
adjusted_open      = raw_open  × adjustment_factor
adjusted_high      = raw_high  × adjustment_factor
adjusted_low       = raw_low   × adjustment_factor
adjusted_close     = provider adjusted close
```

TT currently derives its historical signals from closes, but keeping OHLC on one coherent basis prevents later research code from accidentally mixing adjusted close with raw intraday ranges. Volume is retained provider-supplied and is not consumed by TT.

The canonical history document records:

```text
price_basis
quote_type
adjustment_method
volume_basis
alpha_vantage_function
requested_outputsize
```

`raw` remains the default intentionally. The adjusted Alpha Vantage endpoint is a separate provider capability; v0.4.4 never silently upgrades an ordinary history request to it.

`compact` remains useful for recent research. `full` is the target for multi-year calibration when the API key is entitled to the provider's full adjusted history. The current seven-target set still requires seven provider requests.

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

If that external dataset is already split/dividend adjusted, declare it rather than silently treating it as raw:

```powershell
python .\tactical_history_poc.py history-import-csv `
  --csv .\my_adjusted_historical_prices.csv `
  --output .\output\history\historical_market_data.json `
  --price-basis adjusted
```

The importer rejects duplicate session dates, changing identity metadata, invalid prices, targets with fewer than 21 sessions, and inconsistent price-basis metadata. Imported adjusted data is trusted to be pre-adjusted by its source; v0.4.4 does not invent corporate-action adjustments for an arbitrary CSV.

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
output\tactical_tilt\history\episode_forensics_report.txt
```

The compact replay report retains the aggregate view: planning-cycle count, qualified stressed-cycle count, tactical-watch cycles, dates on which `strategic_review_due` was first entered, maximum stressed-cycle episode length, and final state.

The forensics report expands every detected episode into dated evidence. It distinguishes `active_stressed`, `active_unresolved`, and `closed_recovered` continuity, records first/last stressed market evidence, the last observed PA cycle, unresolved non-stress cycle count, peak/latest signals, worst 5-day and 20-day return, maximum drawdown, and highest governance state. For episodes closed by recovery it records the exact completed market sessions that satisfied the configured recovery run. A review entry or episode is **calibration evidence only**; it is not evidence by itself that the target should have been replaced.

The default recovery rule remains 5 consecutive completed sessions that no longer meet qualified-stress conditions. v0.4.2 made that confirmation authoritative for market-episode closure and v0.4.3 made it cadence-independent. v0.4.4 does not alter those semantics. A non-qualified PA cycle without recovery evidence still leaves the episode unresolved. The five-session value remains a research constant to evaluate against real episodes, not production policy.

# Fresh market data

Generate or refresh market context as before:

```powershell
python .\market_data_poc.py fetch
```

Then run `score` or `calibrate`. The persistence fixtures remain deterministic and offline. v0.4.4 does not change the live/EOD market-context acquisition path; adjusted history is a separate research input for long-horizon replay.

# Offline validation

```powershell
python -m unittest discover -s tests -v
python -m py_compile .\market_data_poc.py .\tactical_tilt_poc.py .\tactical_persistence_poc.py .\tactical_history_poc.py
```

The v0.4.4 bundle should report **95 tests passed**:

- 14 Market Data tests;
- 25 Tactical Tilt scoring/calibration tests;
- 27 cadence/persistence/state-contract tests;
- 29 historical acquisition/import/schedule/replay/forensics/recovery/adjusted-price tests.

# Success criterion for v0.4.4

v0.4.4 succeeds if it demonstrates that:

- all v0.4.3 scoring, persistence, episode, recovery, and human-governance semantics remain unchanged;
- legacy/raw historical fetch remains the default and still uses `TIME_SERIES_DAILY`;
- adjusted historical fetch is explicit and uses `TIME_SERIES_DAILY_ADJUSTED`;
- adjusted close cannot be combined with raw OHLC silently; adjusted OHLC is derived deterministically from one per-session factor;
- malformed/non-positive adjusted prices fail closed without publishing a partial history file;
- API keys remain absent from history artifacts;
- canonical history and replay output expose the price basis and adjustment provenance;
- provider-neutral CSV history can explicitly declare already-adjusted OHLC without provider-specific coupling;
- existing schema-1 raw history remains replay-compatible;
- insufficient history still fails closed per cadence;
- strategic-review evidence remains advisory and target replacement remains human-owned.

# Next research milestone

Do **not** integrate v0.4.4 directly into production PA and do not tune TT thresholds yet. The next evidence step is to obtain a **multi-year adjusted daily dataset** for the seven resolved Xetra targets and replay the unchanged v0.4.4 model across weekly, monthly, quarterly, and yearly cadences. Prefer the full adjusted Alpha Vantage path if the key is entitled to it; otherwise use the provider-neutral adjusted-CSV import path. The desired sample should span several ordinary corrections and at least one prolonged stress regime. Only after that replay should qualification, recovery, cadence thresholds, or historical allocation-state reconstruction change.
