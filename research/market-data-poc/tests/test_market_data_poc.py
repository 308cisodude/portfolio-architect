import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from market_data_poc import (
    AlphaVantageGuard,
    DailyBar,
    ProviderError,
    Target,
    build_parser,
    compute_metrics,
    openfigi_map,
    resolve_one,
    score_av_candidate,
)


class CandidateScoringTests(unittest.TestCase):
    def setUp(self):
        self.target = Target("IE00BJ0KDQ92", "Xtrackers MSCI World UCITS ETF 1C")

    def test_xetra_eur_etf_beats_frankfurt(self):
        xetra = {
            "1. symbol": "XDWD.DEX",
            "2. name": "Xtrackers MSCI World UCITS ETF 1C",
            "3. type": "ETF",
            "4. region": "XETRA",
            "8. currency": "EUR",
            "9. matchScore": "0.95",
        }
        frankfurt = {
            "1. symbol": "XDWD.FRK",
            "2. name": "Xtrackers MSCI World UCITS ETF 1C",
            "3. type": "ETF",
            "4. region": "Frankfurt",
            "8. currency": "EUR",
            "9. matchScore": "0.95",
        }
        sx, _ = score_av_candidate(self.target, xetra, {"XDWD"})
        sf, _ = score_av_candidate(self.target, frankfurt, {"XDWD"})
        self.assertGreater(sx, sf)
        self.assertGreaterEqual(sx - sf, 20)

    def test_wrong_currency_is_penalized(self):
        eur = {
            "1. symbol": "XDWD.DEX",
            "2. name": "Xtrackers MSCI World UCITS ETF 1C",
            "3. type": "ETF",
            "4. region": "XETRA",
            "8. currency": "EUR",
            "9. matchScore": "0.90",
        }
        usd = dict(eur)
        usd["8. currency"] = "USD"
        se, _ = score_av_candidate(self.target, eur, {"XDWD"})
        su, _ = score_av_candidate(self.target, usd, {"XDWD"})
        self.assertGreater(se, su)


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.target = Target("IE00BJ0KDQ92", "Xtrackers MSCI World UCITS ETF 1C")
        self.guard = object()

    @patch("market_data_poc.av_symbol_search")
    def test_filtered_openfigi_ticker_resolves_exact_dex_candidate(self, search):
        search.return_value = [
            {
                "1. symbol": "XDWD.DEX",
                "2. name": "db x-trackers MSCI World Index UCITS DR 1C",
                "3. type": "ETF",
                "4. region": "XETRA",
                "8. currency": "EUR",
                "9. matchScore": "0.727",
            },
            {
                "1. symbol": "XDWD.FRK",
                "2. name": "db x-trackers MSCI World Index UCITS DR 1C",
                "3. type": "ETF",
                "4. region": "Frankfurt",
                "8. currency": "EUR",
                "9. matchScore": "0.800",
            },
        ]
        result = resolve_one(
            self.target,
            [{"figi": "BBGTEST", "ticker": "XDWD", "securityType": "ETF"}],
            "test-key",
            self.guard,
        )
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["selected"]["symbol"], "XDWD.DEX")
        self.assertEqual(result["resolution_reason"]["openfigi_mic"], "XETR")
        search.assert_called_once_with("XDWD", "test-key", self.guard)

    @patch("market_data_poc.av_symbol_search")
    def test_multiple_filtered_openfigi_tickers_fail_before_alpha_vantage(self, search):
        result = resolve_one(
            self.target,
            [{"ticker": "XDWD"}, {"ticker": "XDWDEUR"}],
            "test-key",
            self.guard,
        )
        self.assertEqual(result["status"], "ambiguous_openfigi_listing")
        search.assert_not_called()

    @patch("market_data_poc.av_symbol_search")
    def test_exact_symbol_with_wrong_currency_stays_ambiguous(self, search):
        search.return_value = [
            {
                "1. symbol": "XDWD.DEX",
                "2. name": "Xtrackers MSCI World UCITS ETF 1C",
                "3. type": "ETF",
                "4. region": "XETRA",
                "8. currency": "USD",
                "9. matchScore": "0.95",
            }
        ]
        result = resolve_one(
            self.target,
            [{"ticker": "XDWD"}],
            "test-key",
            self.guard,
        )
        self.assertEqual(result["status"], "ambiguous_listing")
        self.assertFalse(result["resolution_reason"]["strict_identity"])


