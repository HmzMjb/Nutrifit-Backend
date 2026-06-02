import pytest
from unittest.mock import patch
import os
import sys
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from meal_snap import meal_snap
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
    with pytest.raises(FileNotFoundError):
        model._img_to_feature_path("C:/fake_image_file.jpg")
@patch('meal_snap.meal_snap._init_model')
@patch('meal_snap.meal_snap._build_prototypes')
@patch('meal_snap.meal_snap._load_food_csv')
def test_meal_snap_fail_image_byte_corruption(m1, m2, m3):
    model = meal_snap()
    model._img_to_feature_bytes(b"some_random_corrupted_hex_bytes")

@patch('meal_snap.meal_snap._init_model')
@patch('meal_snap.meal_snap._build_prototypes')
@patch('meal_snap.meal_snap._load_food_csv')
def test_meal_snap_fail_invalid_math_types(m1, m2, m3):
    model = meal_snap()
    model.prototypes = None
    with patch.object(model, '_img_to_feature_bytes', return_value=True):
        with patch('torch.matmul'):
            with patch('torch.argmax', return_value=0):
                model.proto_labels = ["Pizza"]
                with patch.object(model, '_find_food_row', return_value={'meal_id': 1, 'calories': 500, 'protein_g': 10, 'carbs_g': 50, 'fat_g': 20}):
                    model.estimate(b"fake_image", quantity_g="Unlimited")
