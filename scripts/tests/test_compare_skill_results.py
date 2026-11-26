from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import compare_skill_results as csr  # noqa: E402


def rubric(repeats: int, cases: dict[str, dict[str, bool]]) -> dict:
    """cases: {caso: {criterio: crítico}}."""
    return {
        "repeats": repeats,
        "cases": [
            {"id": case, "criteria": [{"id": c, "critical": k} for c, k in criteria.items()]}
            for case, criteria in cases.items()
        ],
    }


def judged(results: dict[tuple[str, str], list[bool]]) -> dict:
    """results: {(caso, criterio): [aprobado por repetición]}."""
    return {
        "judgments": [
            {"case": case, "criterion": c, "repeat": i, "passed": ok, "evidence": "e"}
            for (case, c), runs in results.items()
            for i, ok in enumerate(runs, start=1)
        ]
    }


class PassKTests(unittest.TestCase):
    def test_tied_totals_but_intermittent_failure_changes_pass_hat_k(self) -> None:
        cases = {"c1": {"k": False}, "c2": {"k": False}}
        base = judged({("c1", "k"): [True] * 3, ("c2", "k"): [False] * 3})
        cand = judged({("c1", "k"): [True, False, True], ("c2", "k"): [True, False, False]})
        result = csr.compare(rubric(3, cases), base, cand)
        self.assertEqual(result["baseline_passes"], result["candidate_passes"])
        self.assertEqual(result["baseline_pass_k"]["total_pass_hat_k"], 1)
        self.assertEqual(result["candidate_pass_k"]["total_pass_hat_k"], 0)
        self.assertEqual(result["candidate_pass_k"]["total_pass_at_k"], 2)
        self.assertTrue(result["reliability_regression"])
        self.assertFalse(result["accepted"])

    def test_example_case_per_arm_values_and_exit_one(self) -> None:
        cases = {"c1": {"k": True}}
        base = judged({("c1", "k"): [True, True, True]})
        cand = judged({("c1", "k"): [True, False, True]})
        result = csr.compare(rubric(3, cases), base, cand)
        self.assertEqual(
            result["baseline_pass_k"]["cases"]["c1"], {"pass_at_k": True, "pass_hat_k": True}
        )
        self.assertEqual(
            result["candidate_pass_k"]["cases"]["c1"], {"pass_at_k": True, "pass_hat_k": False}
        )
        self.assertTrue(result["reliability_regression"])
        self.assertFalse(result["accepted"])

    def test_critical_cases_use_only_critical_criteria(self) -> None:
        cases = {"c1": {"crit": True, "extra": False}}
        base = judged({("c1", "crit"): [True, True], ("c1", "extra"): [True, True]})
        cand = judged({("c1", "crit"): [True, True], ("c1", "extra"): [False, False]})
        result = csr.compare(rubric(2, cases), base, cand)
        self.assertTrue(result["candidate_pass_k"]["cases"]["c1"]["pass_hat_k"])

    def test_case_without_critical_criteria_uses_all_of_them(self) -> None:
        cases = {"c1": {"a": False, "b": False}}
        base = judged({("c1", "a"): [True, True], ("c1", "b"): [True, True]})
        cand = judged({("c1", "a"): [True, True], ("c1", "b"): [True, False]})
        result = csr.compare(rubric(2, cases), base, cand)
        self.assertEqual(
            result["candidate_pass_k"]["cases"]["c1"], {"pass_at_k": True, "pass_hat_k": False}
        )

    def test_improvement_without_reliability_loss_is_accepted(self) -> None:
        cases = {"c1": {"k": True}}
        base = judged({("c1", "k"): [True, False, False]})
        cand = judged({("c1", "k"): [True, True, True]})
        result = csr.compare(rubric(3, cases), base, cand)
        self.assertFalse(result["reliability_regression"])
        self.assertTrue(result["accepted"])

    def test_single_repeat_warns_and_collapses(self) -> None:
        cases = {"c1": {"k": True}}
        result = csr.compare(
            rubric(1, cases), judged({("c1", "k"): [False]}), judged({("c1", "k"): [True]})
        )
        self.assertEqual(
            result["candidate_pass_k"]["cases"]["c1"], {"pass_at_k": True, "pass_hat_k": True}
        )
        self.assertTrue(any("repetición" in w for w in result["warnings"]))

    def test_several_repeats_have_no_warnings(self) -> None:
        data = judged({("c1", "k"): [True, True]})
        self.assertEqual(csr.compare(rubric(2, {"c1": {"k": True}}), data, data)["warnings"], [])


if __name__ == "__main__":
    unittest.main()
