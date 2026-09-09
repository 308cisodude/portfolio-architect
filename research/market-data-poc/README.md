# Portfolio Architect Market Data PoC 0.1.0

A deliberately standalone research prototype for the proposed **Tactical Tilt** market-context layer.
It does **not** modify Portfolio Architect, Home Assistant, any Gateway App, or any investment recommendation.

## Purpose

The PoC answers one narrow question before architecture work begins:

> Can all seven current Portfolio Architect target ISINs be mapped reproducibly to suitable EUR/Xetra Alpha Vantage symbols, and can we obtain sufficiently fresh daily history to calculate simple observational market-context metrics?

Identity resolution uses the public OpenFIGI v3 mapping API with `ID_ISIN`. Market data uses Alpha Vantage `SYMBOL_SEARCH` and `TIME_SERIES_DAILY` with `outputsize=compact` (latest 100 daily observations).

The resolver deliberately **fails closed**. It will automatically accept a listing only when the top Alpha Vantage candidate is an ETF in Germany, in EUR, uses the documented Xetra `.DEX` symbol suffix, and is clearly separated from the runner-up. Anything else becomes `ambiguous_listing` for human review rather than being guessed.

## Files

- `market_data_poc.py` — standalone Python 3 prototype, standard library only.
- `targets.json` — the seven current PA target ISINs used for the experiment.
- `tests/test_market_data_poc.py` — offline unit tests for candidate scoring and metric calculations.
- `.gitignore` — excludes local outputs and optional secret files.

## Credentials

Required:

- `ALPHAVANTAGE_API_KEY`

Optional:

- `OPENFIGI_API_KEY` — the anonymous OpenFIGI limits are already sufficient for seven ISINs; a key simply raises limits.

Keys are read only from environment variables. They are not written to `mapping.json`, `market_context.json`, or `report.txt`, and provider error messages do not echo request URLs.

### PowerShell

```powershell
$env:ALPHAVANTAGE_API_KEY = 'YOUR_ALPHA_VANTAGE_KEY'
# Optional:
# $env:OPENFIGI_API_KEY = 'YOUR_OPENFIGI_KEY'
```

## First run

From this directory:

```powershell
python .\market_data_poc.py resolve
```

Inspect:

```text
output/mapping.json
```

The acceptance target is **7 × `resolved`**. Do not edit the code to force a mapping merely to make the PoC pass. If one or more instruments are ambiguous or unsupported, that is an experiment result and should trigger provider/source review.

Once all mappings are acceptable:

```powershell
python .\market_data_poc.py fetch
```

or perform both phases:

```powershell
python .\market_data_poc.py all
```

Outputs:

- `output/mapping.json` — OpenFIGI evidence, Alpha Vantage candidates, and selected mapping.
- `output/market_context.json` — normalized observational metrics.
- `output/report.txt` — compact human-readable report.

## Metrics

For each resolved instrument the prototype reports:

- latest daily close and `as_of` date;
- 5-trading-day return;
- 20-trading-day return;
- highest close over the latest 20 sessions;
- drawdown from that 20-session high;
- calendar age of the latest daily bar.

It also reports the median 20-day return across successfully fetched targets as **observational context only**. There is deliberately no Tactical Tilt score and no planner integration in this prototype.

## Important limitations

This PoC tests data identity and availability, not production suitability.

- Alpha Vantage and OpenFIGI remain external dependencies whose terms and availability must be re-evaluated before shipping an official PA adapter.
- `TIME_SERIES_DAILY` is treated as provider daily data. The PoC records the provider's latest date but does not attempt a trading-calendar/market-close proof.
- OpenFIGI ticker values and Alpha Vantage symbols are different namespaces. The cross-provider bridge is therefore deliberately conservative and reviewable.
- The default first run is bounded to at most 21 Alpha Vantage calls for seven targets (up to 14 symbol searches + 7 daily-series calls), keeping `all` inside the currently documented 25-request/day free allowance.
- Xetra/EUR is a PoC preference, not yet a permanent PA policy. Some instruments may require an explicitly chosen alternative venue later.
- No raw market data should become authoritative portfolio evidence. Market Context is supplemental and must fail neutral in a future PA implementation.

## Offline validation

```powershell
python -m unittest discover -s tests -v
python -m py_compile .\market_data_poc.py
```

## What a successful PoC means

Success means all seven target instruments resolve deterministically, daily histories are available, the latest closes are plausible when checked against an independent source, and repeated runs retain stable mappings.

Only then should Portfolio Architect gain a provider-neutral `MarketContext` contract and a bounded, secondary Tactical Tilt signal. Strategic allocation, cash/funding constraints, execution policy, and advisory-only behavior remain primary.
