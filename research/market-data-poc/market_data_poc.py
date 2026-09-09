#!/usr/bin/env python3
"""Portfolio Architect Market Data PoC.

Standalone research prototype for resolving target ISINs via OpenFIGI and
fetching end-of-day market history from Alpha Vantage. It is deliberately
isolated from Portfolio Architect runtime/planner code.

Secrets:
  ALPHAVANTAGE_API_KEY   required for Alpha Vantage calls
  OPENFIGI_API_KEY       optional; raises OpenFIGI limits

The prototype fails closed on ambiguous symbol resolution. It never guesses a
listing silently and never writes API keys to output files.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

VERSION = "0.1.0"
USER_AGENT = f"PortfolioArchitect-MarketData-PoC/{VERSION}"
OPENFIGI_MAPPING_URL = "https://api.openfigi.com/v3/mapping"
ALPHAVANTAGE_URL = "https://www.alphavantage.co/query"
DEFAULT_TIMEOUT_SECONDS = 20


class PocError(RuntimeError):
    pass


class ProviderError(PocError):
    pass


class AmbiguousResolution(PocError):
    pass


@dataclass(frozen=True)
class Target:
    isin: str
    name: str


@dataclass(frozen=True)
class DailyBar:
    day: date
    open: float
    high: float
    low: float
    close: float
    volume: float | None


def _json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_targets(path: Path) -> list[Target]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise PocError("targets file must be a non-empty JSON array")
    seen: set[str] = set()
    targets: list[Target] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise PocError(f"targets[{idx}] must be an object")
        isin = str(item.get("isin", "")).strip().upper()
        name = str(item.get("name", "")).strip()
        if len(isin) != 12 or not isin.isalnum():
            raise PocError(f"targets[{idx}].isin is invalid: {isin!r}")
        if not name:
            raise PocError(f"targets[{idx}].name is empty")
        if isin in seen:
            raise PocError(f"duplicate target ISIN: {isin}")
        seen.add(isin)
        targets.append(Target(isin=isin, name=name))
    return targets


def _request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: Any | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Any:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=request_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        retry_after = exc.headers.get("Retry-After") if exc.headers else None
        suffix = f"; Retry-After={retry_after}" if retry_after else ""
        raise ProviderError(f"HTTP {exc.code} from provider{suffix}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProviderError(f"provider transport failure: {type(exc).__name__}") from exc
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderError("provider returned invalid JSON") from exc


def openfigi_map(targets: list[Target], api_key: str | None) -> dict[str, list[dict[str, Any]]]:
    # OpenFIGI v3 mapping allows fewer jobs per request without an API key.
    batch_size = 100 if api_key else 5
    headers = {"X-OPENFIGI-APIKEY": api_key} if api_key else {}
    result: dict[str, list[dict[str, Any]]] = {}
    for offset in range(0, len(targets), batch_size):
        batch = targets[offset : offset + batch_size]
        jobs = [{"idType": "ID_ISIN", "idValue": target.isin} for target in batch]
        payload = _request_json(
            OPENFIGI_MAPPING_URL,
            method="POST",
            headers=headers,
            body=jobs,
        )
        if not isinstance(payload, list) or len(payload) != len(batch):
            raise ProviderError("OpenFIGI returned unexpected mapping response shape")
        for target, entry in zip(batch, payload, strict=True):
            if not isinstance(entry, dict):
                raise ProviderError(f"OpenFIGI returned invalid entry for {target.isin}")
            if entry.get("error"):
                raise ProviderError(f"OpenFIGI could not map {target.isin}: {entry['error']}")
            data = entry.get("data", [])
            if not isinstance(data, list):
                raise ProviderError(f"OpenFIGI returned invalid data for {target.isin}")
            result[target.isin] = [x for x in data if isinstance(x, dict)]
    return result


def _av_get(params: dict[str, str], api_key: str) -> dict[str, Any]:
    # The key is included only in the request URI. Error messages never echo the URI.
    query = dict(params)
    query["apikey"] = api_key
    url = ALPHAVANTAGE_URL + "?" + urllib.parse.urlencode(query)
    payload = _request_json(url)
    if not isinstance(payload, dict):
        raise ProviderError("Alpha Vantage returned unexpected response shape")
    if "Error Message" in payload:
        raise ProviderError("Alpha Vantage rejected the request")
    if "Information" in payload:
        raise ProviderError(f"Alpha Vantage information response: {payload['Information']}")
    if "Note" in payload:
        raise ProviderError(f"Alpha Vantage rate-limit response: {payload['Note']}")
    return payload


def av_symbol_search(keywords: str, api_key: str) -> list[dict[str, Any]]:
    payload = _av_get({"function": "SYMBOL_SEARCH", "keywords": keywords}, api_key)
    matches = payload.get("bestMatches", [])
    if not isinstance(matches, list):
        raise ProviderError("Alpha Vantage symbol search returned invalid bestMatches")
    return [x for x in matches if isinstance(x, dict)]


def _normalized_words(value: str) -> set[str]:
    out = []
    for ch in value.lower():
        out.append(ch if ch.isalnum() else " ")
    stop = {"ucits", "etf", "usd", "eur", "acc", "1c", "the", "and"}
    return {w for w in "".join(out).split() if len(w) >= 3 and w not in stop}


def _name_similarity(a: str, b: str) -> float:
    wa, wb = _normalized_words(a), _normalized_words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _av_field(candidate: dict[str, Any], key: str) -> str:
    return str(candidate.get(key, "")).strip()


def score_av_candidate(target: Target, candidate: dict[str, Any], openfigi_tickers: set[str]) -> tuple[float, list[str]]:
    symbol = _av_field(candidate, "1. symbol")
    name = _av_field(candidate, "2. name")
    typ = _av_field(candidate, "3. type").lower()
    region = _av_field(candidate, "4. region").lower()
    currency = _av_field(candidate, "8. currency").upper()
    try:
        provider_match = float(_av_field(candidate, "9. matchScore") or 0.0)
    except ValueError:
        provider_match = 0.0

    score = min(max(provider_match, 0.0), 1.0) * 20.0
    reasons: list[str] = [f"provider_match={provider_match:.3f}"]

    if currency == "EUR":
        score += 35
        reasons.append("EUR")
    if "germany" in region:
        score += 30
        reasons.append("Germany")
    if symbol.upper().endswith(".DEX"):
        score += 35
        reasons.append("XETRA-.DEX")
    elif symbol.upper().endswith(".FRA"):
        score += 10
        reasons.append("Frankfurt-.FRA")
    if "etf" in typ or "exchange traded" in typ:
        score += 20
        reasons.append("ETF")

    base = symbol.split(".", 1)[0].upper()
    if base and base in {x.upper() for x in openfigi_tickers}:
        score += 25
        reasons.append("OpenFIGI-ticker")

    similarity = _name_similarity(target.name, name)
    score += similarity * 30
    reasons.append(f"name_similarity={similarity:.3f}")
    return score, reasons


def _unique_search_terms(target: Target, figi_rows: list[dict[str, Any]]) -> list[str]:
    # ISIN is attempted first. If Alpha Vantage indexes it, this is the strongest bridge.
    terms = [target.isin]
    tickers: list[str] = []
    for row in figi_rows:
        ticker = str(row.get("ticker", "")).strip()
        if ticker and ticker not in tickers:
            tickers.append(ticker)
    # Keep the complete first-run experiment within the documented 25-call/day
    # Alpha Vantage free allowance: at most two search calls per target, then
    # seven daily-series calls = at most 21 calls for seven targets.
    terms.extend(tickers[:1])
    return terms


def resolve_one(target: Target, figi_rows: list[dict[str, Any]], av_key: str, pause_seconds: float) -> dict[str, Any]:
    openfigi_tickers = {str(x.get("ticker", "")).strip() for x in figi_rows if x.get("ticker")}
    searches: list[dict[str, Any]] = []
    merged: dict[str, dict[str, Any]] = {}

    for idx, term in enumerate(_unique_search_terms(target, figi_rows)):
        if idx:
            time.sleep(pause_seconds)
        matches = av_symbol_search(term, av_key)
        searches.append({"keywords": term, "match_count": len(matches)})
        for match in matches:
            symbol = _av_field(match, "1. symbol")
            if symbol:
                merged.setdefault(symbol, match)

    ranked = []
    for candidate in merged.values():
        score, reasons = score_av_candidate(target, candidate, openfigi_tickers)
        ranked.append((score, candidate, reasons))
    ranked.sort(key=lambda x: (-x[0], _av_field(x[1], "1. symbol")))

    candidate_dump = []
    for score, candidate, reasons in ranked[:10]:
        candidate_dump.append(
            {
                "symbol": _av_field(candidate, "1. symbol"),
                "name": _av_field(candidate, "2. name"),
                "type": _av_field(candidate, "3. type"),
                "region": _av_field(candidate, "4. region"),
                "currency": _av_field(candidate, "8. currency"),
                "match_score": _av_field(candidate, "9. matchScore"),
                "score": round(score, 3),
                "reasons": reasons,
            }
        )

    result: dict[str, Any] = {
        "isin": target.isin,
        "name": target.name,
        "openfigi": {
            "candidate_count": len(figi_rows),
            "tickers": sorted(openfigi_tickers),
            "figis": sorted({str(x.get("figi")) for x in figi_rows if x.get("figi")}),
            "candidates": [
                {
                    key: row.get(key)
                    for key in (
                        "figi",
                        "ticker",
                        "name",
                        "exchCode",
                        "marketSector",
                        "securityType",
                        "securityType2",
                        "securityDescription",
                    )
                    if row.get(key) is not None
                }
                for row in figi_rows[:25]
            ],
        },
        "alpha_vantage_searches": searches,
        "candidates": candidate_dump,
        "status": "unresolved",
        "selected": None,
    }
    if not ranked:
        result["status"] = "unsupported_symbol"
        return result

    top_score, top, _ = ranked[0]
    runner_score = ranked[1][0] if len(ranked) > 1 else -math.inf
    top_symbol = _av_field(top, "1. symbol")
    top_currency = _av_field(top, "8. currency").upper()
    top_region = _av_field(top, "4. region").lower()
    top_type = _av_field(top, "3. type").lower()

    # Strict automatic acceptance for the PoC. Anything else is left for explicit review.
    strict_identity = (
        top_symbol.upper().endswith(".DEX")
        and top_currency == "EUR"
        and "germany" in top_region
        and ("etf" in top_type or "exchange traded" in top_type)
    )
    clear_margin = top_score - runner_score >= 15.0
    if strict_identity and clear_margin:
        result["status"] = "resolved"
        result["selected"] = candidate_dump[0]
    else:
        result["status"] = "ambiguous_listing"
        result["resolution_reason"] = {
            "strict_identity": strict_identity,
            "score_margin": None if runner_score == -math.inf else round(top_score - runner_score, 3),
            "required_margin": 15.0,
        }
    return result


def resolve_all(targets: list[Target], output_dir: Path, av_key: str, figi_key: str | None, pause_seconds: float) -> dict[str, Any]:
    figi = openfigi_map(targets, figi_key)
    results = []
    for idx, target in enumerate(targets):
        if idx:
            time.sleep(pause_seconds)
        try:
            results.append(resolve_one(target, figi.get(target.isin, []), av_key, pause_seconds))
        except ProviderError as exc:
            results.append(
                {
                    "isin": target.isin,
                    "name": target.name,
                    "status": "provider_unavailable",
                    "selected": None,
                    "detail": str(exc),
                }
            )
    doc = {
        "schema": 1,
        "prototype_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "providers": {"identity": "openfigi", "market_data": "alpha_vantage"},
        "targets": results,
    }
    _json_dump(output_dir / "mapping.json", doc)
    return doc


def av_daily(symbol: str, api_key: str) -> list[DailyBar]:
    payload = _av_get(
        {"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": "compact"},
        api_key,
    )
    series = payload.get("Time Series (Daily)")
    if not isinstance(series, dict) or not series:
        raise ProviderError(f"Alpha Vantage returned no daily series for {symbol}")
    bars = []
    for day_text, values in series.items():
        if not isinstance(values, dict):
            continue
        try:
            volume_text = str(values.get("5. volume", "")).strip()
            bars.append(
                DailyBar(
                    day=date.fromisoformat(day_text),
                    open=float(values["1. open"]),
                    high=float(values["2. high"]),
                    low=float(values["3. low"]),
                    close=float(values["4. close"]),
                    volume=float(volume_text) if volume_text else None,
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(f"invalid daily bar for {symbol} on {day_text}") from exc
    bars.sort(key=lambda x: x.day, reverse=True)
    if not bars:
        raise ProviderError(f"Alpha Vantage returned no usable daily bars for {symbol}")
    return bars


def pct_change(new: float, old: float) -> float:
    if old == 0:
        raise PocError("cannot calculate return from zero close")
    return new / old - 1.0


def compute_metrics(bars: list[DailyBar], today: date | None = None) -> dict[str, Any]:
    if len(bars) < 21:
        raise PocError("insufficient_history: at least 21 daily bars required")
    latest = bars[0]
    closes_20 = [bar.close for bar in bars[:20]]
    high_20 = max(closes_20)
    now_day = today or datetime.now(timezone.utc).date()
    return {
        "quote_type": "daily_close",
        "as_of": latest.day.isoformat(),
        "age_calendar_days": (now_day - latest.day).days,
        "latest_close": latest.close,
        "return_5d": pct_change(latest.close, bars[5].close),
        "return_20d": pct_change(latest.close, bars[20].close),
        "high_close_20d": high_20,
        "drawdown_from_20d_high": pct_change(latest.close, high_20),
        "history_points": len(bars),
    }


def fetch_all(mapping_path: Path, output_dir: Path, av_key: str, pause_seconds: float) -> dict[str, Any]:
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    targets = mapping.get("targets")
    if not isinstance(targets, list):
        raise PocError("mapping.json has invalid targets")
    results = []
    for idx, item in enumerate(targets):
        if not isinstance(item, dict):
            continue
        selected = item.get("selected")
        result = {"isin": item.get("isin"), "name": item.get("name"), "status": "unavailable"}
        if item.get("status") != "resolved" or not isinstance(selected, dict):
            result["status"] = item.get("status", "unresolved")
            result["detail"] = "no unambiguous Alpha Vantage listing is cached"
            results.append(result)
            continue
        symbol = str(selected.get("symbol", "")).strip()
        if not symbol:
            result["status"] = "invalid_mapping"
            results.append(result)
            continue
        if idx:
            time.sleep(pause_seconds)
        try:
            bars = av_daily(symbol, av_key)
            metrics = compute_metrics(bars)
            result.update(
                {
                    "status": "ok",
                    "source": "alpha_vantage",
                    "symbol": symbol,
                    "currency": selected.get("currency"),
                    "region": selected.get("region"),
                    "metrics": metrics,
                }
            )
        except (PocError, ProviderError) as exc:
            result["status"] = "provider_unavailable" if isinstance(exc, ProviderError) else "insufficient_history"
            result["detail"] = str(exc)
        results.append(result)

    ok_returns = [x["metrics"]["return_20d"] for x in results if x.get("status") == "ok"]
    cross_section = None
    if ok_returns:
        cross_section = {
            "median_return_20d": statistics.median(ok_returns),
            "instrument_count": len(ok_returns),
            "note": "observational only; not a Tactical Tilt score",
        }
    doc = {
        "schema": 1,
        "prototype_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cross_section": cross_section,
        "targets": results,
    }
    _json_dump(output_dir / "market_context.json", doc)
    write_report(doc, output_dir / "report.txt")
    return doc


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:+.2f}%"


def write_report(doc: dict[str, Any], path: Path) -> None:
    lines = [
        "Portfolio Architect Market Data PoC",
        f"prototype_version: {doc.get('prototype_version')}",
        f"generated_at: {doc.get('generated_at')}",
        "",
    ]
    for item in doc.get("targets", []):
        lines.append(f"{item.get('isin')}  {item.get('name')}")
        lines.append(f"  status: {item.get('status')}")
        if item.get("status") == "ok":
            m = item["metrics"]
            lines.extend(
                [
                    f"  symbol: {item.get('symbol')}",
                    f"  currency/region: {item.get('currency')} / {item.get('region')}",
                    f"  as_of: {m['as_of']} (age {m['age_calendar_days']} calendar day(s))",
                    f"  latest_close: {m['latest_close']}",
                    f"  return_5d: {_pct(m['return_5d'])}",
                    f"  return_20d: {_pct(m['return_20d'])}",
                    f"  drawdown_from_20d_high: {_pct(m['drawdown_from_20d_high'])}",
                ]
            )
        elif item.get("detail"):
            lines.append(f"  detail: {item.get('detail')}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def require_av_key() -> str:
    key = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
    if not key:
        raise PocError("ALPHAVANTAGE_API_KEY is not set")
    return key


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("resolve", "fetch", "all"))
    parser.add_argument("--targets", type=Path, default=Path("targets.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--mapping", type=Path, default=None, help="mapping.json path for fetch; defaults to OUTPUT/mapping.json")
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0.9,
        help="pause between Alpha Vantage requests; increase if your account requires it",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        av_key = require_av_key()
        figi_key = os.environ.get("OPENFIGI_API_KEY", "").strip() or None
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if args.command in {"resolve", "all"}:
            targets = load_targets(args.targets)
            mapping = resolve_all(targets, args.output_dir, av_key, figi_key, args.pause_seconds)
            counts: dict[str, int] = {}
            for item in mapping["targets"]:
                counts[item["status"]] = counts.get(item["status"], 0) + 1
            print("resolution:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        if args.command in {"fetch", "all"}:
            mapping_path = args.mapping or (args.output_dir / "mapping.json")
            context = fetch_all(mapping_path, args.output_dir, av_key, args.pause_seconds)
            counts = {}
            for item in context["targets"]:
                counts[item["status"]] = counts.get(item["status"], 0) + 1
            print("market data:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
            print(f"report: {args.output_dir / 'report.txt'}")
        return 0
    except PocError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
