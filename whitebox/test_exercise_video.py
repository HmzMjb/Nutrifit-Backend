import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from exercise_video import get_suggestion, EXERCISE_CONFIG, first_line_CSV_file
def test_exercise_video_suggestion_pass():
    msg = get_suggestion("Models/Deadlift_rf.pkl", "up_back", "up_back")
    assert "Avoid leaning backward" in msg
    
def test_exercise_video_config_pass():
    bench = EXERCISE_CONFIG.get("Models/Bench_rf.pkl")
    assert bench is not None
    assert "up_close" in bench["ups"]
def test_exercise_video_fail_file_writer():
    with pytest.raises(PermissionError):
        first_line_CSV_file("C:/Restricted/coords.csv", bench=True)
        
def test_exercise_video_fail_dictionary_iteration():
    # Direct access fail without .get fallback
    with pytest.raises(KeyError):
        fake_dict = {}
        target = fake_dict["Models/Invalid_rf.pkl"]
