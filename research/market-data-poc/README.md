# Portfolio Architect Tactical Tilt PoC 0.2.1

A deliberately standalone research prototype for the proposed optional **Tactical Tilt (TT)** recommendation-enhancement layer.

Version 0.2.1 adds a **calibration harness** on top of the v0.2.0 scoring PoC. The market-data acquisition path and the tactical signal formula are intentionally unchanged. The new question is narrower: **how much strategic allocation advantage are we willing to surrender in exchange for unusually favorable recent market context?**

## Product boundary

Tactical Tilt is optional by design. Portfolio Architect must remain fully useful without an Alpha Vantage key or any market-data service. Missing, stale, incomplete, mixed-timestamp, or failed market context makes TT **neutral** and must never make core PA unhealthy or non-actionable.

TT is also secondary by design. Strategic allocation, PA policy, provider/cash/funding constraints, execution economics, and advisory-only semantics remain authoritative. This PoC does **not** reproduce the full PA planner; it studies only whether market context can safely reorder already-valid allocation candidates.

A price decline is not assumed to predict a recovery. The calibration output measures model behavior, not expected returns.

## What v0.2.1 adds

- keeps the v0.2.0 `score` command and all scoring semantics backward-compatible;
- treats **`bounded_rebound_aware`** as the reference model for calibration without declaring it production policy;
- adds a `calibrate` command that sweeps explicit maximum-strategic-sacrifice bounds;
- default sweep: **0%, 25%, 50%, 75%, 100%, 150%, 200% of one contribution**;
- calculates live challenger break-even requirements against the allocation-only leader;
- generates a generic decision surface across controlled strategic gaps and tactical-signal advantages;
- preserves the fail-neutral market-context gate and candidate eligibility boundary;
- adds calibration regressions for bound sensitivity, break-even math, neutral context, and overweight exclusion.

The Market Data PoC 0.1.2 files remain unchanged. `market_context.json` is still produced exactly as before.

## Allocation input contract

`allocation_state.json` schema 1 contains:

- `contribution_eur`;
- one row per target with ISIN, name, `target_pct`, and `current_value_eur`;
- `buy_enabled`;
- `planner_eligible` — a research boundary standing in for “PA has already decided this target is otherwise valid to buy”.

The PoC calculates strategic deficit against the **post-contribution** current-plan portfolio value. Only buy-enabled, planner-eligible, post-contribution-underweight targets become candidates. An overweight target therefore remains ineligible even if its market drawdown is extreme.

The included allocation example is synthetic and is constructed to make several target deficits deliberately close. It is useful for model comparison; it must not be interpreted as a production portfolio state.

## Market-context coherence gate

TT activates only when every strategically eligible candidate has:

- `status=ok`;
- EUR currency;
- XETRA region;
- valid 5-day return, 20-day return, drawdown and `as_of` date;
- age no greater than the configured calendar-age ceiling (default 4 days, intentionally tolerant of weekends);
- the **same `as_of` date** across all candidates.

If any eligible candidate fails the gate, Tactical Tilt becomes neutral globally. This avoids biasing the ranking merely because one candidate lacks market data.

The default 4-calendar-day rule remains a PoC simplification, not a final exchange-calendar policy.

## Tactical signal — unchanged from v0.2.0

All signals are normalized to 0…1 and remain transparent research constants:

- short-term weakness: full scale at -5% over 5 trading sessions;
- medium-term weakness: full scale at -10% over 20 sessions;
- drawdown: full scale at -10% from the 20-session closing high;
- multi-window score: 25% short weakness + 35% medium weakness + 40% drawdown;
- rebound penalty: starts above +2% over 5 sessions and reaches full suppression at +8%;
- rebound-aware score: multi-window score × (1 - rebound penalty).

The rebound guard is motivated by the observed W1TB move: after a sharp recovery, a stale “it was cheap recently” bonus should disappear immediately.

These constants are hypotheses to compare, **not** a proposed production formula.

## Reference additive model

The calibration harness focuses on the v0.2.0 **bounded_rebound_aware** model:

```text
score = strategic_deficit_eur + sacrifice_bound_eur × rebound_aware_signal
```

Because the tactical signal is bounded to 0…1, a challenger cannot sacrifice more strategic deficit than the configured bound. The strategic deficit remains the base score; market context only adds a bounded secondary advantage.

The older side-by-side models remain available through `score`, but calibration does not tune or rewrite them.

## Run the supplied scoring fixture

No API keys are needed:

```powershell
python .\tactical_tilt_poc.py score `
  --allocation .\examples\allocation_state.example.json `
  --market-context .\examples\market_context_2026-09-14.json `
  --evaluation-date 2026-09-15
```

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

The report has three main sections:

1. **Maximum strategic sacrifice sweep** — shows which target wins at each tested bound, the actual strategic sacrifice, tactical-signal edge, and whether the recommendation changes from allocation-only.
2. **Live challenger break-even** — for each challenger, calculates the additive-score parity bound required to catch the strategic leader. A challenger whose tactical signal does not exceed the leader has no positive-bound break-even.
3. **Generic decision surface** — shows the bound required to reach parity for controlled strategic gaps and signal advantages. This lets the sacrifice policy be chosen deliberately rather than from one portfolio snapshot.

Score parity is only a model threshold. It does **not** establish that the challenger will produce a higher future return.

## Calibration defaults

```text
sacrifice sweep:       0,25,50,75,100,150,200 % of contribution
strategic-gap surface: 2.5,5,10,25,50,100,200 % of contribution
signal advantages:     0.10,0.25,0.50,0.75,1.00
max market age:        4 calendar days
```

They can be overridden for research, for example:

```powershell
python .\tactical_tilt_poc.py calibrate `
  --sweep-pct 0,10,25,50,75,100,125,150,200 `
  --surface-gap-pct 5,10,25,50,100,200 `
  --surface-signal-advantages 0.10,0.25,0.50,0.75,1.00
```

These are research knobs, not intended end-user production configuration.

## Fresh market data

Generate or refresh market context as before:

```powershell
python .\market_data_poc.py fetch
```

Then run either `score` or `calibrate`. Until a deliberate PA export path exists, populate `allocation_state.json` only from an explicit observed PA state. Do not guess holdings or allocations. The file remains git-ignored.

## Offline validation

```powershell
python -m unittest discover -s tests -v
python -m py_compile .\market_data_poc.py .\tactical_tilt_poc.py
```

The v0.2.1 bundle should report **36 tests passed**: 14 existing market-data tests, 14 v0.2.0 Tactical Tilt tests, and 8 calibration tests.

## Success criterion for v0.2.1

The calibration milestone succeeds if it lets us choose a maximum strategic sacrifice from explicit evidence rather than intuition alone while preserving these boundaries:

- allocation-only remains the baseline;
- TT considers only otherwise eligible, underweight targets;
- market-data failure becomes neutral rather than blocking PA;
- the rebound-aware additive model cannot sacrifice more than its explicit bound;
- strong rebounds remove stale dip advantages quickly;
- live challenger break-even requirements are visible rather than hidden inside a coefficient;
- no calibration result is presented as a forecast or proof of future outperformance.

Only after observing the decision surface on realistic states should a production sacrifice policy be proposed.
