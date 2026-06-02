import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from track_progress import clean_numpy, TrackProgress

def test_clean_numpy_pass():
    data = {"points": 45.1234, "active": True}
    res = clean_numpy(data)
    assert res["points"] == 45.12
    assert res["active"] is True
def test_track_progress_init_pass():
    data = {"period": "weekly", "meal_plan": {}}
    tp = TrackProgress(data)
    assert tp.period == "weekly"

def test_track_progress_fail_malformed_string_logic():
    data = {"profile_updated_at": "seconds="}
    # IndexError: list index out of range because there is no comma to split on
    with pytest.raises(IndexError):
        TrackProgress(data)
def test_track_progress_fail_iterable_dictionary():
    """Whitebox Fatal Crash: Feeding strings into an array expecting dictionaries."""
    data = {
        "eaten_foods": ["Apple", "Orange"] # Expects dicts with .get(), will throw AttributeError on string
    }
    tp = TrackProgress(data)
    # Crashes inherently when looping through eaten_foods because string has no .get()
    with pytest.raises(AttributeError):
        tp.weekly_progress()
