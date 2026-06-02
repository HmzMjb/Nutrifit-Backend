import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fixtures"))

import pytest
import time
from datetime import datetime, timedelta
from mock_backend import (
    calculate_bmi,
    calculate_bmr,
    calculate_tdee,
    validate_profile,
    SAMPLE_FOODS,
    apply_all_filters,
    simulate_sequential_backend,
)

#  MODULE 1 — calculate_bmi()

class TestCalculateBMI:
    """
    McCabe Cyclomatic Complexity V(G) = 5 (4 label branches + 2 guard clauses).
    Paths:
      P1 weight <= 0  → error
      P2 height <= 0  → error
      P3 bmi < 18.5   → Underweight
      P4 bmi < 25     → Normal
      P5 bmi < 30     → Overweight
      P6 bmi >= 30    → Obese
    """

    @pytest.mark.parametrize("weight, height, expected_label", [
        (35,  5.6, "Underweight"),  # P3 — BMI ≈ 14.5
        (60,  5.4, "Normal"),       # P4 — BMI ≈ 21.7
        (80,  5.5, "Overweight"),   # P5 — BMI ≈ 28.5
        (120, 5.5, "Obese"),        # P6 — BMI ≈ 42.7
    ])
    def test_bmi_label_branches(self, weight, height, expected_label):
        """P3-P6: All four label branches must produce the correct category."""
        result = calculate_bmi(weight, height)
        assert result["label"] == expected_label, (
            f"W={weight}kg H={height}ft → expected '{expected_label}', got '{result}'"
        )

    def test_bmi_value_is_numeric(self):
        """BMI output must be a numeric float, not a string or None."""
        result = calculate_bmi(60, 5.4)
        assert isinstance(result["bmi"], float)

    def test_bmi_normal_range_boundary_lower(self):
        """Boundary: BMI just above 18.5 (lower Normal boundary) → Normal."""
        result = calculate_bmi(47, 5.4)   # BMI ≈ 18.9
        assert result["label"] == "Normal", (
            f"BMI {result['bmi']:.2f} should fall in Normal range"
        )

    def test_bmi_overweight_boundary(self):
        """Boundary: BMI just below 30 (upper Overweight boundary) → Overweight."""
        result = calculate_bmi(83, 5.5)   # BMI ≈ 29.5
        assert result["label"] == "Overweight"

    # ── Guard-clause branches (P1, P2) ────────────────────────────
    def test_zero_weight_returns_error(self):
        """P1: weight=0 must return an error dict (guard clause)."""
        result = calculate_bmi(0, 5.4)
        assert "error" in result, "Zero weight must produce an error response"

    def test_negative_weight_returns_error(self):
        """P1: negative weight must return an error dict."""
        result = calculate_bmi(-10, 5.4)
        assert "error" in result

    def test_negative_height_returns_error(self):
        """P2: negative height must return an error dict."""
        result = calculate_bmi(60, -1.0)
        assert "error" in result

    def test_zero_height_returns_error(self):
        """P2: height=0 must return an error dict."""
        result = calculate_bmi(60, 0)
        assert "error" in result


