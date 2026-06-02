import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fixtures"))
from mock_backend import (
    get_cheatmeal_plan, validate_cheatmeal_frequency,
    cheatmeal_weekly_extra_calories, CHEATMEAL_FREQUENCY_RULES, _CHEATMEALS,
)
# TestGetCheatmealPlan  — branch coverage per goal

class TestGetCheatmealPlan:

    @pytest.mark.parametrize("goal", ["weight_loss", "weight_gain", "maintenance"])
    def test_valid_goal_returns_nonempty_list(self, goal):
        """[WB-CM-01] Every valid goal returns at least one cheat meal."""
        result = get_cheatmeal_plan(goal)
        assert isinstance(result, list),       f"WB-CM-01 FAIL: '{goal}' → not a list."
        assert len(result) > 0,                f"WB-CM-01 FAIL: '{goal}' → empty list."

    def test_unknown_goal_returns_empty_list(self):
        """[WB-CM-02] Unknown goal returns [] not an error/exception."""
        result = get_cheatmeal_plan("keto")
        assert result == [], "WB-CM-02 FAIL: Unknown goal should return []."

    def test_empty_string_goal_returns_empty(self):
        """[WB-CM-03] Empty string goal returns []."""
        result = get_cheatmeal_plan("")
        assert result == [], "WB-CM-03 FAIL: Empty string goal should return []."

    @pytest.mark.parametrize("goal", ["Weight_Loss", "WEIGHT_GAIN", "Maintenance"])
    def test_goal_case_insensitive(self, goal):
        """[WB-CM-04] Goal matching is case-insensitive."""
        result = get_cheatmeal_plan(goal)
        assert isinstance(result, list) and len(result) > 0, (
            f"WB-CM-04 FAIL: goal='{goal}' (mixed case) returned empty — case sensitivity bug."
        )

    def test_each_cheatmeal_has_required_keys(self):
        """[WB-CM-05] Every cheat meal dict must have name, calories, frequency."""
        required = {"name", "calories", "frequency"}
        for goal in ["weight_loss", "weight_gain", "maintenance"]:
            for meal in get_cheatmeal_plan(goal):
                missing = required - meal.keys()
                assert not missing, (
                    f"WB-CM-05 FAIL: goal='{goal}' meal '{meal.get('name')}' "
                    f"missing keys: {missing}."
                )

    def test_calories_are_positive(self):
        """[WB-CM-06] All cheat meal calorie values must be > 0."""
        for goal in _CHEATMEALS:
            for meal in get_cheatmeal_plan(goal):
                assert meal["calories"] > 0, (
                    f"WB-CM-06 FAIL: '{meal['name']}' has non-positive calories."
                )

    def test_frequency_values_are_valid(self):
        """[WB-CM-07] All frequency strings are in CHEATMEAL_FREQUENCY_RULES."""
        for goal in _CHEATMEALS:
            for meal in get_cheatmeal_plan(goal):
                assert meal["frequency"] in CHEATMEAL_FREQUENCY_RULES, (
                    f"WB-CM-07 FAIL: '{meal['name']}' has invalid frequency "
                    f"'{meal['frequency']}'. Must be one of {list(CHEATMEAL_FREQUENCY_RULES)}."
                )

    def test_result_is_independent_copy(self):
        """[WB-CM-08] Mutating returned list must not affect subsequent calls."""
        result1 = get_cheatmeal_plan("weight_loss")
        result1.clear()
        result2 = get_cheatmeal_plan("weight_loss")
        assert len(result2) > 0, (
            "WB-CM-08 FAIL: get_cheatmeal_plan returned a reference — "
            "internal store was mutated."
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestValidateFrequency
# ══════════════════════════════════════════════════════════════════════════════

class TestValidateFrequency:

    @pytest.mark.parametrize("freq", list(CHEATMEAL_FREQUENCY_RULES.keys()))
    def test_valid_frequencies_pass(self, freq):
        """[WB-CM-09] All defined frequency strings return True."""
        assert validate_cheatmeal_frequency(freq) is True, (
            f"WB-CM-09 FAIL: Valid frequency '{freq}' rejected."
        )

    @pytest.mark.parametrize("bad_freq", ["never", "monthly", "", "weekly", "3x_week"])
    def test_invalid_frequencies_fail(self, bad_freq):
        """[WB-CM-10] Undefined frequency strings return False."""
        assert validate_cheatmeal_frequency(bad_freq) is False, (
            f"WB-CM-10 FAIL: Invalid frequency '{bad_freq}' was accepted."
        )

# TestCheatmealWeeklyCalories  — calculation branch coverage

class TestCheatmealWeeklyCalories:

    def test_unknown_goal_returns_zero(self):
        """[WB-CM-11] Unknown goal → 0 weekly extra calories."""
        result = cheatmeal_weekly_extra_calories("keto")
        assert result == 0.0, (
            f"WB-CM-11 FAIL: Unknown goal should return 0.0, got {result}."
        )

    @pytest.mark.parametrize("goal", ["weight_loss", "weight_gain", "maintenance"])
    def test_valid_goal_returns_positive_calories(self, goal):
        """[WB-CM-12] Valid goal produces positive weekly extra calories."""
        result = cheatmeal_weekly_extra_calories(goal)
        assert result > 0, (
            f"WB-CM-12 FAIL: '{goal}' weekly extra calories should be > 0, got {result}."
        )

    def test_weight_gain_higher_than_weight_loss(self):
        """[WB-CM-13] weight_gain cheat meal calories > weight_loss (higher-cal foods)."""
        gain = cheatmeal_weekly_extra_calories("weight_gain")
        loss = cheatmeal_weekly_extra_calories("weight_loss")
        assert gain > loss, (
            f"WB-CM-13 FAIL: weight_gain ({gain}) should exceed weight_loss ({loss}) weekly cals."
        )

    def test_weekly_calculation_matches_manual(self):
        """[WB-CM-14] Manual calculation matches cheatmeal_weekly_extra_calories."""
        goal  = "weight_loss"
        meals = get_cheatmeal_plan(goal)
        manual = sum(
            m["calories"] * CHEATMEAL_FREQUENCY_RULES[m["frequency"]]
            for m in meals
        )
        result = cheatmeal_weekly_extra_calories(goal)
        assert abs(result - manual) < 0.01, (
            f"WB-CM-14 FAIL: Function returned {result}, manual calc = {manual}."
        )

    def test_return_type_is_float(self):
        """[WB-CM-15] Return type is always float, not int or dict."""
        result = cheatmeal_weekly_extra_calories("maintenance")
        assert isinstance(result, float), (
            f"WB-CM-15 FAIL: Expected float, got {type(result).__name__}."
        )