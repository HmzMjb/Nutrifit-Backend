import pytest
import os
import sys
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from exercise_plan import exercise_plan, exercise_plan_route
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
def test_exercise_plan_fail_zero_math_division():
    planner = exercise_plan()
    profile = {'target_goal': 'weight loss', 'activity_level': 'sedentary', 'timeline_weeks': 4}
    planner.generate_exercise_plan(profile, days=0)
def test_exercise_plan_fail_missing_target_key():
    planner = exercise_plan()
    profile = {'activity_level': 'sedentary', 'timeline_weeks': 4}
    planner.generate_exercise_plan(profile)

def test_exercise_plan_fail_int_instead_of_string():
    planner = exercise_plan()
    profile = {'target_goal': 70, 'activity_level': 'sedentary', 'timeline_weeks': 4}
    planner.generate_exercise_plan(profile)
