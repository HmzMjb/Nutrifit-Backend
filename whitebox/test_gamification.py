import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gamification import calculate_level, calculate_level_data, get_level_badge, update_streak
def test_gamification_level_calculation_pass():
    result = calculate_level(500)
    assert result == 2
def test_gamification_level_data_pass():
    level, progress = calculate_level_data(750)
    assert level == 2
    assert progress == 0.25 # (250 / 1000)
def test_gamification_badge_pass():
    badge = get_level_badge(2)
    assert badge == "bronze"
    badge2 = get_level_badge(5)
    assert badge2 == "silver"
def test_gamification_fail_invalid_date_format():
    update_streak(5, "Not-A-Date")
def test_gamification_fail_math_types():
    """Whitebox Fatal Crash: Sending structural arrays into pure Integer subtraction loops."""
    with pytest.raises(TypeError):
        calculate_level([500, 100])
