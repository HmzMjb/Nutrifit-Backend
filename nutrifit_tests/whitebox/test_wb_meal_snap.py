# whitebox/test_wb_chatbot.py
# ─────────────────────────────────────────────────────────────────────────────
# White-box tests for chatbot module
# Covers: intent detection branches, response generation, history management,
#         empty input handling, multi-turn loop, user isolation
# ─────────────────────────────────────────────────────────────────────────────
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fixtures"))
from mock_backend import (
    detect_intent, generate_chatbot_response,
    get_chat_history, clear_chat_history, count_chat_turns,
    INTENT_MAP,
)

# ══════════════════════════════════════════════════════════════════════════════
# TestDetectIntent  — branch coverage for every intent + default
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectIntent:

    @pytest.mark.parametrize("message,expected_intent", [
        # meal branch
        ("What should I eat today?",         "meal"),
        ("Give me a healthy diet plan",       "meal"),
        ("How many calories in this food?",   "meal"),
        ("I am hungry, suggest nutrition",    "meal"),
        # exercise branch
        ("Plan my workout for today",         "exercise"),
        ("How many sets should I do at gym?", "exercise"),
        ("Show me a fitness training plan",   "exercise"),
        # bmi branch
        ("Calculate my BMI please",           "bmi"),
        ("Am I overweight for my height?",    "bmi"),
        # progress branch
        ("Show my progress history",          "progress"),
        ("I want to track my progress",        "progress"),
        # general / default branch
        ("Hello there!",                      "general"),
        ("What is NutriFit?",                 "general"),
        ("",                                  "general"),
    ])
    def test_intent_detection(self, message, expected_intent):
        """[WB-CB-01] Each keyword cluster maps to correct intent."""
        result = detect_intent(message)
        assert result == expected_intent, (
            f"WB-CB-01 FAIL: '{message}' → intent='{result}', expected='{expected_intent}'."
        )

    def test_all_intents_covered_in_map(self):
        """[WB-CB-02] INTENT_MAP contains meal, exercise, bmi, progress, general."""
        required = {"meal", "exercise", "bmi", "progress", "general"}
        assert required.issubset(INTENT_MAP.keys()), (
            f"WB-CB-02 FAIL: Missing intents in INTENT_MAP: {required - INTENT_MAP.keys()}."
        )

    def test_case_insensitive_detection(self):
        """[WB-CB-03] Intent detection is case-insensitive."""
        assert detect_intent("MEAL PLAN") == detect_intent("meal plan"), (
            "WB-CB-03 FAIL: Intent detection is case-sensitive."
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestGenerateChatbotResponse
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateChatbotResponse:

    def setup_method(self):
        clear_chat_history("bot_user_01")
        clear_chat_history("bot_user_02")

    def test_empty_message_returns_error(self):
        """[WB-CB-04] Empty message returns error dict."""
        result = generate_chatbot_response("bot_user_01", "")
        assert "error" in result, "WB-CB-04 FAIL: Empty message should return error dict."

    def test_whitespace_only_returns_error(self):
        """[WB-CB-05] Whitespace-only message returns error dict."""
        result = generate_chatbot_response("bot_user_01", "   ")
        assert "error" in result, "WB-CB-05 FAIL: Whitespace message should return error."

    def test_valid_message_returns_response_key(self):
        """[WB-CB-06] Valid message returns dict with 'response' key."""
        result = generate_chatbot_response("bot_user_01", "What should I eat?")
        assert "response" in result, "WB-CB-06 FAIL: Missing 'response' key."

    def test_valid_message_returns_intent_key(self):
        """[WB-CB-07] Valid message returns dict with 'intent' key."""
        result = generate_chatbot_response("bot_user_01", "Plan my workout")
        assert "intent" in result, "WB-CB-07 FAIL: Missing 'intent' key."

    def test_response_is_nonempty_string(self):
        """[WB-CB-08] Response text is a non-empty string."""
        result = generate_chatbot_response("bot_user_01", "Hello NutriFit")
        assert isinstance(result.get("response"), str), "WB-CB-08 FAIL: Response not a string."
        assert len(result["response"].strip()) > 0,     "WB-CB-08 FAIL: Response is empty."

    def test_intent_matches_detect_intent(self):
        """[WB-CB-09] Intent in response matches standalone detect_intent result."""
        msg    = "How many calories in my food?"
        result = generate_chatbot_response("bot_user_01", msg)
        assert result["intent"] == detect_intent(msg), (
            "WB-CB-09 FAIL: Intent in response doesn't match detect_intent()."
        )

    def test_user_id_in_response(self):
        """[WB-CB-10] Response dict includes correct user_id."""
        result = generate_chatbot_response("bot_user_01", "Track my progress")
        assert result.get("user_id") == "bot_user_01", (
            "WB-CB-10 FAIL: user_id missing or wrong in response."
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestChatHistory  — loop + isolation
# ══════════════════════════════════════════════════════════════════════════════

class TestChatHistory:

    def setup_method(self):
        clear_chat_history("bot_user_01")
        clear_chat_history("bot_user_02")

    def test_history_empty_for_new_user(self):
        """[WB-CB-11] Fresh user starts with empty chat history."""
        assert get_chat_history("new_user_xyz_999") == [], (
            "WB-CB-11 FAIL: New user should have empty history."
        )

    def test_single_message_adds_two_entries(self):
        """[WB-CB-12] One message → 1 user entry + 1 bot entry in history."""
        generate_chatbot_response("bot_user_01", "Hello")
        history = get_chat_history("bot_user_01")
        assert len(history) == 2, (
            f"WB-CB-12 FAIL: Expected 2 history entries, got {len(history)}."
        )
        assert history[0]["role"] == "user", "WB-CB-12 FAIL: First entry should be 'user'."
        assert history[1]["role"] == "bot",  "WB-CB-12 FAIL: Second entry should be 'bot'."

    def test_loop_five_messages_ten_history_entries(self):
        """[WB-CB-13] Loop: 5 messages → 10 history entries (5 user + 5 bot)."""
        messages = [
            "What should I eat?",
            "Plan my workout",
            "Calculate my BMI",
            "Show my progress",
            "Hello!",
        ]
        for msg in messages:
            generate_chatbot_response("bot_user_01", msg)
        history = get_chat_history("bot_user_01")
        assert len(history) == 10, (
            f"WB-CB-13 FAIL: Expected 10 entries, got {len(history)}."
        )

    def test_count_chat_turns_correct(self):
        """[WB-CB-14] count_chat_turns returns number of user messages sent."""
        for msg in ["Meal tip?", "Workout tip?", "My BMI?"]:
            generate_chatbot_response("bot_user_01", msg)
        turns = count_chat_turns("bot_user_01")
        assert turns == 3, f"WB-CB-14 FAIL: Expected 3 turns, got {turns}."

    def test_clear_history_resets_to_empty(self):
        """[WB-CB-15] clear_chat_history wipes all messages."""
        generate_chatbot_response("bot_user_01", "Hello")
        clear_chat_history("bot_user_01")
        assert get_chat_history("bot_user_01") == [], (
            "WB-CB-15 FAIL: History not cleared."
        )

    def test_two_users_history_isolated(self):
        """[WB-CB-16] Messages from user_01 do not appear in user_02 history."""
        generate_chatbot_response("bot_user_01", "Meal for user 1")
        generate_chatbot_response("bot_user_02", "Workout for user 2")
        h1 = get_chat_history("bot_user_01")
        h2 = get_chat_history("bot_user_02")
        user1_msgs = [m["content"] for m in h1]
        user2_msgs = [m["content"] for m in h2]
        assert "Meal for user 1"    not in user2_msgs, "WB-CB-16 FAIL: Cross-user history leak."
        assert "Workout for user 2" not in user1_msgs, "WB-CB-16 FAIL: Cross-user history leak."

    def test_history_entries_have_role_and_content(self):
        """[WB-CB-17] Every history entry has 'role' and 'content' keys."""
        generate_chatbot_response("bot_user_01", "Test message")
        for entry in get_chat_history("bot_user_01"):
            assert "role"    in entry, "WB-CB-17 FAIL: Missing 'role' in history entry."
            assert "content" in entry, "WB-CB-17 FAIL: Missing 'content' in history entry."