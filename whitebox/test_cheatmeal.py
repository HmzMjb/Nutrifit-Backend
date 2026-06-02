import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cheatmeal import Goal, ActivityLevel, UserProfile
def test_cheatmeal_enums_pass():
    assert Goal.WEIGHT_LOSS.value == "weight_loss"
    assert ActivityLevel.SEDENTARY.value == 1.2
def test_cheatmeal_user_profile_math_pass():
    profile = UserProfile(
        user_id="U1", name="Test", age=25, weight_kg=80.0, height_cm=180.0,
        gender="Male", goal=Goal.WEIGHT_LOSS, activity_level=ActivityLevel.MODERATE
    )
    # Validates Mifflin-St Jeor math logic natively
    assert profile.bmr == 10 * 80.0 + 6.25 * 180.0 - 5 * 25 + 5
    assert profile.tdee == profile.bmr * 1.55
def test_cheatmeal_fail_dataclass_enforcement():
    """Whitebox Fatal Crash: Dataclasses inherently throwing TypeErrors for missing mandatory architectural properties."""
    with pytest.raises(TypeError):
        UserProfile(user_id="U2", name="Fail", age=25, weight_kg=80.0, height_cm=180.0, gender="Male")
def test_cheatmeal_fail_math_types():
    """Whitebox Fatal Crash: Intentionally crossing strings into float-based Mifflin-St Jeor equation."""
    with pytest.raises(TypeError):
        UserProfile(
            user_id="U3", name="Bad", age=20, weight_kg=80.0, height_cm=180.0,
            gender="Male", goal=Goal.WEIGHT_LOSS, activity_level=ActivityLevel.MODERATE
        )
