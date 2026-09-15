import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import tactical_persistence_poc as tp


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "persistence_scenarios.json"


def loaded():
    return {h.scenario_id: h for h in tp.load_scenarios(FIXTURE)}


def obs(day, signal=0.5, r20=-0.05, dd=-0.06, *, r5=-0.02, recovered=False, selected=None):
    return tp.CycleObservation(
        cycle_date=date.fromisoformat(day),
        tactical_signal=signal,
        return_5d=r5,
        return_20d=r20,
        drawdown_from_20d_high=dd,
        recovered_since_previous_cycle=recovered,
        selected_by_tt=selected,
        note=None,
    )


def history(frequency, observations, *, scenario_id="test"):
    return tp.TargetHistory(
        scenario_id=scenario_id,
        description="test",
        plan_frequency=frequency,
        isin="IE00BJ0KDQ92",
        name="World",
        observations=tuple(observations),
    )


class QualificationTests(unittest.TestCase):
    def test_material_signal_with_20d_support_qualifies(self):
        item = obs("2026-09-15", signal=0.35, r20=-0.03, dd=-0.01)
        self.assertTrue(item.market_history_support)
        self.assertTrue(item.stress_qualified)

    def test_signal_alone_without_market_history_does_not_qualify(self):
        item = obs("2026-09-15", signal=0.8, r20=-0.01, dd=-0.02)
        self.assertFalse(item.market_history_support)
        self.assertFalse(item.stress_qualified)

    def test_market_history_alone_without_signal_does_not_qualify(self):
        item = obs("2026-09-15", signal=0.2, r20=-0.08, dd=-0.10)
        self.assertTrue(item.market_history_support)
        self.assertFalse(item.stress_qualified)


class CadenceTests(unittest.TestCase):
    def test_same_three_cycle_count_differs_by_frequency(self):
        weekly = history(
            "weekly",
            [obs("2026-09-01"), obs("2026-09-08"), obs("2026-09-15")],
        )
        monthly = history(
            "monthly",
            [obs("2026-07-15"), obs("2026-08-15"), obs("2026-09-15")],
        )
        w = tp.evaluate_history(weekly)
        m = tp.evaluate_history(monthly)
        self.assertEqual(w["final_state"], "tactical_opportunity")
        self.assertEqual(m["final_state"], "strategic_review_due")

    def test_weekly_nine_cycles_over_eight_weeks_review_due(self):
        result = tp.evaluate_history(loaded()["weekly_nine_stressed_cycles"])
        self.assertEqual(result["final_state"], "strategic_review_due")
        self.assertEqual(result["active_episode"]["stressed_planning_cycles"], 9)
        self.assertEqual(result["active_episode"]["elapsed_days"], 56)

    def test_monthly_two_cycles_is_watch(self):
        result = tp.evaluate_history(loaded()["monthly_two_stressed_cycles"])
        self.assertEqual(result["final_state"], "tactical_watch")
        self.assertTrue(result["tactical_bonus_allowed"])

    def test_monthly_three_cycles_is_review_due(self):
        result = tp.evaluate_history(loaded()["monthly_three_stressed_cycles"])
        self.assertEqual(result["final_state"], "strategic_review_due")
        self.assertFalse(result["tactical_bonus_allowed"])

    def test_quarterly_second_persistent_cycle_can_trigger_review(self):
        result = tp.evaluate_history(loaded()["quarterly_two_stressed_cycles"])
        self.assertEqual(result["final_state"], "strategic_review_due")
        self.assertGreaterEqual(result["active_episode"]["elapsed_days"], 75)

    def test_yearly_second_persistent_cycle_can_trigger_review(self):
        result = tp.evaluate_history(loaded()["yearly_two_stressed_cycles"])
        self.assertEqual(result["final_state"], "strategic_review_due")
        self.assertGreaterEqual(result["active_episode"]["elapsed_days"], 330)


class EpisodeTests(unittest.TestCase):
    def test_nonqualified_cycle_closes_episode_and_new_weakness_restarts(self):
        result = tp.evaluate_history(loaded()["monthly_recovery_closes_episode"])
        self.assertEqual(result["closed_episode_count"], 1)
        self.assertEqual(result["active_episode"]["stressed_planning_cycles"], 1)
        self.assertEqual(result["final_state"], "tactical_opportunity")

    def test_between_cycle_recovery_splits_even_if_next_cycle_is_weak(self):
        result = tp.evaluate_history(
            loaded()["monthly_between_cycle_recovery_splits_episode"]
        )
        self.assertEqual(result["closed_episode_count"], 1)
        self.assertEqual(result["active_episode"]["stressed_planning_cycles"], 2)
        self.assertEqual(result["final_state"], "tactical_watch")

    def test_tt_selection_count_does_not_control_persistence(self):
        observations = [
            obs("2026-07-15", selected=False),
            obs("2026-08-15", selected=False),
            obs("2026-09-15", selected=False),
        ]
        result = tp.evaluate_history(history("monthly", observations))
        self.assertEqual(result["final_state"], "strategic_review_due")
        self.assertEqual(result["active_episode"]["selected_by_tt_cycles"], 0)


class GovernanceBoundaryTests(unittest.TestCase):
    def test_review_due_neutralizes_tt_but_never_replaces_or_sells(self):
        result = tp.evaluate_history(loaded()["monthly_three_stressed_cycles"])
        self.assertEqual(result["tactical_bonus_multiplier"], 0.0)
        self.assertTrue(result["human_strategic_review_required"])
        self.assertFalse(result["automatic_target_replacement"])
        self.assertFalse(result["automatic_sell"])

    def test_scenario_loader_rejects_duplicate_cycle_date(self):
        fixture = {
            "schema": 1,
            "scenarios": [
                {
                    "id": "duplicate",
                    "description": "",
                    "plan_frequency": "weekly",
                    "target": {"isin": "IE00BJ0KDQ92", "name": "World"},
                    "observations": [
                        {"cycle_date": "2026-09-15", "tactical_signal": 0.5, "return_5d": -0.02, "return_20d": -0.05, "drawdown_from_20d_high": -0.06},
                        {"cycle_date": "2026-09-15", "tactical_signal": 0.5, "return_5d": -0.02, "return_20d": -0.05, "drawdown_from_20d_high": -0.06}
                    ]
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps(fixture), encoding="utf-8")
            with self.assertRaisesRegex(tp.PersistenceError, "once per PA planning cycle"):
                tp.load_scenarios(path)

    def test_fixture_replay_writes_report_and_preserves_human_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = tp.replay(FIXTURE, Path(tmp))
            self.assertEqual(document["prototype_version"], "0.3.0")
            self.assertFalse(
                document["governance_boundary"]["daily_market_refreshes_increment_state"]
            )
            self.assertTrue(document["governance_boundary"]["human_target_authority"])
            self.assertFalse(
                document["governance_boundary"]["automatic_target_replacement"]
            )
            self.assertTrue((Path(tmp) / "persistence.json").is_file())
            report = (Path(tmp) / "persistence_report.txt").read_text(encoding="utf-8")
            self.assertIn("CADENCE POLICY", report)
            self.assertIn("strategic_review_due", report)


if __name__ == "__main__":
    unittest.main()