#  MODULE 2 — calculate_bmr()  &  calculate_tdee(
class TestCalculateBMR:
    """
    Two gender branches in BMR formula, five activity multiplier branches.
    """

    # ── Gender branch coverage ─────────────────────────────────────
    def test_male_bmr_mifflin_formula(self):
        """Male BMR = 10w + 6.25*h_cm - 5*age + 5."""
        bmr = calculate_bmr(70, 5.7, 25, "male")
        height_cm = 5.7 * 30.48
        expected = (10 * 70) + (6.25 * height_cm) - (5 * 25) + 5
        assert abs(bmr - expected) < 1.0, (
            f"Male BMR {bmr:.1f} doesn't match Mifflin formula {expected:.1f}"
        )

    def test_female_bmr_mifflin_formula(self):
        """Female BMR = 10w + 6.25*h_cm - 5*age - 161."""
        bmr = calculate_bmr(55, 5.3, 22, "female")
        height_cm = 5.3 * 30.48
        expected = (10 * 55) + (6.25 * height_cm) - (5 * 22) - 161
        assert abs(bmr - expected) < 1.0

    def test_male_bmr_higher_than_female_same_stats(self):
        """Male BMR must always exceed female BMR for identical body stats."""
        bmr_m = calculate_bmr(70, 5.7, 30, "male")
        bmr_f = calculate_bmr(70, 5.7, 30, "female")
        assert bmr_m > bmr_f, (
            "Male BMR should be 166 units higher than female (constant offset)"
        )

    def test_case_insensitive_gender(self):
        """Gender matching must be case-insensitive ('Male' == 'male')."""
        bmr_lower = calculate_bmr(70, 5.7, 25, "male")
        bmr_upper = calculate_bmr(70, 5.7, 25, "Male")
        assert abs(bmr_lower - bmr_upper) < 0.01

    # ── TDEE activity multiplier branches ─────────────────────────
    @pytest.mark.parametrize("activity, multiplier", [
        ("sedentary",         1.2),
        ("lightly active",    1.375),
        ("moderately active", 1.55),
        ("very active",       1.725),
        ("extra active",      1.9),
    ])
    def test_tdee_multiplier_branches(self, activity, multiplier):
        """Each activity level must apply the correct TDEE multiplier."""
        bmr  = calculate_bmr(70, 5.7, 25, "male")
        tdee = calculate_tdee(bmr, activity)
        expected = bmr * multiplier
        assert abs(tdee - expected) < 1.0, (
            f"TDEE for '{activity}' {tdee:.1f} ≠ expected {expected:.1f}"
        )

    def test_tdee_unknown_activity_falls_back_to_sedentary(self):
        """Unknown activity level should fall back to sedentary multiplier (1.2)."""
        bmr  = calculate_bmr(70, 5.7, 25, "male")
        tdee = calculate_tdee(bmr, "alien_activity")
        assert abs(tdee - bmr * 1.2) < 1.0

    def test_tdee_greater_than_bmr(self):
        """TDEE must always be greater than BMR (multiplier > 1.0)."""
        bmr  = calculate_bmr(60, 5.4, 22, "female")
        tdee = calculate_tdee(bmr, "sedentary")
        assert tdee > bmr

#  MODULE 3 — validate_profile()
class TestValidateProfile:
    """
    Branch coverage for required-field presence checks and numeric guards.
    McCabe V(G) = 7 (6 required-field checks + numeric guards).
    """

    def _valid_data(self):
        return {
            "age": "22", "weight": "60", "height": "5.4",
            "gender": "male", "activitylevel": "sedentary",
            "goal": "weight loss",
        }

    def test_valid_profile_returns_no_errors(self):
        """All required fields present and valid → empty errors dict."""
        errors = validate_profile(self._valid_data())
        assert errors == {}, f"Expected no errors, got: {errors}"

    # ── Required-field missing branches ───────────────────────────
    @pytest.mark.parametrize("missing_field", [
        "age", "weight", "height", "gender", "activitylevel", "goal"
    ])
    def test_each_required_field_missing(self, missing_field):
        """Missing any single required field must produce an error for that field."""
        data = self._valid_data()
        del data[missing_field]
        errors = validate_profile(data)
        assert missing_field in errors, (
            f"Missing '{missing_field}' must appear in errors"
        )

    def test_empty_dict_reports_all_six_fields(self):
        """Completely empty input must produce errors for all 6 required fields."""
        errors = validate_profile({})
        assert len(errors) >= 6, f"Expected 6 errors, got {len(errors)}: {errors}"

    def test_none_value_treated_as_missing(self):
        """Field present but set to None must be treated as missing."""
        data = self._valid_data()
        data["age"] = None
        errors = validate_profile(data)
        assert "age" in errors

    def test_empty_string_treated_as_missing(self):
        """Field present but set to '' must be treated as missing."""
        data = self._valid_data()
        data["gender"] = ""
        errors = validate_profile(data)
        assert "gender" in errors

    # ── Numeric guard branches ─────────────────────────────────────
    def test_zero_age_produces_error(self):
        """age=0 must trigger age > 0 validation."""
        data = {**self._valid_data(), "age": "0"}
        errors = validate_profile(data)
        assert "age" in errors

    def test_negative_age_produces_error(self):
        data = {**self._valid_data(), "age": "-5"}
        errors = validate_profile(data)
        assert "age" in errors

    def test_non_numeric_age_produces_error(self):
        """age='abc' → cannot convert → validation error."""
        data = {**self._valid_data(), "age": "abc"}
        errors = validate_profile(data)
        assert "age" in errors

    def test_zero_weight_produces_error(self):
        """weight=0 must trigger weight > 0 validation."""
        data = {**self._valid_data(), "weight": "0"}
        errors = validate_profile(data)
        assert "weight" in errors

    def test_negative_weight_produces_error(self):
        data = {**self._valid_data(), "weight": "-20"}
        errors = validate_profile(data)
        assert "weight" in errors

    def test_non_numeric_weight_produces_error(self):
        data = {**self._valid_data(), "weight": "heavy"}
        errors = validate_profile(data)
        assert "weight" in errors

    def test_zero_height_produces_error(self):
        data = {**self._valid_data(), "height": "0"}
        errors = validate_profile(data)
        assert "height" in errors

    def test_negative_height_produces_error(self):
        data = {**self._valid_data(), "height": "-1"}
        errors = validate_profile(data)
        assert "height" in errors

    def test_non_numeric_height_produces_error(self):
        data = {**self._valid_data(), "height": "tall"}
        errors = validate_profile(data)
        assert "height" in errors

    def test_valid_large_weight_no_error(self):
        """Very high but numeric weight (e.g. 300 kg) should not error."""
        data = {**self._valid_data(), "weight": "300"}
        errors = validate_profile(data)
        assert "weight" not in errors

    def test_decimal_height_no_error(self):
        """Height as decimal string (e.g. '5.11') must pass numeric validation."""
        data = {**self._valid_data(), "height": "5.11"}
        errors = validate_profile(data)
        assert "height" not in errors

