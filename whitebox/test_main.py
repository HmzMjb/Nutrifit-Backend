import pytest
import sys
import os

os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ==========================================
# PASSING CASES (Endpoint Testing)
# ==========================================
def test_main_routing_pass_meal_snap(client):
    # Discovery test handling 400 natively for missing file buffer
    response = client.post('/meal_snap')
    assert response.status_code == 400


def test_main_routing_pass_gamification(client):
    response = client.post('/gamification', json={"xp": 100})
    assert response.status_code == 200


def test_main_routing_pass_chatbot(client):
    # Validate Ollama dictionary parser discovery
    response = client.post('/chatbot', json={"user_profile": {"name": "Test"}, "message": "hello"})
    assert response.status_code == 200


def test_main_routing_pass_exercise_plan(client):
    # Validate dataframe loading via client HTTP
    response = client.post('/exercise_plan',
                           json={"goal": "Weight loss", "activitylevel": "sedentary", "timeline_weeks": 4})
    assert response.status_code == 200


def test_main_routing_pass_track_progress(client):
    # Validate datetime conversion mapping in tracker
    response = client.post('/track_progress', json={"period": "weekly", "meal_plan": {}})
    assert response.status_code == 200


def test_main_routing_pass_exercise_video(client):
    # Tests Flask file boundary (400 if no video is appended over form-data)
    response = client.post('/exercise_video')
    assert response.status_code == 400


def test_main_fail_malformed_json_payload(client):
    """Whitebox Fatal Crash: Bypass Flask JSON deserializer."""
    # Send raw plaintext data instead of dict header
    response = client.post('/profile_setup', data="This is not json")
    assert response.status_code == 500


def test_main_fail_cheatmeal_null_values(client):
    """Whitebox Fatal Crash: Exploit Flask missing key casting."""
    # Sending None/Null throws unhandled float() math exceptions
    response = client.post('/cheatmeal', json={"weight_kg": None, "height_cm": None})
    assert response.status_code == 500


def test_main_fail_meal_plan_invalid(client):
    """Whitebox Fatal Crash: Send integers to break Health string parsing inside Flask."""
    # Ints don't have .split()
    response = client.post('/meal_plan', json={"health_condition": 404})
    assert response.status_code == 500
