# Portfolio Architect Tactical Tilt PoC 0.2.2

A deliberately standalone research prototype for the proposed optional **Tactical Tilt (TT)** recommendation-enhancement layer.

Version 0.2.2 is a narrow terminology and calibration cleanup on top of v0.2.1. It does **not** change the v0.2.0 tactical signal, candidate gate, rebound suppression, or additive scoring formula. Its purpose is to make the calibration semantics precise before the next milestone adds cycle-aware persistence.

## Product boundary

Tactical Tilt is optional by design. Portfolio Architect must remain fully useful without an Alpha Vantage key or any market-data service. Missing, stale, incomplete, mixed-timestamp, or failed market context makes TT **neutral** and must never make core PA unhealthy or non-actionable.

TT is also secondary by design. Strategic allocation, PA policy, provider/cash/funding constraints, execution economics, and advisory-only semantics remain authoritative. This PoC does **not** reproduce the full PA planner; it studies only whether market context can safely reorder already-valid allocation candidates.

A price decline is not assumed to predict a recovery. The calibration output measures model behavior, not expected returns.

## What v0.2.2 changes

- keeps the v0.2.0 `score` formula and all tactical-signal semantics unchanged;
- keeps **`bounded_rebound_aware`** as the calibration reference model without declaring it production policy;
- replaces misleading **maximum strategic sacrifice** terminology with **tactical bonus ceiling**;
- makes explicit that the effective strategic gap TT can overcome is:

```text
strategic gap capacity = tactical bonus ceiling × positive tactical-signal advantage
```

- adds a finer default calibration sweep across **0%, 25%, 50%, 75%, 100%, 125%, 150%, 175%, 200% of one contribution**;
- marks **150% of one contribution** as a **provisional research reference only**, not a production constant;
- adds an **effective strategic gap capacity** table so the real effect of each ceiling is visible at representative signal advantages;
- renames break-even and decision-surface JSON fields to use bonus-ceiling terminology;
- adds `--tactical-bonus-ceiling-pct` to the `score` command while retaining `--tilt-budget-pct` as a compatibility alias;
- preserves the fail-neutral market-context gate and the underweight/eligibility boundary;
- expands offline regression coverage for the refined sweep, effective-gap arithmetic, and CLI alias.

The Market Data PoC 0.1.2 acquisition files remain unchanged.

## Allocation input contract

`allocation_state.json` schema 1 contains:

- `contribution_eur`;
- one row per target with ISIN, name, `target_pct`, and `current_value_eur`;
- `buy_enabled`;
- `planner_eligible` — a research boundary standing in for “PA has already decided this target is otherwise valid to buy”.

The PoC calculates strategic deficit against the **post-contribution current-plan portfolio value**. Only buy-enabled, planner-eligible, post-contribution-underweight targets become candidates. An overweight target remains ineligible even if its market drawdown is extreme.

The included allocation example is synthetic and deliberately keeps several target deficits close. It is useful for model comparison; it must not be interpreted as a production portfolio state.

## Market-context coherence gate

TT activates only when every strategically eligible candidate has:

- `status=ok`;
- EUR currency;
- XETRA region;
- valid 5-day return, 20-day return, drawdown and `as_of` date;
- age no greater than the configured calendar-age ceiling, default 4 days;
- the **same `as_of` date** across all candidates.

If any eligible candidate fails the gate, Tactical Tilt becomes neutral globally. This avoids biasing the ranking merely because one candidate lacks market data.

The 4-calendar-day rule remains a PoC simplification, not a final exchange-calendar policy.

## Tactical signal — unchanged from v0.2.0

All signals are normalized to 0…1 and remain transparent research constants:

- short-term weakness: full scale at -5% over 5 trading sessions;
- medium-term weakness: full scale at -10% over 20 sessions;
- drawdown: full scale at -10% from the 20-session closing high;
- multi-window score: 25% short weakness + 35% medium weakness + 40% drawdown;
- rebound penalty: starts above +2% over 5 sessions and reaches full suppression at +8%;
- rebound-aware score: multi-window score × (1 - rebound penalty).

These constants are hypotheses to compare, **not** a proposed production formula.

## Reference additive model

The calibration harness focuses on the v0.2.0 **bounded_rebound_aware** model:

```text
score = strategic_deficit_eur + tactical_bonus_ceiling_eur × rebound_aware_signal
```

The tactical bonus ceiling is an **EUR-equivalent score addition when the signal is 1.0**. It is **not** a direct statement that PA may sacrifice that many euros of strategic allocation advantage.

For a challenger versus the baseline:

