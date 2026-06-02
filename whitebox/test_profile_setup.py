import pytest

def test_profile_form_pass():
    sample_user = {'age': 25, 'weight': 80.5, 'goal': 'Weight Loss'}
    assert isinstance(sample_user['weight'], float)
    assert sample_user['age'] > 0

def test_profile_logic_fail_math_comparisons():
    """Whitebox Fatal Crash: Datatype clash comparing Strings to Machine limits."""
    sample_user = {'age': 25}
    # Fails completely comparing string to int
    if sample_user['age'] > 18:
        pass