class OpenFigiBatchTests(unittest.TestCase):
    def targets(self):
        return [Target(f"IE00000000{i:02d}", f"Target {i}") for i in range(7)]

    @patch("market_data_poc._request_json")
    def test_authenticated_openfigi_batches_seven_isins_in_one_request(self, request):
        request.return_value = [{"data": [{"ticker": f"T{i}"}]} for i in range(7)]
        result = openfigi_map(
            self.targets(),
            "figi-key",
            mic_code="XETR",
            currency="EUR",
        )
        self.assertEqual(len(result), 7)
        self.assertEqual(request.call_count, 1)
        kwargs = request.call_args.kwargs
        self.assertEqual(len(kwargs["body"]), 7)
        self.assertTrue(all(job["idType"] == "ID_ISIN" for job in kwargs["body"]))
        self.assertTrue(all(job["micCode"] == "XETR" for job in kwargs["body"]))
        self.assertTrue(all(job["currency"] == "EUR" for job in kwargs["body"]))

    @patch("market_data_poc._request_json")
    def test_anonymous_openfigi_uses_conservative_five_job_batches(self, request):
        request.side_effect = [
            [{"data": [{"ticker": f"T{i}"}]} for i in range(5)],
            [{"data": [{"ticker": f"T{i}"}]} for i in range(5, 7)],
        ]
        result = openfigi_map(
            self.targets(),
            None,
            mic_code="XETR",
            currency="EUR",
        )
        self.assertEqual(len(result), 7)
        self.assertEqual(request.call_count, 2)


class AlphaVantageGuardTests(unittest.TestCase):
    def test_default_cli_policy_is_conservative(self):
        args = build_parser().parse_args(["resolve"])
        self.assertEqual(args.pause_seconds, 12.5)
        self.assertEqual(args.av_daily_limit, 25)
        self.assertEqual(args.av_used_last_24h, 0)

    def test_local_daily_budget_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "usage.json"
            guard = AlphaVantageGuard(
                state,
                min_interval_seconds=0,
                daily_limit=2,
                clock=lambda: 1_789_000_000.0,
                sleeper=lambda _: None,
            )
            guard.before_request()
            guard.before_request()
            with self.assertRaisesRegex(ProviderError, "rolling-24h call budget exhausted"):
                guard.before_request()
            saved = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(len(saved["request_epochs"]), 2)
            self.assertNotIn("api", json.dumps(saved).lower())

    def test_seed_is_applied_only_when_state_does_not_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "usage.json"
            clock = lambda: 1_789_000_000.0
            first = AlphaVantageGuard(
                state,
                min_interval_seconds=0,
                daily_limit=25,
                initial_used_last_24h=14,
                clock=clock,
                sleeper=lambda _: None,
            )
            self.assertEqual(first.usage()["request_count"], 14)
            first.before_request()
            self.assertEqual(first.usage()["request_count"], 15)

            second = AlphaVantageGuard(
                state,
                min_interval_seconds=0,
                daily_limit=25,
                initial_used_last_24h=14,
                clock=clock,
                sleeper=lambda _: None,
            )
            self.assertEqual(second.usage()["request_count"], 15)

    def test_spacing_is_enforced_across_guard_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "usage.json"
            now = [1_789_000_000.0]
            sleeps = []

            def clock():
                return now[0]

            def sleeper(seconds):
                sleeps.append(seconds)
                now[0] += seconds

            guard = AlphaVantageGuard(
                state,
                min_interval_seconds=12.5,
                daily_limit=25,
                clock=clock,
                sleeper=sleeper,
            )
            guard.before_request()
            now[0] += 2.0
            guard.before_request()
            self.assertEqual(len(sleeps), 1)
            self.assertAlmostEqual(sleeps[0], 10.5)

    def test_spacing_survives_new_guard_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "usage.json"
            now = [1_789_000_000.0]
            sleeps = []

            def clock():
                return now[0]

            def sleeper(seconds):
                sleeps.append(seconds)
                now[0] += seconds

            first = AlphaVantageGuard(
                state,
                min_interval_seconds=12.5,
                daily_limit=25,
                clock=clock,
                sleeper=sleeper,
            )
            first.before_request()
            now[0] += 3.0

            second = AlphaVantageGuard(
                state,
                min_interval_seconds=12.5,
                daily_limit=25,
                clock=clock,
                sleeper=sleeper,
            )
            second.before_request()
            self.assertEqual(len(sleeps), 1)
            self.assertAlmostEqual(sleeps[0], 9.5)
            self.assertEqual(second.usage()["request_count"], 2)


class MetricTests(unittest.TestCase):
    def bars(self):
        start = date(2026, 9, 9)
        bars = []
        for idx in range(30):
            close = 120.0 - idx
            bars.append(
                DailyBar(
                    day=start - timedelta(days=idx),
                    open=close - 0.5,
                    high=close + 1,
                    low=close - 1,
                    close=close,
                    volume=1000.0,
                )
            )
        return bars

    def test_metrics_use_trading_positions_not_calendar_offsets(self):
        metrics = compute_metrics(self.bars(), today=date(2026, 9, 10))
        self.assertEqual(metrics["as_of"], "2026-09-09")
        self.assertAlmostEqual(metrics["return_5d"], 120 / 115 - 1)
        self.assertAlmostEqual(metrics["return_20d"], 120 / 100 - 1)
        self.assertAlmostEqual(metrics["drawdown_from_20d_high"], 0.0)
        self.assertEqual(metrics["age_calendar_days"], 1)

    def test_insufficient_history_fails_closed(self):
        with self.assertRaisesRegex(Exception, "insufficient_history"):
            compute_metrics(self.bars()[:20])


if __name__ == "__main__":
    unittest.main()