```text
effective strategic gap capacity
    = tactical_bonus_ceiling_eur
    × max(challenger_signal - baseline_signal, 0)
```

Example with a €350 contribution and the provisional 150% research reference:

```text
tactical bonus ceiling = €525

signal edge +0.10 -> effective gap capacity €52.50
signal edge +0.25 -> effective gap capacity €131.25
signal edge +0.50 -> effective gap capacity €262.50
signal edge +0.75 -> effective gap capacity €393.75
signal edge +1.00 -> effective gap capacity €525.00
```

This distinction is the central terminology correction in v0.2.2.

## Run the supplied scoring fixture

No API keys are needed:

```powershell
python .\tactical_tilt_poc.py score `
  --allocation .\examples\allocation_state.example.json `
  --market-context .\examples\market_context_2026-09-14.json `
  --evaluation-date 2026-09-15
```

The score command retains the historical conservative 10% default for regression continuity. To test another ceiling explicitly:

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

## Run the calibration harness

Against the supplied synthetic fixture:

```powershell
python .\tactical_tilt_poc.py calibrate `
  --allocation .\examples\allocation_state.example.json `
  --market-context .\examples\market_context_2026-09-14.json `
  --evaluation-date 2026-09-15
```

Against an explicit observed PA allocation snapshot and the current Market Data PoC output:

```powershell
python .\tactical_tilt_poc.py calibrate `
  --allocation .\allocation_state.json `
  --market-context .\output\market_context.json `
  --evaluation-date 2026-09-15
```

Calibration outputs:

```text
output\tactical_tilt\calibration.json
output\tactical_tilt\calibration_report.txt
```

The report contains four main analysis sections:

1. **Tactical bonus ceiling sweep** — which target wins at each tested ceiling, the actual strategic sacrifice, signal edge, and whether the recommendation changes from allocation-only.
2. **Live challenger break-even** — the bonus ceiling required for each challenger merely to reach additive-score parity with the strategic leader.
3. **Effective strategic gap capacity** — for each tested ceiling, how much strategic gap could be overcome at representative signal advantages.
4. **Generic decision surface** — the inverse view: what bonus ceiling is required to overcome controlled strategic gaps at representative signal advantages.

Score parity is only a model threshold. It does **not** establish that the challenger will produce a higher future return.

## Calibration defaults

```text
bonus-ceiling sweep:    0,25,50,75,100,125,150,175,200 % of contribution
research reference:     150 % of contribution
strategic-gap surface:  2.5,5,10,25,50,100,200 % of contribution
signal advantages:      0.10,0.25,0.50,0.75,1.00
max market age:         4 calendar days
```

Override the sweep when useful:

```powershell
python .\tactical_tilt_poc.py calibrate `
  --sweep-pct 0,50,100,125,150,175,200,250 `
  --surface-gap-pct 5,10,25,50,100,200 `
  --surface-signal-advantages 0.10,0.25,0.50,0.75,1.00
```

These remain research knobs, not intended end-user production configuration.

## Fresh market data

Generate or refresh market context as before:

```powershell
python .\market_data_poc.py fetch
```

Then run either `score` or `calibrate`. Until a deliberate PA export path exists, populate `allocation_state.json` only from explicit observed PA state. Do not guess holdings or allocations. The file remains git-ignored.

## Offline validation

```powershell
python -m unittest discover -s tests -v
python -m py_compile .\market_data_poc.py .\tactical_tilt_poc.py
```

The v0.2.2 bundle should report **39 tests passed**: 14 existing market-data tests plus 25 Tactical Tilt/scoring/calibration tests.

## Success criterion for v0.2.2

The cleanup succeeds if calibration can be interpreted without conflating a score ceiling with an actual strategic sacrifice while preserving these boundaries:

- allocation-only remains the baseline;
- TT considers only otherwise eligible, underweight targets;
- market-data failure becomes neutral rather than blocking PA;
- the rebound-aware additive formula is unchanged;
- strong rebounds remove stale dip advantages quickly;
- actual strategic sacrifice and bonus ceiling are reported separately;
- effective-gap capacity is explicit rather than hidden inside a coefficient;
- no calibration result is presented as a forecast or proof of future outperformance.

## Next research milestone

v0.3.0 should move from stateless scoring to **cadence-aware persistence**. Daily market data may update evidence, but strategic-review state should advance only across independent PA planning cycles. Weekly, monthly, quarterly and yearly plans must not share a fixed “N stressed cycles” threshold; cycle count, elapsed wall-clock persistence, recovery behavior and supporting market-history evidence must be considered together. Persistent weakness may trigger a human strategic-review prompt, never automatic target replacement.
