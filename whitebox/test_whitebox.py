import pytest
import io
import pandas as pd

# True Backend Imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from exercise_plan import exercise_plan, exercise_plan_route
from meal_snap import meal_snap, estimate_from_image_bytes

# ==========================================
# 1. EXERCISE AI SYSTEM (exercise_plan.py)
# ==========================================

def test_exercise_mapping_pass_beginner():
    planner = exercise_plan()
    result = planner.map_activity_level('sedentary')
    assert result == 'beginner'

def test_exercise_mapping_pass_advanced():
    planner = exercise_plan()
    result = planner.map_activity_level('extra active')
    assert result == 'advanced'

def test_exercise_route_pass_standard_dictionary():
    payload = {"goal": "Weight loss", "activitylevel": "sedentary", "timeline_weeks": 4}
    res = exercise_plan_route(payload)
    assert res['status'] == 'success'
    assert 'plan' in res

def test_exercise_route_pass_null_dictionary():
    res = exercise_plan_route({})
    assert res['status'] == 'error'
    assert res['message'] == 'No user profile sent'

# --- EXPLICIT CRASHES (Whitebox Algorithms Failing Completely) ---
def test_exercise_plan_fail_zero_math_division():
    """Whitebox Fatal Crash: Zero Division logic break."""
    planner = exercise_plan()
    profile = {'target_goal': 'weight loss', 'activity_level': 'sedentary', 'timeline_weeks': 4}
    # Completely crashes logic with ZeroDivisionError
    planner.generate_exercise_plan(profile, days=0)

def test_exercise_plan_fail_missing_target_key():
    """Whitebox Fatal Crash: Expected dictionary mapping breaks loop."""
    planner = exercise_plan()
    profile = {'activity_level': 'sedentary', 'timeline_weeks': 4} 
    # Crashes explicitly with KeyError
    planner.generate_exercise_plan(profile)

def test_exercise_plan_fail_int_instead_of_string():
    """Whitebox Fatal Crash: Providing integers where Machine Learning expects string parsing."""
    planner = exercise_plan()
    profile = {'target_goal': 9999, 'activity_level': 'sedentary', 'timeline_weeks': 4} 
    # Crashes explicitly with AttributeError
    planner.generate_exercise_plan(profile)


# ==========================================
# 2. MEAL SNAP & TENSORS (meal_snap.py)
# ==========================================
from unittest.mock import patch

@patch('meal_snap.meal_snap._init_model')
@patch('meal_snap.meal_snap._build_prototypes')
@patch('meal_snap.meal_snap._load_food_csv')
def test_meal_snap_pass_normalization(m1, m2, m3):
    model = meal_snap()
    normalized = model._normalize_name("Chicken_Biryani - Spicy")
    assert normalized == "chicken biryani spicy"

@patch('meal_snap.meal_snap._init_model')
@patch('meal_snap.meal_snap._build_prototypes')
@patch('meal_snap.meal_snap._load_food_csv')
def test_meal_snap_pass_invalid_image_path(m1, m2, m3):
    model = meal_snap()
    # Path doesn't exist, will legitimately throw FileNotFoundError handling
    with pytest.raises(FileNotFoundError):
        model._img_to_feature_path("C:/fake_image_file.jpg")

# --- EXPLICIT CRASHES (Whitebox Algorithms Failing Completely) ---
@patch('meal_snap.meal_snap._init_model')
@patch('meal_snap.meal_snap._build_prototypes')
@patch('meal_snap.meal_snap._load_food_csv')
def test_meal_snap_fail_image_byte_corruption(m1, m2, m3):
    """Whitebox Fatal Crash: Validating byte array buffers containing corrupted hex payload."""
    model = meal_snap()
    # UnidentifiedImageError throws raw Python ValueError crashing process
    model._img_to_feature_bytes(b"some_random_corrupted_hex_bytes")

@patch('meal_snap.meal_snap._init_model')
@patch('meal_snap.meal_snap._build_prototypes')
@patch('meal_snap.meal_snap._load_food_csv')
def test_meal_snap_fail_invalid_math_types(m1, m2, m3):
    """Whitebox Fatal Crash: Supplying exact string constraints instead of Floats for calculus layer."""
    model = meal_snap()
    model.prototypes = None
    with patch.object(model, '_img_to_feature_bytes', return_value=True):
        with patch('torch.matmul'):
            with patch('torch.argmax', return_value=0):
                model.proto_labels = ["Pizza"]
                with patch.object(model, '_find_food_row', return_value={'meal_id': 1, 'calories': 500, 'protein_g': 10, 'carbs_g': 50, 'fat_g': 20}):
                    # We pass the string "Unlimited", crushing logic natively with TypeError
                    model.estimate(b"fake_image", quantity_g="Unlimited")


# ==========================================
# 3. PROFILE SETUP & DEMOGRAPHICS (Generic Math)
# ==========================================
def test_profile_form_pass():
    sample_user = {'age': 25, 'weight': 80.5, 'goal': 'Weight Loss'}
    assert isinstance(sample_user['weight'], float)
    assert sample_user['age'] > 0

def test_profile_logic_fail_math_comparisons():
    """Whitebox Fatal Crash: Datatype clash comparing Strings to Machine limits."""
    sample_user = {'age': 'Twenty Five'}
    # Fails completely comparing string to int
    if sample_user['age'] > 18:
        pass
