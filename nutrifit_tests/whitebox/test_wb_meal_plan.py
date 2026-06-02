import sys, os, time, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fixtures"))
from mock_backend import (
    filter_foods, calculate_daily_calories, generate_meal_plan, _FOODS
)

class TestFilterFoods:

    # ── Basis Path 1: no filters → all foods returned ─────────────────────
    def test_bp1_no_filter_returns_all(self):
        """[WB-FF-01] No criteria → entire food list returned."""
        result = filter_foods()
        assert len(result) == len(_FOODS), (
            "WB-FF-01 FAIL: Expected all foods without filters. "
            "Fix: ensure default args are all None and no implicit filter applied."
        )

    # ── Basis Path 2: category filter only ────────────────────────────────
    @pytest.mark.parametrize("cat,expected_min", [
        ("protein",  3),
        ("carbs",    3),
        ("fat",      2),
        ("dairy",    2),
        ("vegetable",1),
        ("fruit",    1),
    ])
    def test_bp2_category_filter(self, cat, expected_min):
        """[WB-FF-02] Category filter removes all non-matching rows."""
        result = filter_foods(category=cat)
        assert len(result) >= expected_min, (
            f"WB-FF-02 FAIL: category='{cat}' returned {len(result)}, "
            f"expected >= {expected_min}."
        )
        assert all(f["category"] == cat for f in result), (
            f"WB-FF-02 FAIL: Non-'{cat}' items leaked through filter."
        )

    # ── Basis Path 3: calorie cap only ────────────────────────────────────
    def test_bp3_calorie_cap_filters_high_cal(self):
        """[WB-FF-03] max_calories removes foods above threshold."""
        result = filter_foods(max_calories=200)
        assert all(f["calories"] <= 200 for f in result), (
            "WB-FF-03 FAIL: Foods above calorie cap leaked through. "
            "Fix: use <= not < in calorie comparison."
        )
        assert len(result) > 0, "WB-FF-03 FAIL: Should have results below 200 kcal."

    def test_bp3_calorie_cap_exact_boundary(self):
        """[WB-FF-04] Boundary: food at exactly max_calories must be included (<=)."""
        boundary_cal = 165  # Chicken Breast = 165 kcal
        result = filter_foods(max_calories=boundary_cal)
        names = [f["name"] for f in result]
        assert "Chicken Breast" in names, (
            "WB-FF-04 FAIL: Boundary value excluded. Off-by-one in <= check."
        )

    # ── Basis Path 4: protein floor only ──────────────────────────────────
    def test_bp4_min_protein_filter(self):
        """[WB-FF-05] min_protein keeps only high-protein foods."""
        result = filter_foods(min_protein=15)
        assert all(f["protein"] >= 15 for f in result), (
            "WB-FF-05 FAIL: Low-protein item passed min_protein filter."
        )
        assert len(result) > 0, "WB-FF-05 FAIL: No results for protein >= 15."

    def test_bp4_min_protein_zero_returns_all(self):
        """[WB-FF-06] min_protein=0 should not discard anything."""
        result = filter_foods(min_protein=0)
        assert len(result) == len(_FOODS), (
            "WB-FF-06 FAIL: min_protein=0 discarded items unexpectedly."
        )

    # ══════════════════════════════════════════════════════════════════════
    # Branch coverage — boolean flags
    # ══════════════════════════════════════════════════════════════════════

    def test_branch_vegan_true(self):
        """[WB-FF-07] vegan=True → only vegan foods."""
        result = filter_foods(vegan=True)
        assert all(f["vegan"] for f in result), (
            "WB-FF-07 FAIL: Non-vegan food returned when vegan=True."
        )

    def test_branch_vegan_false(self):
        """[WB-FF-08] vegan=False → only non-vegan foods."""
        result = filter_foods(vegan=False)
        assert all(not f["vegan"] for f in result), (
            "WB-FF-08 FAIL: Vegan food returned when vegan=False."
        )

    def test_branch_gluten_free_true(self):
        """[WB-FF-09] gluten_free=True → only gluten-free foods."""
        result = filter_foods(gluten_free=True)
        assert all(f["gluten_free"] for f in result), (
            "WB-FF-09 FAIL: Gluten food returned when gluten_free=True."
        )

    def test_branch_gluten_free_false(self):
        """[WB-FF-10] gluten_free=False → only non-gluten-free foods."""
        result = filter_foods(gluten_free=False)
        assert all(not f["gluten_free"] for f in result), (
            "WB-FF-10 FAIL: Gluten-free food returned when gluten_free=False."
        )

    # ══════════════════════════════════════════════════════════════════════
    # Combined (compound) filter — loop iteration coverage
    # ══════════════════════════════════════════════════════════════════════

    def test_loop_combined_all_filters(self):
        """[WB-FF-11] All 5 filters applied simultaneously — loop touches every row."""
        result = filter_foods(
            category="protein",
            max_calories=200,
            min_protein=10,
            vegan=False,
            gluten_free=True,
        )
        for food in result:
            assert food["category"] == "protein"
            assert food["calories"] <= 200
            assert food["protein"] >= 10
            assert not food["vegan"]
            assert food["gluten_free"]

    def test_loop_no_match_returns_empty(self):
        """[WB-FF-12] Contradictory filters → empty list, not exception."""
        result = filter_foods(category="fruit", vegan=False)
        assert result == [], (
            "WB-FF-12 FAIL: Contradictory filters should return [], not raise."
        )

    def test_loop_single_item_match(self):
        """[WB-FF-13] Narrow filter isolates exactly one food — single-iteration result."""
        result = filter_foods(category="vegetable")
        assert len(result) == 1, (
            f"WB-FF-13 FAIL: Expected 1 vegetable, got {len(result)}."
        )
        assert result[0]["name"] == "Broccoli"

    def test_loop_result_preserves_all_keys(self):
        """[WB-FF-14] Filtered results must carry full food dict keys."""
        required = {"name", "calories", "protein", "carbs", "fat",
                    "category", "vegan", "gluten_free"}
        result = filter_foods(category="protein")
        for food in result:
            missing = required - food.keys()
            assert not missing, f"WB-FF-14 FAIL: Missing keys {missing} in {food['name']}."


