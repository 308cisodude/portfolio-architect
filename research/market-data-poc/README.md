# Portfolio Architect Tactical Tilt PoC 0.2.0

A deliberately standalone research prototype for the proposed optional **Tactical Tilt (TT)** recommendation-enhancement layer.

Version 0.2.0 builds on the proven Market Data PoC 0.1.2. The acquisition code is intentionally unchanged: OpenFIGI resolves ISINs to EUR/Xetra identities, Alpha Vantage supplies daily history, and `market_context.json` remains a supplemental, fail-neutral input. The new work is entirely local scoring research.

## Product boundary

Tactical Tilt is optional by design. Portfolio Architect must remain fully useful without an Alpha Vantage key or any market-data service. Missing, stale, incomplete, mixed-timestamp, or failed market context makes TT **neutral** and must never make core PA unhealthy or non-actionable.

TT is also secondary by design. Strategic allocation, PA policy, provider/cash/funding constraints, execution economics, and advisory-only semantics remain authoritative. This PoC does **not** reproduce the full PA planner; it studies only whether market context can safely reorder already-valid allocation candidates.

## What v0.2.0 adds

- `tactical_tilt_poc.py` — offline scoring prototype; makes **no network calls**.
- `examples/allocation_state.example.json` — synthetic seven-target allocation fixture, explicitly not the user's live portfolio.
- `examples/market_context_2026-09-14.json` — public-market regression fixture based on the observed 14 September 2026 Xetra closes.
- `tests/test_tactical_tilt_poc.py` — scoring, freshness, neutrality, bounding, and rebound-regression coverage.
- side-by-side comparison of an allocation-only baseline and four candidate TT policies.

The Market Data PoC 0.1.2 files remain present and unchanged so an existing `output/market_context.json` can be generated exactly as before.

## Allocation input contract

`allocation_state.json` schema 1 contains:

- `contribution_eur`;
- one row per target with ISIN, name, `target_pct`, and `current_value_eur`;
- `buy_enabled`;
- `planner_eligible` — a research boundary standing in for "PA has already decided this target is otherwise valid to buy".

The PoC calculates the strategic deficit against the **post-contribution** portfolio value. Only buy-enabled, planner-eligible, post-contribution-underweight targets are candidates.

The included allocation example is synthetic and is constructed to make several target deficits deliberately close. It is useful for model comparison; it must not be interpreted as the user's production portfolio state.

## Market-context coherence gate

TT activates only when every strategically eligible candidate has:

- `status=ok`;
- EUR currency;
- XETRA region;
- valid 5-day return, 20-day return, drawdown and `as_of` date;
- age no greater than the configured calendar-age ceiling (default 4 days, intentionally tolerant of weekends);
- the **same `as_of` date** across all candidates.

If any eligible candidate fails the gate, Tactical Tilt becomes neutral globally. This avoids biasing the ranking merely because one candidate lacks market data.

The default 4-calendar-day rule is a PoC simplification, not a final exchange-calendar policy.

## Tactical signals

All signals are normalized to 0…1 and are deliberately transparent research constants:

- short-term weakness: full scale at -5% over 5 trading sessions;
- medium-term weakness: full scale at -10% over 20 sessions;
- drawdown: full scale at -10% from the 20-session closing high;
- multi-window score: 25% short weakness + 35% medium weakness + 40% drawdown;
- rebound penalty: starts above +2% over 5 sessions and reaches full suppression at +8%;
- rebound-aware score: multi-window score × (1 - rebound penalty).

The rebound guard is motivated by the live W1TB observation: Cybersecurity moved from a deep medium-term drawdown to +8.18% over five sessions and a new 20-session high. A stale "it was cheap recently" bonus should disappear immediately.

These constants are hypotheses to compare, **not** a proposed production formula.

## Candidate models

The report calculates these side by side:

1. **baseline_allocation_only** — largest strategic post-contribution deficit; no market input.
2. **bounded_drawdown_only** — adds a bounded EUR-equivalent bonus based only on current 20-session drawdown.
3. **bounded_multi_window** — bounded bonus using 5d weakness, 20d weakness and drawdown.
4. **bounded_rebound_aware** — the same bounded signal, suppressed after a strong short-term rebound.
5. **tie_break_rebound_aware** — Tactical Tilt may reorder only candidates already within a bounded strategic-deficit band.

By default the bounded bonus is at most **10% of the planned contribution**. With a EUR 350 contribution, TT can contribute at most EUR 35 of score. Therefore a candidate more than EUR 35 behind the strategic leader cannot win a bounded model, even with a perfect tactical score.

The tie-break model likewise considers only candidates within 10% of the contribution (EUR 35 by default) of the best strategic deficit.

The report explicitly shows `strategic_sacrifice_eur` whenever a TT model selects something other than the allocation-only baseline.

## Run the supplied regression fixture

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

The fixture is designed so ordinary allocation ranking prefers MSCI World, while the strongest rebound-aware TT candidates can prefer Robotics with only a small, explicitly bounded strategic sacrifice. Cybersecurity receives no rebound-aware bonus after its observed sharp recovery.

## Run against a fresh Market Data PoC output

Generate or refresh market context as before:

```powershell
python .\market_data_poc.py fetch
```

Then provide a real `allocation_state.json` and run:

```powershell
python .\tactical_tilt_poc.py score
```

The default input paths are:

```text
allocation_state.json
output\market_context.json
```

Until we deliberately create a PA export path, populate `allocation_state.json` only from an explicit observed PA state. Do not guess holdings or allocations.

## Research knobs

Defaults:

```text
--tilt-budget-pct 10
--tie-band-pct 10
--max-market-age-days 4
```

These exist to compare sensitivity. They are not intended as end-user production configuration yet.

## Offline validation

```powershell
python -m unittest discover -s tests -v
python -m py_compile .\market_data_poc.py .\tactical_tilt_poc.py
```

The v0.2.0 bundle should report **28 tests passed** (14 existing market-data tests + 14 Tactical Tilt tests).

## Success criterion for v0.2.x

The scoring PoC succeeds if we can feed real PA allocation state plus coherent market context into several explainable bounded models and observe:

- core allocation ranking remains the baseline;
- TT never considers an otherwise invalid buy candidate;
- market-data failure becomes neutral rather than blocking PA;
- no TT model can sacrifice more strategic deficit than its explicit bound;
- strong rebounds remove stale "buy-the-dip" advantages quickly;
- every changed recommendation is explainable from the report.

Only after comparing the models on real PA states should one policy be proposed for production integration.
