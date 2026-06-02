import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from chatbot import Chatbot
def test_chatbot_health_split_pass():
    bot = Chatbot()
    profile = {
        "healthConditions": ["allergy: Peanuts", "Asthma"]
    }
    clean_health, clean_allergies = bot.split_health_and_allergies(profile)
    assert "Peanuts" in clean_allergies
    assert "Asthma" in clean_health

def test_chatbot_system_prompt_pass():
    bot = Chatbot()
    profile = {"name": "TestUser", "goal": "muscle gain"}
    prompt = bot.build_system_prompt(profile, "Monday")
    assert "TestUser" in prompt
    assert "NutriFit AI Coach" in prompt

def test_chatbot_fail_string_logic():
    bot = Chatbot()
    profile = {"healthConditions": [{"allergy": "Peanuts"}]}
    with pytest.raises(AttributeError):
         bot.split_health_and_allergies(profile)
def test_chatbot_fail_flatten_plan_iterator():
    bot = Chatbot()
    plan = {"plan": {"Monday": {"meals": 404}}}
    with pytest.raises(AttributeError):
         bot.flatten_today_plan(plan, "Meal Plan", "Monday")
