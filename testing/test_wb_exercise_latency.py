"""
test_wb_exercise_latency.py
════════════════════════════════════════════════════════════════════
WHITE BOX TESTING — generate_exercise_plan()  &  Backend Latency
────────────────────────────────────────────────────────────────────
Techniques : Branch Coverage, Loop Testing, Performance Path Analysis
Run        : pytest test_wb_exercise_latency.py -v
════════════════════════════════════════════════════════════════════
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fixtures"))

import pytest
import time
from mock_backend import (
    generate_exercise_plan,
    adjust_exercise,
    map_activity_level,
    calculate_bmi,
    simulate_sequential_backend,
    SAMPLE_EXERCISES,
)


# ════════════════════════════════════════════════════════════════
#  MODULE 2A — map_activity_level()
# ════════════════════════════════════════════════════════════════
class TestMapActivityLevel:

    @pytest.mark.parametrize("activity,expected", [
        ("sedentary",        "beginner"),
        ("Sedentary",        "beginner"),   # case-insensitive
        ("lightly active",   "beginner"),
        ("moderately active","advanced"),
        ("very active",      "advanced"),
        ("extra active",     "advanced"),
        ("unknown_level",    "beginner"),   # fallback
    ])
    def test_mapping(self, activity, expected):
        assert map_activity_level(activity) == expected, \
            f"'{activity}' should map to '{expected}'"


# ════════════════════════════════════════════════════════════════
#  MODULE 2B — adjust_exercise()  branch coverage
# ════════════════════════════════════════════════════════════════
class TestAdjustExercise:

    def _row(self):
        return {"sets": 3, "repetitions": 12, "duration": 30}

    def test_beginner_reduces_values(self):
        """Sedentary activity → sets/reps/duration multiplied by 0.8."""
        import pandas as pd
        row = pd.Series(self._row())
        result = adjust_exercise(row, "sedentary", "weight loss", 8)
        # After beginner (×0.8) + weight-loss duration (×1.2) + 5–8 weeks (×1.05)
        assert result[0] <= 3, "Beginner sets should be ≤ original"

    def test_advanced_increases_values(self):
        """Very active → sets/reps/duration multiplied by 1.2."""
        import pandas as pd
        row = pd.Series(self._row())
        result = adjust_exercise(row, "very active", "weight gain", 10)
        assert result[1] >= 12, "Advanced reps should be ≥ original"

    def test_short_timeline_boosts_intensity(self):
        """Timeline ≤ 4 weeks applies ×1.1 multiplier."""
        import pandas as pd
        row = pd.Series({"sets": 3, "repetitions": 12, "duration": 30})
        res_short = adjust_exercise(row, "sedentary", "weight loss", 3)   # ≤4 wks
        res_long  = adjust_exercise(row, "sedentary", "weight loss", 12)  # >8 wks
        # Short-timeline value should be higher than long-timeline
        assert res_short[0] >= res_long[0] or res_short[1] >= res_long[1]


# ════════════════════════════════════════════════════════════════
#  MODULE 2C — generate_exercise_plan()
# ════════════════════════════════════════════════════════════════
class TestGenerateExercisePlan:

    @pytest.fixture
    def valid_profile(self):
        return {
            "target_goal":    "weight loss",
            "activity_level": "Sedentary",
            "timeline_weeks": 8,
        }

    # ── PASSING TESTS ─────────────────────────────────────────────
    def test_7_day_plan_returned(self, valid_profile):
        """Plan must contain exactly 7 days."""
        result = generate_exercise_plan(valid_profile, days=7)
        assert len(result) == 7, "Must return 7 days of exercises"

    def test_each_day_has_exercises(self, valid_profile):
        """Each day must have at least 3 exercises."""
        result = generate_exercise_plan(valid_profile, days=7)
        for day, exs in result.items():
            assert len(exs) >= 3, f"{day} must have ≥ 3 exercises"

    def test_each_exercise_has_required_keys(self, valid_profile):
        """Each exercise dict must contain the 4 required keys."""
        result = generate_exercise_plan(valid_profile, days=7)
        required = {"exercise_name", "sets", "repetitions", "duration"}
        for day, exs in result.items():
            for ex in exs:
                assert required.issubset(ex.keys()), \
                    f"{day} exercise missing keys: {required - ex.keys()}"

    def test_beginner_sets_reduced(self, valid_profile):
        """Sedentary (beginner) user gets reduced sets compared to advanced."""
        result_beginner = generate_exercise_plan(valid_profile, days=1)
        advanced_profile = dict(valid_profile, activity_level="Very Active")
        result_advanced  = generate_exercise_plan(advanced_profile, days=1)

        beginner_sets = result_beginner["Day 1"][0]["sets"]
        advanced_sets = result_advanced["Day 1"][0]["sets"]
        assert beginner_sets <= advanced_sets, \
            "Beginner sets must be ≤ advanced sets"

    def test_weight_gain_goal_exercises(self):
        """Weight gain goal must return muscle-building exercises."""
        profile = {"target_goal": "weight gain",
                   "activity_level": "Moderately Active",
                   "timeline_weeks": 12}
        result = generate_exercise_plan(profile, days=7)
        assert "error" not in result, "Weight gain plan must not return error"

    # ── FAILING TEST ───────────────────────────────────────────────
    def test_unrecognised_goal_FAIL(self):
        """
        WB-TC-07 FAILING CASE
        Goal 'body recomposition' is not in exercise.csv.
        Expected: fallback/normalised plan returned.
        Actual  : error dict returned — Flutter shows blank screen.
        """
        profile = {
            "target_goal":    "body recomposition",  # not in dataset
            "activity_level": "Sedentary",
            "timeline_weeks": 8,
        }
        result = generate_exercise_plan(profile, days=7)

        print(f"\n[WB-TC-07] Result for unknown goal: {result}")

        # This assertion FAILS — documents the known bug
        assert "error" not in result, (
            "WB-TC-07 FAIL: Unrecognised goal returns error dict. "
            "Fix: add goal-synonym normalisation map before the filter."
        )

    # ── LOOP TESTS ────────────────────────────────────────────────
    def test_loop_single_day(self, valid_profile):
        """days=1 — loop runs exactly once."""
        result = generate_exercise_plan(valid_profile, days=1)
        assert list(result.keys()) == ["Day 1"]

    def test_loop_three_days(self, valid_profile):
        """days=3 — loop runs three times."""
        result = generate_exercise_plan(valid_profile, days=3)
        assert list(result.keys()) == ["Day 1", "Day 2", "Day 3"]

    def test_loop_full_seven_days(self, valid_profile):
        """days=7 — loop runs seven times (standard usage)."""
        result = generate_exercise_plan(valid_profile, days=7)
        assert len(result) == 7


# ════════════════════════════════════════════════════════════════
#  MODULE 2D — calculate_bmi()  branch coverage
# ════════════════════════════════════════════════════════════════
class TestCalculateBMI:

    @pytest.mark.parametrize("weight,height,expected_label", [
        (35,  5.6, "Underweight"),
        (60,  5.4, "Normal"),
        (80,  5.5, "Overweight"),   # 80kg/5.5ft → BMI ~28.5 = Overweight
        (120, 5.5, "Obese"),
    ])
    def test_bmi_labels(self, weight, height, expected_label):
        result = calculate_bmi(weight, height)
        assert result["label"] == expected_label, \
            f"Weight {weight}kg, Height {height}ft → expected {expected_label}, got {result}"

    def test_bmi_value_accuracy(self):
        """BMI for 60 kg / 5.4 ft — check it falls in Normal range (18.5–25)."""
        result = calculate_bmi(60, 5.4)
        assert 18.0 <= result["bmi"] <= 26.0, \
            f"BMI {result['bmi']} out of expected Normal range for 60kg/5.4ft"

    # ── FAILING TEST ───────────────────────────────────────────────
    def test_zero_weight_FAIL(self):
        """
        BB-TC-03 (also verifiable as white box)
        Zero weight must raise ValueError — not proceed with calculation.
        """
        with pytest.raises(ValueError, match="positive"):
            calculate_bmi(0, 5.4)

    def test_negative_height_FAIL(self):
        """Negative height must raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            calculate_bmi(60, -2.0)


