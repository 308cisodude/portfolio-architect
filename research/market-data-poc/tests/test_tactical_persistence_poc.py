import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import tactical_persistence_poc as tp


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "persistence_scenarios.json"
CONTRACT_FIXTURE = ROOT / "examples" / "persistence_contract_events.json"


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


    def test_nonqualified_cycle_without_confirmed_recovery_keeps_episode_unresolved(self):
        observations = [
            obs("2026-07-15", signal=0.55, r20=-0.06, dd=-0.07),
            obs("2026-08-15", signal=0.58, r20=-0.07, dd=-0.08),
            obs("2026-09-15", signal=0.10, r20=0.01, dd=-0.01, recovered=False),
        ]
        result = tp.evaluate_history(history("monthly", observations))
        self.assertEqual(result["closed_episode_count"], 0)
        self.assertEqual(result["active_episode"]["stressed_planning_cycles"], 2)
        self.assertEqual(result["active_episode"]["elapsed_days"], 62)
        self.assertEqual(result["active_episode"]["last_stressed"], "2026-08-15")
        self.assertEqual(result["active_episode"]["last_observed"], "2026-09-15")
        self.assertEqual(result["observations"][-1]["episode_continuity"], "unresolved_nonstress")
        self.assertEqual(result["final_state"], "tactical_watch")

    def test_stress_after_unconfirmed_nonstress_continues_same_episode(self):
        observations = [
            obs("2026-07-15", signal=0.55, r20=-0.06, dd=-0.07),
            obs("2026-08-15", signal=0.10, r20=0.01, dd=-0.01, recovered=False),
            obs("2026-09-15", signal=0.60, r20=-0.08, dd=-0.09, recovered=False),
        ]
        result = tp.evaluate_history(history("monthly", observations))
        self.assertEqual(result["closed_episode_count"], 0)
        self.assertEqual(result["active_episode"]["stressed_planning_cycles"], 2)
        self.assertEqual(result["active_episode"]["started"], "2026-07-15")
        self.assertEqual(result["active_episode"]["last_stressed"], "2026-09-15")
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
            self.assertEqual(document["prototype_version"], "0.4.4")
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


def state_event(
    day,
    *,
    plan_id="plan",
    frequency="monthly",
    target_id="target",
    isin="IE00BJ0KDQ92",
    name="World",
    signal=0.5,
    r5=-0.02,
    r20=-0.05,
    dd=-0.06,
    recovered=False,
    selected=None,
    outcome=None,
    note=None,
):
    return tp.StateCycleEvent(
        plan_id=plan_id,
        cycle_effective_date=date.fromisoformat(day),
        plan_frequency=frequency,
        target_id=target_id,
        isin=isin,
        name=name,
        tactical_signal=signal,
        return_5d=r5,
        return_20d=r20,
        drawdown_from_20d_high=dd,
        recovered_since_previous_cycle=recovered,
        selected_by_tt=selected,
        execution_outcome=outcome,
        note=note,
    )