#  MODULE 4 — apply_all_filters()
class TestApplyAllFilters:
    """Loop: iterates over each food entry (zero/one/many iterations)."""

    # ── Empty-list loop boundary ───────────────────────────────────
    def test_empty_food_list_returns_empty(self):
        """Zero-iteration loop: empty input must return empty output."""
        result = apply_all_filters([], {"target_goal": "weight loss"})
        assert result == []

    # ── Allergy filter branches ────────────────────────────────────
    def test_gluten_allergy_removes_non_gluten_free(self):
        """Gluten allergy branch: any food with gluten_free=False must be removed."""
        result = apply_all_filters(
            SAMPLE_FOODS, {"target_goal": "maintain", "allergies": ["gluten"]}
        )
        assert all(f["gluten_free"] for f in result), (
            "All results must be gluten-free when gluten allergy is set"
        )

    def test_dairy_allergy_removes_dairy_category(self):
        """Dairy allergy branch: foods in 'dairy' category must be excluded."""
        result = apply_all_filters(
            SAMPLE_FOODS, {"target_goal": "maintain", "allergies": ["dairy"]}
        )
        assert all(f["category"] != "dairy" for f in result)

    def test_no_allergies_returns_all_foods(self):
        """No allergy filter: all foods in the input must pass through."""
        result = apply_all_filters(
            SAMPLE_FOODS, {"target_goal": "maintain", "allergies": []}
        )
        assert len(result) == len(SAMPLE_FOODS)

    def test_weight_loss_goal_caps_at_400_calories(self):
        """Weight loss branch: foods above 400 cal must be filtered out."""
        result = apply_all_filters(SAMPLE_FOODS, {"target_goal": "weight loss"})
        assert all(f["calories"] <= 400 for f in result), (
            "Weight loss filter must remove any food > 400 calories"
        )

    def test_weight_gain_goal_requires_min_5g_protein(self):
        """Weight gain branch: foods with protein < 5g must be excluded."""
        result = apply_all_filters(SAMPLE_FOODS, {"target_goal": "weight gain"})
        assert all(f["protein"] >= 5 for f in result), (
            "Weight gain filter must keep only foods with >= 5g protein"
        )

    def test_maintain_goal_applies_no_calorie_filter(self):
        """Maintain branch: no calorie restriction — high-cal foods remain."""
        result = apply_all_filters(SAMPLE_FOODS, {"target_goal": "maintain"})
        # Almonds (579 cal) must survive
        names = [f["name"] for f in result]
        assert "Almonds" in names, (
            "Maintain goal must not apply a calorie cap"
        )

    # ── Combined filters ───────────────────────────────────────────
    def test_gluten_allergy_plus_weight_loss_goal(self):
        """Multiple filters applied simultaneously: both must be enforced."""
        result = apply_all_filters(
            SAMPLE_FOODS,
            {"target_goal": "weight loss", "allergies": ["gluten"]}
        )
        assert all(f["gluten_free"] for f in result), "Must be gluten-free"
        assert all(f["calories"] <= 400 for f in result), "Must be ≤ 400 cal"

    def test_single_food_list_loop_boundary(self):
        """One-iteration loop: single-element list filters correctly."""
        chicken = [f for f in SAMPLE_FOODS if f["name"] == "Chicken Breast"]
        result = apply_all_filters(chicken, {"target_goal": "weight loss"})
        # Chicken Breast is 165 cal — must pass weight-loss filter
        assert len(result) == 1