# ════════════════════════════════════════════════════════════════
#  MODULE 3 — Backend Latency  (Performance Path)
# ════════════════════════════════════════════════════════════════
class TestBackendLatency:
    """
    Performance specification from FYP Section 1.2:
    Response time ≤ 2 seconds for AI recommendations.
    """
    SLA_SECONDS = 2.0

    @pytest.fixture
    def test_profile(self):
        return {
            "target_goal":      "weight loss",
            "activity_level":   "Sedentary",
            "timeline_weeks":   8,
            "allergies":        [],
            "health_conditions": [],
            "age": 22, "weight_kg": 60, "height_cm": 164,
            "gender": "Male",
        }

    def test_individual_filter_foods_fast(self, test_profile):
        """filter_foods alone must complete in < 0.5s."""
        from mock_backend import filter_foods, SAMPLE_FOODS
        start  = time.time()
        filter_foods(SAMPLE_FOODS, test_profile)
        elapsed = time.time() - start
        assert elapsed < 0.5, f"filter_foods took {elapsed:.3f}s — too slow"

    def test_individual_exercise_plan_fast(self, test_profile):
        """generate_exercise_plan alone must complete in < 0.5s."""
        start   = time.time()
        generate_exercise_plan(test_profile, days=7)
        elapsed = time.time() - start
        assert elapsed < 0.5, f"Exercise plan took {elapsed:.3f}s — too slow"

    # ── FAILING TEST ───────────────────────────────────────────────
    def test_sequential_backend_SLA_FAIL(self, test_profile):
        """
        WB-TC-08 FAILING CASE
        Sequential model-load + meal-plan + exercise-plan call chain
        exceeds the 2-second SLA defined in performance specifications.

        Real backend: ~2.67s  |  Stripped simulation: still > SLA
        Fix: cache model at startup, parallelise independent calls.
        """
        result  = simulate_sequential_backend(test_profile)
        elapsed = result["elapsed"]

        print(f"\n[WB-TC-08] Sequential backend elapsed: {elapsed:.3f}s")
        print(f"           SLA target: {self.SLA_SECONDS}s")
        print(f"           Status: {'PASS' if elapsed <= self.SLA_SECONDS else 'FAIL'}")

        assert elapsed <= self.SLA_SECONDS, (
            f"WB-TC-08 FAIL: Sequential execution took {elapsed:.3f}s "
            f"— exceeds {self.SLA_SECONDS}s SLA. "
            "Fix: use ThreadPoolExecutor for parallel module calls."
        )
