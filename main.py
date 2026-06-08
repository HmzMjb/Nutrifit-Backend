from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()
from chatbot import chatbot
from cheatmeal import cheatmeal_route
from exercise_plan import exercise_plan_route

from gamification import gamification_sync_route
from datetime import datetime
from profile_setup import profile_setup_route, profile_validate

from meal_plan import generate_meal_plan_route
from track_progress import TrackProgress

app = Flask(__name__)
import threading
from meal_snap import get_model
threading.Thread(target=get_model, daemon=True).start()
CORS(app)


@app.route("/profile_validate", methods=["POST"])
def handle_profile_validate():
    try:
        return profile_validate()

    except Exception as e:
        app.logger.exception("Profile validation error")

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/profile_setup", methods=["POST"])
def handle_profile_setup_endpoint():
    try:
        user_data = request.get_json()
        print(user_data)
        result = profile_setup_route()
        print(result)
        return result
    except Exception as e:
        app.logger.error(f"Error in profile setup: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/meal_snap", methods=["POST"])
def predict():
    from meal_snap import estimate_from_image_bytes
    file = request.files.get("meal_image")
    if file is None:
        return jsonify({"error": "No file provided"}), 400

    quantity_g_raw = request.form.get("quantity_g", None)
    quantity_g = float(quantity_g_raw) if quantity_g_raw else None  # ← None jab empty

    image_bytes = file.read()

    try:
        result = estimate_from_image_bytes(image_bytes, quantity_g)
        print("Prediction result:", result)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/meal_plan", methods=["POST"])
def meal_plan_endpoint():
    try:
        user_data = request.get_json()
        print(user_data)
        result = generate_meal_plan_route(user_data)
        print(result)
        return jsonify(result)
    except Exception as e:
        app.logger.error("Meal plan ERROR:", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
@app.route("/cheatmeal", methods=["POST"])
def cheatmeal_endpoint():
    try:
        data = request.get_json()
        print("Cheat meal request:", data)

        result = cheatmeal_route(data)
        print("Cheat meal result:", result)

        status_code = 200 if result.get("status") != "error" else 500
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/gamification", methods=["POST"])
def gamification_endpoint():
    try:
        data = request.get_json()
        print("Gamification data:", data)

        result = gamification_sync_route(data)
        print(result)

        status_code = 200 if result.get("status") == "success" else 500
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
@app.route("/exercise_plan", methods=["POST"])
def exercise_plan_endpoint():
    user_data = request.get_json()
    print(user_data)
    result = exercise_plan_route(user_data)
    print(result)
    status_code = 200 if result.get("status") == "success" else 500
    return jsonify(result), status_code


@app.route("/exercise_video", methods=["POST"])
def handle_exercise_video_endpoint():
    from exercise_video import process_video
    try:
         file = request.files.get("video")
         print(request.files)

         if file is None:
             return jsonify({"error": "No video"}), 400
        # ── Read exercise type sent from Flutter ──────────────────
         exercise = request.form.get("exercise", "bench")
         model_map = {
             "bench": "Models/Bench_rf.pkl",
             "deadlift": "Models/Deadlift_rf.pkl",
             "squat": "Models/Squat_rf.pkl",
         }
         model_path = model_map.get(exercise.lower(), "Models/Bench_rf.pkl")
         print(f"Exercise: {exercise} → Model: {model_path}")
#         # ──────────────────────────────────────────────────────────

         import tempfile, os

         with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
             file.save(tmp.name)
             tmp_path = tmp.name

         try:
             result = process_video(tmp_path, model_path=model_path)
         finally:
             os.remove(tmp_path)

         return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/chatbot", methods=["POST"])
def chatbot_endpoint():
    data = request.get_json()
    print(data)
    result = chatbot.generate_chat_response(data)
    print(result)
    return jsonify(result)

@app.route("/track_progress", methods=["POST"])
def track_progress_endpoint():
    try:
        data = request.get_json()
        print(data)
        tracker = TrackProgress(data)
        result = tracker.track_progress()
        print(result)

        adaptive = result.get("adaptivePlan", {})

        new_meal_plan = None
        new_meal_plan_updated_at = None

        if adaptive.get("should_regenerate"):
            user_profile = {
                "age": data.get("age"),
                "weight_kg": data.get("weight"),
                "height_cm": data.get("height_cm"),
                "gender": data.get("gender"),
                "activity_level": data.get("activitylevel"),
                "target_goal": data.get("goal"),
                "health_condition": data.get("health_condition", []),
                "allergies": data.get("allergies", []),
            }
            meal_response = generate_meal_plan_route(user_profile)
            if meal_response.get("status") == "success":
                new_meal_plan = meal_response.get("meal_plan")
                new_meal_plan_updated_at = datetime.now().isoformat()

        return jsonify({
            "status": "success",
            **result,
            "new_meal_plan": new_meal_plan,
            "new_meal_plan_updated_at": new_meal_plan_updated_at,
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)