#  MODULE 5 — BMI → Goal Suggestion Logic
class TestBMIGoalSuggestion:
    """Branch coverage for the BMI-based goal suggestion in validate_goal()."""

    def _get_suggested_goal(self, weight: float, height: float) -> str:
        """Helper: derive suggested goal from BMI label, mirroring validate_goal()."""
        result = calculate_bmi(weight, height)
        label  = result["label"]
        if label == "Underweight":
            return "weight gain"
        elif label == "Normal":
            return "maintain"
        else:  # Overweight or Obese
            return "weight loss"

    def test_underweight_bmi_suggests_weight_gain(self):
        """BMI < 18.5 → suggested goal must be 'weight gain'."""
        assert self._get_suggested_goal(35, 5.6) == "weight gain"

    def test_normal_bmi_suggests_maintain(self):
        """BMI 18.5–24.9 → suggested goal must be 'maintain'."""
        assert self._get_suggested_goal(60, 5.4) == "maintain"

    def test_overweight_bmi_suggests_weight_loss(self):
        """BMI 25–29.9 → suggested goal must be 'weight loss'."""
        assert self._get_suggested_goal(80, 5.5) == "weight loss"

    def test_obese_bmi_suggests_weight_loss(self):
        """BMI ≥ 30 → suggested goal must be 'weight loss'."""
        assert self._get_suggested_goal(120, 5.5) == "weight loss"

#  MODULE 6 — check_progress()
class TestCheckProgress:
    """
    Mirrors check_progress() which returns True when weight is moving
    in the right direction for the user's goal.
    """

    def _check(self, weights: list, goal: str) -> bool:
        """Inline implementation of check_progress() logic for testing."""
        if len(weights) < 2:
            return False
        diff = weights[-1] - weights[-2]
        if goal == "weight loss":
            return diff < -0.5
        elif goal == "weight gain":
            return diff > 0.5
        elif goal == "maintain":
            return abs(diff) < 0.5
        return True

    # ── Insufficient-data branch ───────────────────────────────────
    def test_single_entry_returns_false(self):
        """< 2 entries → cannot determine progress → must return False."""
        assert self._check([80.0], "weight loss") is False

    def test_empty_history_returns_false(self):
        """Zero entries → must return False."""
        assert self._check([], "weight loss") is False

    # ── Weight-loss branch ────────────────────────────────────────
    def test_weight_loss_sufficient_drop(self):
        """Weight drop > 0.5 kg for weight loss goal → returns True."""
        assert self._check([82.0, 81.3], "weight loss") is True

    def test_weight_loss_insufficient_drop(self):
        """Weight drop ≤ 0.5 kg for weight loss goal → returns False."""
        assert self._check([82.0, 81.6], "weight loss") is False

    def test_weight_loss_gain_instead_of_loss(self):
        """Weight increased while goal is weight loss → returns False."""
        assert self._check([80.0, 81.0], "weight loss") is False

    # ── Weight-gain branch ────────────────────────────────────────
    def test_weight_gain_sufficient_gain(self):
        """Weight gain > 0.5 kg for weight gain goal → returns True."""
        assert self._check([70.0, 70.8], "weight gain") is True

    def test_weight_gain_insufficient_gain(self):
        """Weight gain ≤ 0.5 kg for weight gain goal → returns False."""
        assert self._check([70.0, 70.3], "weight gain") is False

    # ── Maintain branch ───────────────────────────────────────────
    def test_maintain_within_threshold(self):
        """Weight change < 0.5 kg for maintain goal → returns True."""
        assert self._check([75.0, 75.3], "maintain") is True

    def test_maintain_outside_threshold(self):
        """Weight change > 0.5 kg for maintain goal → returns False."""
        assert self._check([75.0, 76.0], "maintain") is False

#  MODULE 7 — should_regenerate_plan()  branch coverage

