"""
test_wb_meal_filter.py
════════════════════════════════════════════════════════════════════
WHITE BOX TESTING — filter_by_allergies() & filter_by_health_conditions()
Source file : meal_plan.py  (ProfessionalMealPlanner)
────────────────────────────────────────────────────────────────────
Technique   : Basis Path Testing  (McCabe Cyclomatic Complexity)
V(G)        : 4  (3 predicate nodes + 1)

Paths
  P1  No filters applied            (allergies=[], conditions=[])
  P2  Allergy filter only           (egg allergy)
  P3  Allergy + health condition    (egg + diabetes)
  P4  All conditions stacked        (egg + gluten + diabetes + hypertension)
       → KNOWN FAIL: dataset too small, all foods eliminated

Run : pytest whitebox/ -v
════════════════════════════════════════════════════════════════════
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fixtures"))

import pytest
import pandas as pd
from mock_backend import (
    filter_by_allergies,
    filter_by_health_conditions,
    apply_all_filters,
    SAMPLE_FOODS,
    ALLERGEN_FILTERS,
    HEALTH_RESTRICTIONS,
)


@pytest.fixture
def foods():
    """Fresh copy of food dataset for every test."""
    return SAMPLE_FOODS.copy()


# ════════════════════════════════════════════════════════════════
#  VARIABLE DECLARATION TESTS
# ════════════════════════════════════════════════════════════════
class TestVariableDeclaration:

    def test_allergen_filters_dict_exists(self):
        """ALLERGEN_FILTERS must be a non-empty dict."""
        assert isinstance(ALLERGEN_FILTERS, dict)
        assert len(ALLERGEN_FILTERS) > 0

    def test_health_restrictions_dict_exists(self):
        """HEALTH_RESTRICTIONS must contain diabetes and hypertension."""
        assert "diabetes" in HEALTH_RESTRICTIONS
        assert "hypertension" in HEALTH_RESTRICTIONS

    def test_empty_allergies_returns_dataframe(self, foods):
        """Empty allergies list — function must return DataFrame without crash."""
        result = filter_by_allergies(foods, [])
        assert isinstance(result, pd.DataFrame)

    def test_empty_conditions_returns_dataframe(self, foods):
        """Empty conditions list — function must return DataFrame without crash."""
        result = filter_by_health_conditions(foods, [])
        assert isinstance(result, pd.DataFrame)

    def test_return_has_food_name_lower_column(self, foods):
        """food_name_lower column must survive filtering."""
        result = apply_all_filters(foods, {"allergies": ["egg"], "health_conditions": []})
        assert "food_name_lower" in result.columns


# ════════════════════════════════════════════════════════════════
#  CONTROL STRUCTURE TESTS  (True / False branch coverage)
# ════════════════════════════════════════════════════════════════
class TestControlStructure:

    # ── Allergy branch ─────────────────────────────────────────
    def test_allergy_branch_TRUE_removes_egg_foods(self, foods):
        """Allergy=egg → 'Boiled egg' and 'Egg omelette' removed."""
        result = filter_by_allergies(foods, ["egg"])
        names = result["food_name"].str.lower().tolist()
        assert not any("egg" in n or "omelette" in n for n in names), \
            "Egg-containing foods must be removed when egg allergy is set"

    def test_allergy_branch_FALSE_no_removal(self, foods):
        """Empty allergies → zero rows removed."""
        result = filter_by_allergies(foods, [])
        assert len(result) == len(foods), \
            "No allergy filter must not remove any food"

    def test_allergy_branch_dairy_removes_yogurt_and_lassi(self, foods):
        """Dairy allergy → yogurt, lassi, milkshake removed."""
        result = filter_by_allergies(foods, ["dairy"])
        names = result["food_name"].str.lower().tolist()
        for item in ["yogurt", "lassi", "milkshake"]:
            assert item not in names, f"Dairy allergy must remove '{item}'"

    def test_allergy_branch_nuts_removes_halwa_kheer(self, foods):
        """Nuts allergy → halwa and kheer removed (contain nuts)."""
        result = filter_by_allergies(foods, ["nuts"])
        names = result["food_name"].str.lower().tolist()
        assert "halwa" not in names
        assert "kheer" not in names

    # ── Diabetes branch ────────────────────────────────────────
    def test_diabetes_branch_TRUE_removes_sweets(self, foods):
        """Diabetes condition → halwa, kheer, biryani, juice removed."""
        result = filter_by_health_conditions(foods, ["diabetes"])
        names = result["food_name"].str.lower().tolist()
        for item in ["halwa", "kheer", "chicken biryani", "mango juice",
                     "fruit chaat", "milkshake", "lassi"]:
            assert item not in names, \
                f"Diabetes filter must remove '{item}'"

    def test_diabetes_branch_FALSE_sweets_remain(self, foods):
        """No diabetes → halwa and kheer remain."""
        result = filter_by_health_conditions(foods, [])
        names = result["food_name"].tolist()
        assert "Halwa" in names and "Kheer" in names, \
            "Without diabetes condition sweets must remain"

    # ── Hypertension branch ────────────────────────────────────
    def test_hypertension_branch_TRUE_removes_heavy_foods(self, foods):
        """Hypertension → nihari, biryani, paratha removed."""
        result = filter_by_health_conditions(foods, ["hypertension"])
        names = result["food_name"].str.lower().tolist()
        for item in ["nihari", "chicken biryani", "paratha"]:
            assert item not in names, \
                f"Hypertension filter must remove '{item}'"

    def test_hypertension_branch_FALSE_heavy_foods_remain(self, foods):
        """No hypertension → nihari still present."""
        result = filter_by_health_conditions(foods, [])
        assert "Nihari" in result["food_name"].tolist()

    # ── Heart disease branch ───────────────────────────────────
    def test_heart_disease_removes_fried_and_biryani(self, foods):
        """Heart disease → biryani, nihari, haleem removed."""
        result = filter_by_health_conditions(foods, ["heart disease"])
        names = result["food_name"].str.lower().tolist()
        assert "chicken biryani" not in names
        assert "nihari" not in names


# ════════════════════════════════════════════════════════════════
#  METHOD PARAMETER TESTS
# ════════════════════════════════════════════════════════════════
class TestMethodParameters:

    def test_valid_df_valid_allergies(self, foods):
        """Valid DataFrame + valid allergy list → no exception."""
        result = filter_by_allergies(foods, ["egg", "dairy"])
        assert isinstance(result, pd.DataFrame)

    def test_empty_dataframe_no_crash(self):
        """Empty DataFrame must not crash."""
        empty = pd.DataFrame(columns=SAMPLE_FOODS.columns)
        result = filter_by_allergies(empty, ["egg"])
        assert len(result) == 0

    def test_unknown_allergen_ignored(self, foods):
        """Allergen not in ALLERGEN_FILTERS dict → no food removed."""
        before = len(foods)
        result = filter_by_allergies(foods, ["plutonium"])
        assert len(result) == before, \
            "Unknown allergen must not remove any food"

    def test_unknown_health_condition_ignored(self, foods):
        """Unknown health condition → no food removed."""
        before = len(foods)
        result = filter_by_health_conditions(foods, ["lycanthropy"])
        assert len(result) == before, \
            "Unknown health condition must not remove any food"

    def test_allergen_case_insensitive(self, foods):
        """EGG and egg must produce identical results."""
        r1 = filter_by_allergies(foods, ["EGG"])
        r2 = filter_by_allergies(foods, ["egg"])
        assert len(r1) == len(r2), \
            "Allergy filter must be case-insensitive"

    def test_health_condition_case_insensitive(self, foods):
        """DIABETES and diabetes must produce identical results."""
        r1 = filter_by_health_conditions(foods, ["DIABETES"])
        r2 = filter_by_health_conditions(foods, ["diabetes"])
        assert len(r1) == len(r2), \
            "Health condition filter must be case-insensitive"

    def test_apply_all_filters_no_profile_keys(self, foods):
        """Empty profile dict must not raise KeyError."""
        result = apply_all_filters(foods, {})
        assert isinstance(result, pd.DataFrame)


# ════════════════════════════════════════════════════════════════
#  RETURN TYPE TESTS
# ════════════════════════════════════════════════════════════════
class TestReturnType:

    def test_return_is_dataframe(self, foods):
        result = apply_all_filters(foods, {})
        assert type(result).__name__ == "DataFrame"

    def test_return_has_required_columns(self, foods):
        result = apply_all_filters(foods, {})
        for col in ["food_name", "calories", "protein_g", "carbs_g", "fat_g"]:
            assert col in result.columns, f"Column '{col}' missing"

    def test_index_is_reset_after_allergy_filter(self, foods):
        """Index must start from 0 after filtering."""
        result = filter_by_allergies(foods, ["egg"])
        assert list(result.index) == list(range(len(result))), \
            "Index must be reset after filtering"

    def test_index_is_reset_after_health_filter(self, foods):
        result = filter_by_health_conditions(foods, ["diabetes"])
        assert list(result.index) == list(range(len(result)))


# ════════════════════════════════════════════════════════════════
#  BASIS PATH TESTS  (V(G) = 4)
# ════════════════════════════════════════════════════════════════
class TestBasisPaths:
    """
    Flow graph (apply_all_filters):
      Node 1 → if profile.allergies?          ← predicate
      Node 2 → filter_by_allergies()
      Node 3 → if profile.health_conditions?  ← predicate
      Node 4 → filter_by_health_conditions()
      Node 5 → return df

    V(G) = 2 + 1 = 3 (+ 1 for inner loop in allergy filter) = 4
    """

    def test_path1_no_filters(self, foods):
        """P1: allergies=[] conditions=[] → all foods returned."""
        result = apply_all_filters(foods, {"allergies": [], "health_conditions": []})
        assert len(result) == len(foods), "P1: no filtering, full dataset expected"

    def test_path2_allergy_only(self, foods):
        """P2: egg allergy only → egg foods removed, sweets remain."""
        result = apply_all_filters(foods, {"allergies": ["egg"], "health_conditions": []})
        names = result["food_name"].str.lower().tolist()
        assert not any("egg" in n for n in names)
        assert "halwa" in result["food_name"].str.lower().tolist(), \
            "P2: halwa must remain (no diabetes filter)"

    def test_path3_allergy_and_diabetes(self, foods):
        """P3: egg allergy + diabetes → egg foods AND sweets removed."""
        result = apply_all_filters(
            foods, {"allergies": ["egg"], "health_conditions": ["diabetes"]})
        names = result["food_name"].str.lower().tolist()
        assert not any("egg" in n for n in names)
        assert "halwa" not in names
        assert "chicken biryani" not in names

    def test_path4_all_conditions_KNOWN_FAIL(self, foods):
        """
        P4: egg + gluten + dairy + diabetes + hypertension  — KNOWN FAIL
        Root cause: stacking 5 filters on a 20-food dataset eliminates
        every item. Fix: add constraint-relaxation fallback (remove least
        critical filter when pool < 3 items).
        """
        result = apply_all_filters(foods, {
            "allergies":        ["egg", "gluten", "dairy"],
            "health_conditions": ["diabetes", "hypertension"],
        })
        print(f"\n[P4] Foods remaining: {result['food_name'].tolist()}")
        # This FAILS intentionally — documents the known bug
        assert len(result) > 0, (
            "P4 KNOWN FAIL: All filters combined eliminated entire food dataset. "
            "Fix: add constraint-relaxation fallback when pool < 3 items."
        )


# ════════════════════════════════════════════════════════════════
#  LOOP TESTS  (inner for-loop over allergies list)
# ════════════════════════════════════════════════════════════════
class TestLoopCoverage:

    def test_loop_zero_iterations(self, foods):
        """Skip: empty list → no iteration, all foods returned."""
        result = filter_by_allergies(foods, [])
        assert len(result) == len(foods)

    def test_loop_one_iteration(self, foods):
        """One pass: single allergen removed correctly."""
        result = filter_by_allergies(foods, ["egg"])
        assert all("egg" not in n and "omelette" not in n
                   for n in result["food_name_lower"].tolist())

    def test_loop_two_iterations(self, foods):
        """Two passes: two allergens both removed."""
        result = filter_by_allergies(foods, ["egg", "seafood"])
        for name in result["food_name_lower"]:
            assert "egg" not in name and "fish" not in name \
                   and "shrimp" not in name

    def test_loop_three_iterations(self, foods):
        """Three passes: three allergens removed."""
        result = filter_by_allergies(foods, ["egg", "dairy", "nuts"])
        for name in result["food_name_lower"]:
            assert "egg" not in name
            assert "yogurt" not in name
            assert "halwa" not in name
            assert "kheer" not in name
