import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from market_data_poc import DailyBar, Target, compute_metrics, score_av_candidate


class CandidateScoringTests(unittest.TestCase):
    def setUp(self):
        self.target = Target("IE00BJ0KDQ92", "Xtrackers MSCI World UCITS ETF 1C")

    def test_xetra_eur_etf_beats_frankfurt(self):
        xetra = {
            "1. symbol": "XDWD.DEX",
            "2. name": "Xtrackers MSCI World UCITS ETF 1C",
            "3. type": "ETF",
            "4. region": "Germany",
            "8. currency": "EUR",
            "9. matchScore": "0.95",
        }
        frankfurt = {
            "1. symbol": "XDWD.FRA",
            "2. name": "Xtrackers MSCI World UCITS ETF 1C",
            "3. type": "ETF",
            "4. region": "Germany",
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
            "4. region": "Germany",
            "8. currency": "EUR",
            "9. matchScore": "0.90",
        }
        usd = dict(eur)
        usd["8. currency"] = "USD"
        se, _ = score_av_candidate(self.target, eur, {"XDWD"})
        su, _ = score_av_candidate(self.target, usd, {"XDWD"})
        self.assertGreater(se, su)


class MetricTests(unittest.TestCase):
    def bars(self):
        start = date(2026, 9, 9)
        # newest first; oldest close=100, newest close=120
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
