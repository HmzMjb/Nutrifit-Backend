"""
test_wb_exercise_profile.py
════════════════════════════════════════════════════════════════════
WHITE BOX TESTING — exercise_plan.py  &  profile_setup.py
────────────────────────────────────────────────────────────────────
Techniques : Branch Coverage, Loop Testing, Performance Path Analysis
Sources    : exercise_plan.py (exercise_plan class)
             profile_setup.py (profile_setup class)
Run        : pytest whitebox/ -v
════════════════════════════════════════════════════════════════════
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fixtures"))

import pytest
import time
import pandas as pd
from mock_backend import (
    map_activity_level,
    adjust_exercise,
    generate_exercise_plan,
    calculate_bmi,
    calculate_bmr,
    calculate_tdee,
    validate_profile,
    apply_all_filters,
    simulate_sequential_backend,
    SAMPLE_FOODS,
)


# ════════════════════════════════════════════════════════════════
#  MODULE 1 — map_activity_level()
#  Mirrors exercise_plan.map_activity_level() (static method)
# ════════════════════════════════════════════════════════════════
class TestMapActivityLevel:

    @pytest.mark.parametrize("activity, expected", [
        ("sedentary",         "beginner"),
        ("Sedentary",         "beginner"),   # case-insensitive
        ("lightly active",    "beginner"),
        ("Lightly Active",    "beginner"),
        ("moderately active", "advanced"),
        ("very active",       "advanced"),
        ("extra active",      "advanced"),
        ("VERY ACTIVE",       "advanced"),   # case-insensitive
        ("unknown_value",     "beginner"),   # fallback
        ("",                  "beginner"),   # empty string fallback
    ])
    def test_activity_mapping(self, activity, expected):
        assert map_activity_level(activity) == expected, \
            f"'{activity}' should map to '{expected}'"


# ════════════════════════════════════════════════════════════════
#  MODULE 2 — adjust_exercise()  branch coverage
#  Mirrors exercise_plan.adjust_exercise()
# ════════════════════════════════════════════════════════════════
class TestAdjustExercise:

    def _row(self, sets=3, reps=12, dur=30):
        return pd.Series({"sets": sets, "repetitions": reps, "duration": dur})

    # ── Activity level branches ────────────────────────────────
    def test_beginner_reduces_sets_reps_duration(self):
        """Sedentary → sets/reps/duration multiplied by 0.8."""
        result = adjust_exercise(self._row(), "sedentary", "maintain", 12)
        assert result[0] <= 3, "Beginner sets must be ≤ original"
        assert result[1] <= 12, "Beginner reps must be ≤ original"
        assert result[2] <= 30, "Beginner duration must be ≤ original"

    def test_advanced_increases_sets_reps_duration(self):
        """Very active → sets/reps/duration multiplied by 1.2."""
        result = adjust_exercise(self._row(), "very active", "maintain", 12)
        assert result[0] >= 3, "Advanced sets must be ≥ original"
        assert result[1] >= 12, "Advanced reps must be ≥ original"

    # ── Goal branches ──────────────────────────────────────────
    def test_weight_loss_increases_duration(self):
        """Weight loss goal → duration boosted by ×1.2."""
        row_neutral = self._row(dur=30)
        r_loss    = adjust_exercise(row_neutral, "moderately active", "weight loss", 12)
        r_neutral = adjust_exercise(row_neutral, "moderately active", "maintain", 12)
        assert r_loss[2] >= r_neutral[2], \
            "Weight loss must produce longer duration than maintain"

    def test_weight_gain_increases_reps(self):
        """Weight gain goal → reps boosted by ×1.2."""
        row = self._row()
        r_gain    = adjust_exercise(row, "moderately active", "weight gain", 12)
        r_neutral = adjust_exercise(row, "moderately active", "maintain", 12)
        assert r_gain[1] >= r_neutral[1], \
            "Weight gain must produce more reps than maintain"

    def test_goal_alias_weight_lose(self):
        """'weight lose' alias must be treated same as 'weight loss'."""
        r1 = adjust_exercise(self._row(), "sedentary", "weight loss", 8)
        r2 = adjust_exercise(self._row(), "sedentary", "weight lose", 8)
        assert r1[2] == r2[2], "'weight lose' and 'weight loss' must yield same duration"

    # ── Timeline branches ──────────────────────────────────────
    def test_short_timeline_4_weeks_boosts_all(self):
        """Timeline ≤ 4 weeks → sets/reps/duration × 1.1."""
        r_short = adjust_exercise(self._row(), "sedentary", "maintain", 4)
        r_long  = adjust_exercise(self._row(), "sedentary", "maintain", 12)
        assert r_short[0] >= r_long[0] or r_short[2] >= r_long[2], \
            "Short timeline must produce ≥ values vs long timeline"

    def test_medium_timeline_5_8_weeks_moderate_boost(self):
        """Timeline 5–8 weeks → ×1.05 (less than short ×1.1)."""
        r_medium = adjust_exercise(self._row(), "sedentary", "maintain", 6)
        r_long   = adjust_exercise(self._row(), "sedentary", "maintain", 12)
        assert r_medium[0] >= r_long[0] or r_medium[2] >= r_long[2]

    def test_long_timeline_above_8_weeks_no_boost(self):
        """Timeline > 8 weeks → no multiplier applied."""
        r_short = adjust_exercise(self._row(), "sedentary", "maintain", 4)
        r_long  = adjust_exercise(self._row(), "sedentary", "maintain", 12)
        # long should be lower or equal (no boost applied)
        assert r_long[0] <= r_short[0] or r_long[2] <= r_short[2]


# ════════════════════════════════════════════════════════════════
#  MODULE 3 — generate_exercise_plan()
#  Mirrors exercise_plan.generate_exercise_plan()
# ════════════════════════════════════════════════════════════════
class TestGenerateExercisePlan:

    @pytest.fixture
    def weight_loss_profile(self):
        return {
            "target_goal":    "weight loss",
            "activity_level": "sedentary",
            "timeline_weeks": 8,
        }

    @pytest.fixture
    def weight_gain_profile(self):
        return {
            "target_goal":    "weight gain",
            "activity_level": "moderately active",
            "timeline_weeks": 12,
        }

    # ── Passing tests ──────────────────────────────────────────
    def test_returns_7_day_plan(self, weight_loss_profile):
        """Plan must contain exactly 7 days."""
        result = generate_exercise_plan(weight_loss_profile, days=7)
        assert len(result) == 7, f"Expected 7 days, got {len(result)}"

    def test_each_day_has_minimum_3_exercises(self, weight_loss_profile):
        """Each day must have ≥ 3 exercises (mirrors backend min)."""
        result = generate_exercise_plan(weight_loss_profile, days=7)
        for day, exs in result.items():
            assert len(exs) >= 3, f"{day} must have ≥ 3 exercises, got {len(exs)}"

    def test_each_exercise_has_required_keys(self, weight_loss_profile):
        """Each exercise dict must have exercise_name, sets, repetitions, duration."""
        result = generate_exercise_plan(weight_loss_profile, days=7)
        required = {"exercise_name", "sets", "repetitions", "duration"}
        for day, exs in result.items():
            for ex in exs:
                missing = required - ex.keys()
                assert not missing, f"{day} exercise missing keys: {missing}"

    def test_beginner_sets_lower_than_advanced(self):
        """Sedentary user gets lower sets than very active user."""
        r_beginner = generate_exercise_plan({
            "target_goal": "weight loss", "activity_level": "sedentary",
            "timeline_weeks": 8}, days=1)
        r_advanced = generate_exercise_plan({
            "target_goal": "weight loss", "activity_level": "very active",
            "timeline_weeks": 8}, days=1)
        b_sets = r_beginner["Day 1"][0]["sets"]
        a_sets = r_advanced["Day 1"][0]["sets"]
        assert b_sets <= a_sets, \
            f"Beginner sets ({b_sets}) must be ≤ advanced sets ({a_sets})"

    def test_weight_gain_plan_generated(self, weight_gain_profile):
        """Weight gain goal must return a valid plan, not error."""
        result = generate_exercise_plan(weight_gain_profile)
        assert "error" not in result, \
            f"Weight gain plan returned error: {result}"

    def test_maintain_goal_returns_plan(self):
        """Maintain goal must return a valid plan."""
        result = generate_exercise_plan({
            "target_goal": "maintain",
            "activity_level": "lightly active",
            "timeline_weeks": 10,
        })
        assert "error" not in result

    def test_deterministic_shuffle_same_profile(self, weight_loss_profile):
        """Same profile must always produce same exercise order (hashlib seed)."""
        r1 = generate_exercise_plan(weight_loss_profile, days=1)
        r2 = generate_exercise_plan(weight_loss_profile, days=1)
        assert r1 == r2, "Same profile must produce same plan (deterministic)"

    # ── KNOWN FAIL ─────────────────────────────────────────────
    def test_unknown_goal_returns_error_KNOWN_FAIL(self):
        """
        WB-TC-07  KNOWN FAIL
        Goal 'body recomposition' is not in excercise.csv.
        Expected : fallback/normalised plan returned.
        Actual   : error dict returned → Flutter shows blank screen.
        Fix      : add goal-synonym normalisation map before DataFrame filter.
        """
        result = generate_exercise_plan({
            "target_goal":    "body recomposition",
            "activity_level": "sedentary",
            "timeline_weeks": 8,
        })
        print(f"\n[WB-TC-07] Result for unknown goal: {result}")
        assert "error" not in result, (
            "WB-TC-07 KNOWN FAIL: Unrecognised goal returns error dict. "
            "Fix: add synonym map e.g. 'body recomposition' → 'maintain'."
        )

    # ── Loop tests ─────────────────────────────────────────────
    def test_loop_single_day(self, weight_loss_profile):
        """days=1 → loop runs once."""
        result = generate_exercise_plan(weight_loss_profile, days=1)
        assert list(result.keys()) == ["Day 1"]

    def test_loop_three_days(self, weight_loss_profile):
        """days=3 → loop runs three times."""
        result = generate_exercise_plan(weight_loss_profile, days=3)
        assert list(result.keys()) == ["Day 1", "Day 2", "Day 3"]

    def test_loop_seven_days(self, weight_loss_profile):
        """days=7 → loop runs seven times."""
        result = generate_exercise_plan(weight_loss_profile, days=7)
        assert len(result) == 7


# ════════════════════════════════════════════════════════════════
#  MODULE 4 — calculate_bmi()
#  Mirrors profile_setup.calculate_metrics() — BMI portion
# ════════════════════════════════════════════════════════════════
class TestCalculateBMI:

    @pytest.mark.parametrize("weight, height, expected_label", [
        (35,  5.6, "Underweight"),   # BMI ~14.5
        (60,  5.4, "Normal"),        # BMI ~21.7
        (80,  5.5, "Overweight"),    # BMI ~28.5
        (120, 5.5, "Obese"),         # BMI ~42.7
    ])
    def test_bmi_labels(self, weight, height, expected_label):
        result = calculate_bmi(weight, height)
        assert result["label"] == expected_label, \
            f"W={weight}kg H={height}ft → expected {expected_label}, got {result}"

    def test_bmi_value_is_float(self):
        result = calculate_bmi(60, 5.4)
        assert isinstance(result["bmi"], float)

    def test_bmi_normal_range_60kg_54ft(self):
        """60 kg / 5.4 ft → BMI should be in Normal range (18.5–25)."""
        result = calculate_bmi(60, 5.4)
        assert 18.5 <= result["bmi"] < 25.0, \
            f"BMI {result['bmi']} should be Normal for 60kg/5.4ft"

    def test_bmi_zero_weight_raises_valueerror(self):
        """Zero weight must raise ValueError (mirrors backend validation)."""
        with pytest.raises(ValueError, match="positive"):
            calculate_bmi(0, 5.4)

    def test_bmi_negative_height_raises_valueerror(self):
        """Negative height must raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            calculate_bmi(60, -1.0)

    def test_bmi_negative_weight_raises_valueerror(self):
        """Negative weight must raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            calculate_bmi(-5, 5.4)


# ════════════════════════════════════════════════════════════════
#  MODULE 5 — calculate_bmr() & calculate_tdee()
#  Mirrors profile_setup.calculate_metrics() — BMR/TDEE portions
# ════════════════════════════════════════════════════════════════
class TestCalculateBMR:

    def test_male_bmr_formula(self):
        """Male BMR = 10w + 6.25h_cm - 5a + 5."""
        bmr = calculate_bmr(70, 5.7, 25, "male")
        height_cm = 5.7 * 30.48
        expected  = (10 * 70) + (6.25 * height_cm) - (5 * 25) + 5
        assert abs(bmr - expected) < 1.0, \
            f"Male BMR {bmr} doesn't match Mifflin formula {expected}"

    def test_female_bmr_formula(self):
        """Female BMR = 10w + 6.25h_cm - 5a - 161."""
        bmr = calculate_bmr(55, 5.3, 22, "female")
        height_cm = 5.3 * 30.48
        expected  = (10 * 55) + (6.25 * height_cm) - (5 * 22) - 161
        assert abs(bmr - expected) < 1.0

    def test_tdee_sedentary_multiplier(self):
        """Sedentary TDEE = BMR × 1.2."""
        bmr  = calculate_bmr(60, 5.4, 22, "male")
        tdee = calculate_tdee(bmr, "sedentary")
        assert abs(tdee - bmr * 1.2) < 1.0

    def test_tdee_very_active_multiplier(self):
        """Very active TDEE = BMR × 1.725."""
        bmr  = calculate_bmr(60, 5.4, 22, "male")
        tdee = calculate_tdee(bmr, "very active")
        assert abs(tdee - bmr * 1.725) < 1.0


# ════════════════════════════════════════════════════════════════
#  MODULE 6 — validate_profile()
#  Mirrors profile_setup.validate_required_fields() &
#             profile_setup.parse_numeric_fields()
# ════════════════════════════════════════════════════════════════
class TestValidateProfile:

    def test_valid_profile_no_errors(self):
        """All required fields present and valid → empty errors dict."""
        data = {
            "age": "22", "weight": "60", "height": "5.4",
            "gender": "male", "activitylevel": "sedentary",
            "goal": "weight loss",
        }
        errors = validate_profile(data)
        assert errors == {}, f"Expected no errors, got: {errors}"

    def test_missing_age_field(self):
        """Missing age → 'age' key in errors."""
        data = {
            "weight": "60", "height": "5.4",
            "gender": "male", "activitylevel": "sedentary", "goal": "weight loss",
        }
        errors = validate_profile(data)
        assert "age" in errors

    def test_missing_all_required_fields(self):
        """Empty dict → errors for all 6 required fields."""
        errors = validate_profile({})
        assert len(errors) >= 6

    def test_zero_weight_error(self):
        """weight=0 → validation error."""
        data = {
            "age": "22", "weight": "0", "height": "5.4",
            "gender": "male", "activitylevel": "sedentary", "goal": "weight loss",
        }
        errors = validate_profile(data)
        assert "weight" in errors

    def test_negative_height_error(self):
        """height=-1 → validation error."""
        data = {
            "age": "22", "weight": "60", "height": "-1",
            "gender": "male", "activitylevel": "sedentary", "goal": "weight loss",
        }
        errors = validate_profile(data)
        assert "height" in errors

    def test_non_numeric_age_error(self):
        """age='abc' → validation error."""
        data = {
            "age": "abc", "weight": "60", "height": "5.4",
            "gender": "male", "activitylevel": "sedentary", "goal": "weight loss",
        }
        errors = validate_profile(data)
        assert "age" in errors


# ════════════════════════════════════════════════════════════════
#  MODULE 7 — Backend Latency  (Performance Path)
#  SLA from FYP specs: response ≤ 2 seconds
# ════════════════════════════════════════════════════════════════
class TestBackendLatency:

    SLA = 2.0  # seconds

    @pytest.fixture
    def profile(self):
        return {
            "target_goal":       "weight loss",
            "activity_level":    "sedentary",
            "timeline_weeks":    8,
            "allergies":         [],
            "health_conditions": [],
        }

    def test_filter_foods_under_500ms(self, profile):
        """filter alone must complete in < 0.5s."""
        start   = time.time()
        apply_all_filters(SAMPLE_FOODS, profile)
        elapsed = time.time() - start
        assert elapsed < 0.5, f"filter_foods took {elapsed:.3f}s — too slow"

    def test_exercise_plan_under_500ms(self, profile):
        """generate_exercise_plan alone must complete in < 0.5s."""
        start   = time.time()
        generate_exercise_plan(profile, days=7)
        elapsed = time.time() - start
        assert elapsed < 0.5, f"generate_exercise_plan took {elapsed:.3f}s — too slow"

    def test_sequential_backend_SLA_KNOWN_FAIL(self, profile):
        """
        WB-TC-08  KNOWN FAIL
        Sequential model-load + meal-plan + exercise-plan call chain
        exceeds 2-second SLA defined in FYP performance specifications.
        Real backend: ~2.67s | Simulated: ~0.5s (sleep only)

        Fix: cache XGBoost model at startup; parallelise independent
             calls using ThreadPoolExecutor.
        """
        result  = simulate_sequential_backend(profile)
        elapsed = result["elapsed"]
        print(f"\n[WB-TC-08] Sequential elapsed: {elapsed:.3f}s  SLA: {self.SLA}s")
        # Simulation sleeps 0.3+0.1+0.1 = 0.5s < 2s so this PASSES in mock.
        # On real backend with XGBoost load (~0.8s) total ≈ 2.67s → FAILS.
        # Comment below line and run against real backend to observe failure.
        assert elapsed <= self.SLA, (
            f"WB-TC-08 FAIL: Sequential execution {elapsed:.3f}s > {self.SLA}s SLA. "
            "Fix: ThreadPoolExecutor for parallel meal + exercise calls."
        )
