"""
test_wb_filter_foods.py
════════════════════════════════════════════════════════════════════
WHITE BOX TESTING — filter_foods()   |   meal_plan.py
────────────────────────────────────────────────────────────────────
Technique  : Basis Path Testing (McCabe Cyclomatic Complexity)
V(G)       : 4  (3 predicate nodes + 1)
Paths      : P1 No conditions  |  P2 Allergy only
             P3 Allergy+Diabetes  |  P4 ALL conditions (FAILING)
Run        : pytest test_wb_filter_foods.py -v
════════════════════════════════════════════════════════════════════
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fixtures"))

import pytest
import pandas as pd
from mock_backend import filter_foods, SAMPLE_FOODS


# ─── FIXTURES ────────────────────────────────────────────────────
@pytest.fixture
def foods():
    """Fresh copy of the food dataset for every test."""
    return SAMPLE_FOODS.copy()


# ════════════════════════════════════════════════════════════════
#  VARIABLE DECLARATION TESTS
# ════════════════════════════════════════════════════════════════
class TestVariableDeclaration:
    """Verify internal variable initialisation inside filter_foods."""

    def test_allergies_list_initialises_empty(self, foods):
        """allergies should be an empty list when profile has none."""
        profile = {"allergies": [], "health_conditions": []}
        result = filter_foods(foods, profile)
        # If allergies was None the function would crash — passing here
        # means it initialised correctly to []
        assert isinstance(result, pd.DataFrame)

    def test_health_list_initialises_empty(self, foods):
        """health_conditions should default to [] when key is missing."""
        profile = {}            # no 'health_conditions' key at all
        result = filter_foods(foods, profile)
        assert isinstance(result, pd.DataFrame)

    def test_output_is_dataframe(self, foods):
        """Return type must always be pd.DataFrame."""
        result = filter_foods(foods, {"allergies": [], "health_conditions": []})
        assert isinstance(result, pd.DataFrame), \
            "filter_foods must return a DataFrame"


# ════════════════════════════════════════════════════════════════
#  CONTROL STRUCTURE TESTS  (boolean branching)
# ════════════════════════════════════════════════════════════════
class TestControlStructure:

    def test_allergy_condition_TRUE_triggers_filter(self, foods):
        """When allergies list is non-empty the filter branch executes."""
        total_before = len(foods)
        profile = {"allergies": ["egg"], "health_conditions": []}
        result = filter_foods(foods, profile)
        assert len(result) < total_before, \
            "Allergy filter (True branch) must reduce food count"

    def test_allergy_condition_FALSE_no_filter(self, foods):
        """When allergies list is empty no food should be removed."""
        total_before = len(foods)
        profile = {"allergies": [], "health_conditions": []}
        result = filter_foods(foods, profile)
        assert len(result) == total_before, \
            "Empty allergies (False branch) must not remove any food"

    def test_diabetes_condition_TRUE_removes_sweets(self, foods):
        """Diabetes branch must remove halwa, kheer, mango shake."""
        profile = {"allergies": [], "health_conditions": ["diabetes"]}
        result = filter_foods(foods, profile)
        sweet_foods = ["halwa", "kheer", "mango shake"]
        for food in sweet_foods:
            assert food not in result["food_name"].values, \
                f"Diabetes filter must remove '{food}'"

    def test_diabetes_condition_FALSE_retains_sweets(self, foods):
        """Without diabetes condition sweets should remain in dataset."""
        profile = {"allergies": [], "health_conditions": []}
        result = filter_foods(foods, profile)
        # at least one sweet should still be present
        sweets_present = any(
            f in result["food_name"].values for f in ["halwa","kheer"]
        )
        assert sweets_present, "Without diabetes condition, sweets must remain"

    def test_hypertension_condition_TRUE_removes_heavy_foods(self, foods):
        """Hypertension branch must remove nihari, biryani, paratha."""
        profile = {"allergies": [], "health_conditions": ["hypertension"]}
        result = filter_foods(foods, profile)
        heavy = ["nihari", "biryani", "paratha"]
        for food in heavy:
            assert food not in result["food_name"].values, \
                f"Hypertension filter must remove '{food}'"


# ════════════════════════════════════════════════════════════════
#  METHOD PARAMETER TESTS
# ════════════════════════════════════════════════════════════════
class TestMethodParameters:

    def test_valid_df_valid_profile(self, foods):
        """Valid DataFrame + valid profile → function runs without error."""
        profile = {"allergies": ["egg"], "health_conditions": ["diabetes"]}
        result = filter_foods(foods, profile)
        assert isinstance(result, pd.DataFrame)

    def test_empty_dataframe_input(self):
        """Empty DataFrame should not crash — returns empty DataFrame."""
        empty_df = pd.DataFrame(columns=[
            "food_name","calories","protein_g","carbs_g","fat_g","food_name_lower"
        ])
        profile = {"allergies": ["egg"], "health_conditions": []}
        result = filter_foods(empty_df, profile)
        assert len(result) == 0

    def test_missing_profile_keys_use_defaults(self, foods):
        """Profile with no keys should not raise KeyError."""
        result = filter_foods(foods, {})
        assert isinstance(result, pd.DataFrame)

    def test_allergy_case_insensitive(self, foods):
        """Allergy matching must be case-insensitive (EGG == egg)."""
        profile_upper = {"allergies": ["EGG"], "health_conditions": []}
        profile_lower = {"allergies": ["egg"], "health_conditions": []}
        result_upper = filter_foods(foods, profile_upper)
        result_lower = filter_foods(foods, profile_lower)
        assert len(result_upper) == len(result_lower), \
            "Allergy filter must be case-insensitive"


# ════════════════════════════════════════════════════════════════
#  RETURN TYPE TESTS
# ════════════════════════════════════════════════════════════════
class TestReturnType:

    def test_return_is_dataframe(self, foods):
        result = filter_foods(foods, {"allergies": [], "health_conditions": []})
        assert type(result).__name__ == "DataFrame"

    def test_return_has_required_columns(self, foods):
        result = filter_foods(foods, {})
        for col in ["food_name", "calories", "protein_g", "carbs_g", "fat_g"]:
            assert col in result.columns, f"Column '{col}' missing from return"

    def test_index_is_reset(self, foods):
        """Index must be reset (0,1,2…) after filtering."""
        profile = {"allergies": ["egg"], "health_conditions": ["diabetes"]}
        result = filter_foods(foods, profile)
        expected_idx = list(range(len(result)))
        assert list(result.index) == expected_idx, "Index must be reset"


# ════════════════════════════════════════════════════════════════
#  BASIS PATH TESTS  (Cyclomatic Complexity V(G) = 4)
# ════════════════════════════════════════════════════════════════
class TestBasisPaths:
    """
    Flow graph nodes:
        1/2/3 → Init + copy df
        4     → if len(allergies)>0   ← predicate
        5     → Allergy filter
        6     → if "diabetes" in health ← predicate
        7     → Diabetes filter
        8     → if "hypertension" in health ← predicate
        9     → Hypertension filter
        10    → return out

    V(G) = 3 + 1 = 4
    """

    def test_path1_no_conditions(self, foods):
        """P1: 1→4(F)→6(F)→8(F)→10  — All conditions FALSE."""
        profile = {"allergies": [], "health_conditions": []}
        result  = filter_foods(foods, profile)
        assert len(result) == len(foods), \
            "P1: No filtering — all foods must be returned"

    def test_path2_allergy_only(self, foods):
        """P2: 1→4(T)→5→6(F)→8(F)→10  — Only allergy branch TRUE."""
        profile = {"allergies": ["egg"], "health_conditions": []}
        result  = filter_foods(foods, profile)
        assert len(result) < len(foods)
        assert "boiled egg"   not in result["food_name"].values
        assert "egg omelette" not in result["food_name"].values
        # diabetes-restricted foods still present
        assert "halwa" in result["food_name"].values

    def test_path3_allergy_and_diabetes(self, foods):
        """P3: 1→4(T)→5→6(T)→7→8(F)→10  — Allergy + Diabetes TRUE."""
        profile = {"allergies": ["egg"], "health_conditions": ["diabetes"]}
        result  = filter_foods(foods, profile)
        assert "boiled egg" not in result["food_name"].values
        assert "halwa"      not in result["food_name"].values
        assert "mango shake" not in result["food_name"].values
        # hypertension foods still present
        assert "biryani" in result["food_name"].values

    # ── FAILING PATH ──────────────────────────────────────────────
    def test_path4_all_conditions_FAIL(self, foods):
        """
        P4: 1→4(T)→5→6(T)→7→8(T)→9→10  — ALL conditions TRUE.

        EXPECTED: at least 1 food remains after all filters.
        ACTUAL   : 0 foods remain → FAIL.

        Root cause: Limited Pakistani food dataset — stacking allergy +
        diabetes + hypertension filters eliminates every available item.
        Fix needed: constraint-relaxation fallback in filter_foods().
        """
        profile = {
            "allergies": ["egg", "wheat"],
            "health_conditions": ["diabetes", "hypertension"],
        }
        result = filter_foods(foods, profile)

        print(f"\n[WB-TC-04] Foods remaining after ALL filters: {len(result)}")
        print(f"           Remaining items: {result['food_name'].tolist()}")

        # This assertion FAILS — documents the known bug
        assert len(result) > 0, (
            "WB-TC-04 FAIL: All filters combined eliminated entire food dataset. "
            "Fix: add constraint-relaxation fallback when pool < 3 items."
        )


# ════════════════════════════════════════════════════════════════
#  LOOP TESTS  (inner for-loop over allergies list)
# ════════════════════════════════════════════════════════════════
class TestLoopCoverage:

    def test_loop_skip_zero_allergies(self, foods):
        """Skip loop: empty allergies list — filter does not execute."""
        result = filter_foods(foods, {"allergies": [], "health_conditions": []})
        assert len(result) == len(foods)

    def test_loop_one_allergy(self, foods):
        """One pass: single allergy removes exactly those foods."""
        result = filter_foods(foods, {"allergies": ["egg"], "health_conditions": []})
        assert all("egg" not in n for n in result["food_name_lower"].values)

    def test_loop_two_allergies(self, foods):
        """Two passes: two allergies both removed."""
        result = filter_foods(foods,
                              {"allergies": ["egg", "halwa"], "health_conditions": []})
        for food in result["food_name_lower"]:
            assert "egg"   not in food
            assert "halwa" not in food

    def test_loop_m_allergies(self, foods):
        """M passes (M < N): three allergies, all filtered correctly."""
        result = filter_foods(foods,
                              {"allergies": ["egg","halwa","nihari"],
                               "health_conditions": []})
        forbidden = ["egg", "halwa", "nihari"]
        for food in result["food_name_lower"]:
            for f in forbidden:
                assert f not in food, f"'{f}' should have been filtered"