class StatefulContractTests(unittest.TestCase):
    def test_cycle_identity_is_explicit_and_stable(self):
        event = state_event("2026-09-15", frequency="weekly")
        self.assertEqual(
            event.cycle_identity,
            {
                "plan_id": "plan",
                "cycle_effective_date": "2026-09-15",
                "plan_frequency": "weekly",
                "target_id": "target",
                "isin": "IE00BJ0KDQ92",
            },
        )

    def test_exact_cycle_replay_is_noop(self):
        state = tp.empty_persistence_state()
        event = state_event("2026-09-15")
        self.assertEqual(tp.apply_state_event(state, event), "applied")
        before = json.dumps(state, sort_keys=True)
        self.assertEqual(tp.apply_state_event(state, event), "duplicate_noop")
        self.assertEqual(json.dumps(state, sort_keys=True), before)
        self.assertEqual(len(state["events"]), 1)

    def test_execution_evidence_can_enrich_without_advancing_cycle(self):
        state = tp.empty_persistence_state()
        original = state_event("2026-09-15", selected=True, outcome=None)
        enriched = state_event("2026-09-15", selected=True, outcome="not_followed")
        self.assertEqual(tp.apply_state_event(state, original), "applied")
        self.assertEqual(tp.apply_state_event(state, enriched), "audit_enriched")
        self.assertEqual(len(state["events"]), 1)
        self.assertEqual(state["events"][0]["execution_outcome"], "not_followed")

    def test_conflicting_same_cycle_governance_evidence_is_rejected(self):
        state = tp.empty_persistence_state()
        tp.apply_state_event(state, state_event("2026-09-15", signal=0.5))
        with self.assertRaisesRegex(tp.PersistenceError, "conflicting governance evidence"):
            tp.apply_state_event(state, state_event("2026-09-15", signal=0.7))

    def test_execution_followed_does_not_change_governance_result(self):
        states = []
        for followed in ("followed", "not_followed", "partial"):
            state = tp.empty_persistence_state()
            for day in ("2026-07-15", "2026-08-15", "2026-09-15"):
                tp.apply_state_event(
                    state, state_event(day, outcome=followed, selected=True)
                )
            states.append(tp.evaluate_persistence_state(state))
        baseline = states[0]["roles"][0]
        for document in states[1:]:
            role = document["roles"][0]
            self.assertEqual(baseline["final_state"], role["final_state"])
            self.assertEqual(
                baseline["segments"][0]["active_episode"],
                role["segments"][0]["active_episode"],
            )

    def test_contract_forbids_tactical_debt(self):
        state = tp.empty_persistence_state()
        tp.apply_state_event(state, state_event("2026-09-15", outcome="not_followed"))
        document = tp.evaluate_persistence_state(state)
        contract = document["contract"]
        self.assertFalse(contract["unexecuted_recommendation_creates_tactical_debt"])
        self.assertTrue(contract["next_cycle_scoring_uses_current_authoritative_holdings"])
        self.assertNotIn("tactical_debt", state)

    def test_cadence_change_keeps_old_segment_without_reinterpreting_it(self):
        state = tp.empty_persistence_state()
        tp.apply_state_event(state, state_event("2026-06-15", frequency="monthly"))
        tp.apply_state_event(state, state_event("2026-07-15", frequency="monthly"))
        tp.apply_state_event(state, state_event("2026-09-15", frequency="weekly"))
        role = tp.evaluate_persistence_state(state)["roles"][0]
        self.assertEqual(role["segment_count"], 2)
        self.assertEqual(role["segments"][0]["terminated_by"], "plan_frequency_changed")
        self.assertEqual(role["segments"][0]["final_state"], "tactical_watch")
        self.assertEqual(role["final_state"], "tactical_opportunity")

    def test_target_replacement_starts_clean_asset_segment(self):
        state = tp.empty_persistence_state()
        tp.apply_state_event(state, state_event("2026-07-15", isin="IE00BYZK4552"))
        tp.apply_state_event(state, state_event("2026-08-15", isin="IE00BYZK4552"))
        tp.apply_state_event(state, state_event("2026-09-15", isin="IE00BYZK4776"))
        role = tp.evaluate_persistence_state(state)["roles"][0]
        self.assertEqual(role["segment_count"], 2)
        self.assertEqual(role["segments"][0]["terminated_by"], "target_replaced")
        self.assertEqual(role["active_target"]["isin"], "IE00BYZK4776")
        self.assertEqual(role["final_state"], "tactical_opportunity")
        self.assertEqual(
            role["segments"][1]["active_episode"]["stressed_planning_cycles"], 1
        )

    def test_state_save_reload_and_batch_replay_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            output = Path(tmp) / "out"
            first, counts1 = tp.state_replay(CONTRACT_FIXTURE, state_path, output)
            state_bytes = state_path.read_bytes()
            second, counts2 = tp.state_replay(CONTRACT_FIXTURE, state_path, output)
            self.assertEqual(state_path.read_bytes(), state_bytes)
            self.assertEqual(first, second)
            self.assertEqual(counts1["applied"], 9)
            self.assertEqual(counts1["audit_enriched"], 1)
            self.assertEqual(counts1["duplicate_noop"], 1)
            self.assertEqual(counts2["applied"], 0)
            self.assertEqual(counts2["audit_enriched"], 0)
            self.assertEqual(counts2["duplicate_noop"], 11)

    def test_contract_fixture_exercises_review_cadence_and_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            document, _ = tp.state_replay(CONTRACT_FIXTURE, state_path, Path(tmp))
            roles = {(r["plan_id"], r["target_id"]): r for r in document["roles"]}
            self.assertEqual(
                roles[("plan_monthly_demo", "target_cybersecurity")]["final_state"],
                "strategic_review_due",
            )
            self.assertEqual(
                roles[("plan_cadence_change", "target_world")]["segment_count"], 2
            )
            self.assertEqual(
                roles[("plan_target_replacement", "target_thematic_role")]["segment_count"],
                2,
            )
            report = (Path(tmp) / "persistence_contract_report.txt").read_text(
                encoding="utf-8"
            )
            self.assertIn("no tactical debt", report)
            self.assertIn("target_replaced", report)


if __name__ == "__main__":
    unittest.main()
