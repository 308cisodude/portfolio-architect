# Portfolio Architect Market Data PoC 0.1.2

A deliberately standalone research prototype for the proposed **Tactical Tilt** market-context layer.
It does **not** modify Portfolio Architect, Home Assistant, any Gateway App, or any investment recommendation.

## Purpose

The PoC asks one narrow question before architecture work begins:

> Can all seven current Portfolio Architect target ISINs be mapped reproducibly to suitable EUR/Xetra Alpha Vantage symbols, and can we obtain sufficiently fresh daily history to calculate simple observational market-context metrics?

Version 0.1.2 retains the evidence-driven venue resolver introduced after the first live run and adds conservative provider-budget hardening before further live requests.

The resolver gives each provider one responsibility:

1. OpenFIGI maps each ISIN **with `micCode=XETR` and `currency=EUR`** and must return exactly one distinct venue ticker.
2. Alpha Vantage searches only that ticker.
3. The mapping is accepted only when Alpha Vantage returns exactly one matching `<ticker>.DEX` candidate that is an ETF, EUR-denominated, and identified as Xetra/Germany.
4. The accepted identity mapping is cached locally; normal market-history refreshes do not repeat symbol resolution.

No score-margin heuristic is required for final identity selection. Candidate scores remain diagnostics only.

## Files

- `market_data_poc.py` — standalone Python 3 prototype, standard library only.
- `targets.json` — the seven current PA target ISINs used for the experiment.
- `tests/test_market_data_poc.py` — offline unit tests for resolver, OpenFIGI batching, Alpha Vantage pacing/budget state, and metrics.
- `.gitignore` — excludes local outputs and optional secret files.
- `.gitattributes` — keeps this research subtree LF-normalized for deterministic hashes.

## Credentials

Required:

- `ALPHAVANTAGE_API_KEY`

Recommended:

- `OPENFIGI_API_KEY`

Keys are read only from environment variables. They are never written to output files.

With an OpenFIGI API key, the seven `ID_ISIN` mapping jobs are sent in **one OpenFIGI POST**. Without a key, this PoC deliberately uses conservative batches of five jobs, so seven targets require two OpenFIGI POSTs.

## Alpha Vantage safety policy

The default policy is deliberately conservative for an ordinary free key:

- minimum interval between Alpha Vantage request starts: **12.5 seconds**;
- local Alpha Vantage ceiling: **25 calls per rolling 24 hours**;
- usage state persists in ignored `output/.alpha_vantage_usage.json`, so separate `resolve` and `fetch` invocations do not accidentally bypass pacing or the local counter;
- a request is counted immediately before network dispatch because a transport failure may still have reached the provider;
- the state contains no API key.

The local counter can only account for calls made by this PoC. It deliberately uses a rolling 24-hour window rather than assuming an undocumented provider quota-reset timezone. If calls were already made with the same key before v0.1.2 created its usage-state file, seed the first run explicitly:

```powershell
python .\market_data_poc.py resolve --av-used-last-24h 14
```

`--av-used-last-24h` is applied only when the usage-state file does not yet exist. Because the exact prior timestamps are unknown, seeded calls are conservatively treated as if they happened at seed time and remain in the local window for a full 24 hours. It cannot overwrite an established counter.

If Alpha Vantage later confirms an unlimited daily entitlement for the open-source project, the local rolling-24h ceiling can be disabled explicitly:

```powershell
python .\market_data_poc.py resolve --av-daily-limit 0
```

Do that only after Alpha Vantage confirms the entitlement. The 12.5-second pacing remains in force unless Alpha Vantage separately confirms a different request-frequency policy.

## Call budget

For seven targets:

- initial resolver: at most **7 Alpha Vantage `SYMBOL_SEARCH` calls**;
- daily-history fetch after resolution: at most **7 `TIME_SERIES_DAILY` calls**;
- one fresh `all` run: at most **14 Alpha Vantage calls**;
- steady-state daily operation after cached resolution: **7 Alpha Vantage calls**.

OpenFIGI identity resolution is separate and is not part of the Alpha Vantage call budget.

## First run

Load both keys into the current PowerShell process without echoing them, then run only the resolver:

```powershell
python .\market_data_poc.py resolve
```

Inspect `output/mapping.json`. The acceptance target is **7 × `resolved`**.

Once all mappings are acceptable and the Alpha Vantage daily budget permits it:

```powershell
python .\market_data_poc.py fetch
```

or both phases on a fresh allowance:

```powershell
python .\market_data_poc.py all
```

## Metrics

For each resolved instrument the prototype reports:

- latest daily close and `as_of` date;
- 5-trading-day return;
- 20-trading-day return;
- highest close over the latest 20 sessions;
- drawdown from that 20-session high;
- calendar age of the latest daily bar.

There is deliberately no Tactical Tilt score and no planner integration yet.

## Important limitations

- Alpha Vantage and OpenFIGI are external dependencies whose terms, entitlement and availability must be reviewed before production use.
- Local Alpha Vantage usage accounting cannot see requests made from other applications or machines using the same key.
- `TIME_SERIES_DAILY` is provider daily data; the PoC records the provider date but does not prove a trading-calendar close boundary.
- Xetra/EUR is a PoC preference, not yet a permanent PA policy.
- No raw market data becomes authoritative portfolio evidence. Future Market Context must remain supplemental and fail neutral.
- A missing, multiple, or inconsistent Xetra mapping fails closed rather than selecting another venue automatically.

## Offline validation

```powershell
python -m unittest discover -s tests -v
python -m py_compile .\market_data_poc.py
```

The v0.1.2 bundle should report **14 tests passed**.

## What success means

Success means all seven target instruments resolve deterministically, daily histories are available, latest closes survive independent plausibility checks, and repeated runs retain stable mappings.

Only then should Portfolio Architect gain a provider-neutral `MarketContext` contract and a bounded secondary Tactical Tilt signal. Strategic allocation, cash/funding constraints, execution policy, and advisory-only behavior remain primary.