# ══════════════════════════════════════════════════════════════════════════════
# TestCalculateDailyCalories
# ══════════════════════════════════════════════════════════════════════════════

class TestCalculateDailyCalories:

    def test_male_weight_loss_below_maintenance(self):
        """[WB-CAL-01] Male weight-loss TDEE must be 500 kcal below maintenance."""
        maintenance = calculate_daily_calories(75, 175, 30, "male", "maintenance")
        weight_loss  = calculate_daily_calories(75, 175, 30, "male", "weight_loss")
        assert abs((maintenance - weight_loss) - 500) < 1, (
            "WB-CAL-01 FAIL: Weight-loss adjustment is not -500 kcal."
        )

    def test_female_weight_gain_above_maintenance(self):
        """[WB-CAL-02] Female weight-gain TDEE must be 500 kcal above maintenance."""
        maintenance  = calculate_daily_calories(60, 160, 25, "female", "maintenance")
        weight_gain  = calculate_daily_calories(60, 160, 25, "female", "weight_gain")
        assert abs((weight_gain - maintenance) - 500) < 1, (
            "WB-CAL-02 FAIL: Weight-gain adjustment is not +500 kcal."
        )

    def test_male_female_bmr_differ(self):
        """[WB-CAL-03] Same stats → male BMR > female BMR (Harris-Benedict)."""
        male   = calculate_daily_calories(70, 170, 28, "male",   "maintenance")
        female = calculate_daily_calories(70, 170, 28, "female", "maintenance")
        assert male > female, (
            "WB-CAL-03 FAIL: Male TDEE should exceed female for same stats."
        )

    def test_calories_positive(self):
        """[WB-CAL-04] Result must always be a positive number."""
        result = calculate_daily_calories(50, 150, 20, "female", "weight_loss")
        assert result > 0, "WB-CAL-04 FAIL: Calorie result must be positive."

    @pytest.mark.parametrize("goal", ["weight_loss", "weight_gain", "maintenance"])
    def test_all_goals_return_numeric(self, goal):
        """[WB-CAL-05] All valid goals produce a float, not an error dict."""
        result = calculate_daily_calories(70, 170, 30, "male", goal)
        assert isinstance(result, (int, float)), (
            f"WB-CAL-05 FAIL: goal='{goal}' did not return a number."
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestGenerateMealPlan
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateMealPlan:

    def test_standard_plan_has_three_meals(self):
        """[WB-MP-01] Default plan must contain breakfast, lunch, dinner."""
        result = generate_meal_plan("weight_loss", 2000)
        assert set(result.keys()) >= {"breakfast", "lunch", "dinner"}, (
            "WB-MP-01 FAIL: Meal plan missing one or more meal keys."
        )

    def test_meal_calories_sum_near_total(self):
        """[WB-MP-02] Sum of meal calories ≈ daily_calories (within 5 kcal rounding)."""
        daily = 2000
        result = generate_meal_plan("maintenance", daily)
        total = sum(m["calories"] for m in result.values())
        assert abs(total - daily) < 5, (
            f"WB-MP-02 FAIL: Meal calories sum {total} != {daily}."
        )

    def test_vegan_plan_excludes_animal_products(self):
        """[WB-MP-03] vegan=True plan must not reference non-vegan foods."""
        non_vegan = {f["name"] for f in _FOODS if not f["vegan"]}
        result = generate_meal_plan("maintenance", 2000, vegan=True)
        for meal_key, meal in result.items():
            assert meal["food"] not in non_vegan, (
                f"WB-MP-03 FAIL: Non-vegan food '{meal['food']}' in vegan plan ({meal_key})."
            )

    def test_gluten_free_plan_excludes_gluten(self):
        """[WB-MP-04] gluten_free=True plan must not reference gluten foods."""
        gluten_foods = {f["name"] for f in _FOODS if not f["gluten_free"]}
        result = generate_meal_plan("weight_gain", 2500, gluten_free=True)
        for meal_key, meal in result.items():
            assert meal["food"] not in gluten_foods, (
                f"WB-MP-04 FAIL: Gluten food '{meal['food']}' in gluten-free plan ({meal_key})."
            )

    def test_each_meal_has_food_and_calories_keys(self):
        """[WB-MP-05] Every meal dict must have 'food' and 'calories' keys."""
        result = generate_meal_plan("weight_loss", 1800)
        for meal_key, meal in result.items():
            assert "food" in meal and "calories" in meal, (
                f"WB-MP-05 FAIL: Meal '{meal_key}' missing required keys."
            )

    def test_calorie_splits_roughly_correct(self):
        """[WB-MP-06] Breakfast ≈25%, Lunch ≈40%, Dinner ≈35% of daily calories."""
        daily = 2000
        result = generate_meal_plan("maintenance", daily)
        assert abs(result["breakfast"]["calories"] - daily * 0.25) < 5
        assert abs(result["lunch"]["calories"]     - daily * 0.40) < 5
        assert abs(result["dinner"]["calories"]    - daily * 0.35) < 5