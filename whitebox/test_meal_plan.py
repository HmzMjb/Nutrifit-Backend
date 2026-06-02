import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from meal_plan import generate_meal_plan_route, BREAKFAST_FOODS
def test_meal_plan_constants_pass():
    assert "Oats" in BREAKFAST_FOODS
    assert "Apple" in BREAKFAST_FOODS
def test_meal_plan_route_clean_empty():
    res = generate_meal_plan_route({"health_condition": "", "allergies": ""})
    assert "status" in res
def test_meal_plan_fail_split_method():
    payload = {
        "health_condition": 404 # Expects a comma separated string like "diabetes, hypertension"
    }
    with pytest.raises(AttributeError):
        generate_meal_plan_route(payload)
def test_meal_plan_fail_allergy_split_method():
    payload = {
        "allergies": ["Peanuts"]
    }
    pass
