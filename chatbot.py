import os
import json
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

SYSTEM_PROMPT = """You are NutriFit AI, a personal nutrition and fitness coach.
You have access to the user's full profile including their meal plan, exercise plan,
and progress data. Give concise, personalized advice based on their data.
Always respond in the same language the user writes in."""


class Chatbot:
    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT
        )

    def generate_chat_response(self, data: dict) -> dict:
        user_profile = data.get("user_profile", {})
        message = data.get("message", "")

        profile_context = json.dumps(user_profile, indent=2, default=str)

        prompt = f"""User Profile & Data:
{profile_context}

User Question: {message}"""

        try:
            response = self.model.generate_content(prompt)
            return {"reply": response.text}
        except Exception as e:
            return {"reply": f"Sorry, I couldn't process your request. Error: {str(e)}"}


chatbot = Chatbot()