class TestShouldRegeneratePlan:
    """
    Two nested conditions:
      1. is_two_weeks_passed?  (time gate)
      2. check_progress?       (progress gate)
    Four paths through these two branches.
    """

    def _should_regen(self, last_updated_days_ago, weights, goal) -> bool:
        """Inline simulation of should_regenerate_plan() logic."""
        if last_updated_days_ago is None:
            return False   # first time — no regeneration
        two_weeks_passed = last_updated_days_ago >= 14
        if not two_weeks_passed:
            return False
        # Progress check
        if len(weights) < 2:
            return True   # no history = assume no progress
        diff = weights[-1] - weights[-2]
        if goal == "weight loss":
            progress_ok = diff < -0.5
        elif goal == "weight gain":
            progress_ok = diff > 0.5
        else:
            progress_ok = abs(diff) < 0.5
        return not progress_ok

    def test_first_time_no_regeneration(self):
        """No last_updated date → first-time user → must NOT regenerate."""
        assert self._should_regen(None, [], "weight loss") is False

    def test_under_2_weeks_no_regeneration(self):
        """Updated 10 days ago → time gate not met → must NOT regenerate."""
        assert self._should_regen(10, [80, 79], "weight loss") is False

    def test_2_weeks_with_good_progress_no_regeneration(self):
        """14 days passed + making progress → plan working → must NOT regenerate."""
        assert self._should_regen(14, [82, 81.3], "weight loss") is False

    def test_2_weeks_with_no_progress_triggers_regeneration(self):
        """14 days passed + no progress → plan not working → MUST regenerate."""
        assert self._should_regen(14, [82, 81.8], "weight loss") is True

    def test_over_2_weeks_no_history_triggers_regeneration(self):
        """14+ days passed, no weight history → assume stalled → MUST regenerate."""
        assert self._should_regen(20, [], "weight gain") is True

    def test_exact_14_day_boundary(self):
        """Exactly 14 days passed + no progress on weight_loss → regeneration triggers."""
        assert self._should_regen(14, [82, 81.8], "weight loss") is True

    def test_13_days_boundary_not_passed(self):
        """13 days (one day before boundary) — must NOT trigger regeneration."""
        assert self._should_regen(13, [80, 80], "maintain") is False


# ════════════════════════════════════════════════════════════════
#  MODULE 8 — Backend Latency  (Performance Path)
#  SLA: each profile-setup call ≤ 2 seconds
# ════════════════════════════════════════════════════════════════
class TestProfileSetupLatency:
    SLA = 2.0

    @pytest.fixture
    def profile(self):
        return {
            "target_goal":       "weight loss",
            "activity_level":    "sedentary",
            "timeline_weeks":    8,
            "allergies":         [],
            "health_conditions": [],
        }

    def test_validate_profile_under_100ms(self):
        """validate_profile must complete in < 100 ms."""
        data = {
            "age": "22", "weight": "60", "height": "5.4",
            "gender": "male", "activitylevel": "sedentary",
            "goal": "weight loss",
        }
        start   = time.time()
        validate_profile(data)
        elapsed = time.time() - start
        assert elapsed < 0.1, f"validate_profile took {elapsed:.3f}s — too slow"

    def test_calculate_bmi_under_100ms(self):
        """calculate_bmi must complete in < 100 ms."""
        start   = time.time()
        calculate_bmi(70, 5.7)
        elapsed = time.time() - start
        assert elapsed < 0.1

    def test_calculate_bmr_tdee_under_100ms(self):
        """BMR + TDEE calculation chain must complete in < 100 ms."""
        start   = time.time()
        bmr     = calculate_bmr(70, 5.7, 25, "male")
        calculate_tdee(bmr, "moderately active")
        elapsed = time.time() - start
        assert elapsed < 0.1

    def test_apply_all_filters_under_500ms(self, profile):
        """apply_all_filters on full food list must complete in < 500 ms."""
        start   = time.time()
        apply_all_filters(SAMPLE_FOODS, profile)
        elapsed = time.time() - start
        assert elapsed < 0.5

    def test_sequential_backend_SLA_KNOWN_FAIL(self, profile):

        result  = simulate_sequential_backend(profile)
        elapsed = result["elapsed"]
        print(f"\n[WB-TC-08] Sequential elapsed: {elapsed:.3f}s  SLA: {self.SLA}s")
        assert elapsed <= self.SLA, (
            f"WB-TC-08 FAIL: Sequential execution {elapsed:.3f}s > {self.SLA}s SLA. "
            "Fix: parallelise meal-plan + exercise-plan calls."
        )