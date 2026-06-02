_FOODS = [
    {"name": "Chicken Breast",  "calories": 165, "protein": 31, "carbs": 0,  "fat": 3.6, "category": "protein",  "vegan": False, "gluten_free": True},
    {"name": "Brown Rice",      "calories": 216, "protein": 5,  "carbs": 45, "fat": 1.8, "category": "carbs",    "vegan": True,  "gluten_free": True},
    {"name": "Broccoli",        "calories": 55,  "protein": 3.7,"carbs": 11, "fat": 0.6, "category": "vegetable","vegan": True,  "gluten_free": True},
    {"name": "Salmon",          "calories": 208, "protein": 20, "carbs": 0,  "fat": 13,  "category": "protein",  "vegan": False, "gluten_free": True},
    {"name": "Whole Wheat Bread","calories": 247,"protein": 13, "carbs": 41, "fat": 3.4, "category": "carbs",    "vegan": True,  "gluten_free": False},
    {"name": "Greek Yogurt",    "calories": 100, "protein": 17, "carbs": 6,  "fat": 0.7, "category": "dairy",    "vegan": False, "gluten_free": True},
    {"name": "Almonds",         "calories": 579, "protein": 21, "carbs": 22, "fat": 50,  "category": "fat",      "vegan": True,  "gluten_free": True},
    {"name": "Banana",          "calories": 89,  "protein": 1.1,"carbs": 23, "fat": 0.3, "category": "fruit",    "vegan": True,  "gluten_free": True},
    {"name": "Egg",             "calories": 155, "protein": 13, "carbs": 1.1,"fat": 11,  "category": "protein",  "vegan": False, "gluten_free": True},
    {"name": "Oats",            "calories": 389, "protein": 17, "carbs": 66, "fat": 7,   "category": "carbs",    "vegan": True,  "gluten_free": False},
    {"name": "Lentils",         "calories": 116, "protein": 9,  "carbs": 20, "fat": 0.4, "category": "protein",  "vegan": True,  "gluten_free": True},
    {"name": "Avocado",         "calories": 160, "protein": 2,  "carbs": 9,  "fat": 15,  "category": "fat",      "vegan": True,  "gluten_free": True},
    {"name": "Tuna",            "calories": 144, "protein": 30, "carbs": 0,  "fat": 1,   "category": "protein",  "vegan": False, "gluten_free": True},
    {"name": "Pasta",           "calories": 371, "protein": 13, "carbs": 75, "fat": 1.5, "category": "carbs",    "vegan": True,  "gluten_free": False},
    {"name": "Cottage Cheese",  "calories": 98,  "protein": 11, "carbs": 3.4,"fat": 4.3, "category": "dairy",    "vegan": False, "gluten_free": True},
]

# ── EXERCISE DATA (mirrors excercise.csv) ─────────────────────────────────────
_EXERCISES = {
    "weight_loss": [
        {"name": "Jumping Jacks", "sets": 3, "reps": 20, "duration_min": 10},
        {"name": "Burpees",       "sets": 3, "reps": 10, "duration_min": 8},
        {"name": "Mountain Climbers","sets": 3,"reps": 15,"duration_min": 7},
        {"name": "High Knees",    "sets": 3, "reps": 30, "duration_min": 5},
    ],
    "weight_gain": [
        {"name": "Bench Press",   "sets": 4, "reps": 8,  "duration_min": 12},
        {"name": "Deadlift",      "sets": 4, "reps": 6,  "duration_min": 15},
        {"name": "Squats",        "sets": 4, "reps": 10, "duration_min": 10},
        {"name": "Pull-ups",      "sets": 3, "reps": 8,  "duration_min": 8},
    ],
    "maintenance": [
        {"name": "Jogging",       "sets": 1, "reps": 1,  "duration_min": 30},
        {"name": "Push-ups",      "sets": 3, "reps": 15, "duration_min": 8},
        {"name": "Plank",         "sets": 3, "reps": 1,  "duration_min": 5},
        {"name": "Cycling",       "sets": 1, "reps": 1,  "duration_min": 25},
    ],
}

GOAL_SYNONYMS = {

}

# ══════════════════════════════════════════════════════════════════════════════
# exercise_plan.py  (mock)
# ══════════════════════════════════════════════════════════════════════════════

def map_activity_level(level: str) -> str:
    """Map free-text activity level → 'beginner' | 'advanced'."""
    _map = {
        "sedentary":        "beginner",
        "lightly active":   "beginner",
        "moderately active":"advanced",
        "very active":      "advanced",
        "extra active":     "advanced",
    }
    return _map.get(level.lower(), "beginner")


def adjust_exercise(exercise: dict, level: str, timeline_weeks: int) -> dict:
    """Return a copy of exercise with sets/reps adjusted for level & timeline."""
    ex = exercise.copy()
    if level == "beginner":
        ex["sets"] = max(1, int(ex["sets"] * 0.75))
        ex["reps"] = max(1, int(ex["reps"] * 0.75))
    else:
        ex["sets"] = int(ex["sets"] * 1.1)
        ex["reps"] = int(ex["reps"] * 1.1)
    if timeline_weeks <= 4:
        ex["sets"] = ex["sets"] + 1
    return ex


def generate_exercise_plan(goal: str, activity_level: str,
                            timeline_weeks: int = 8, days: int = 7) -> dict:
    """Return a {day: [exercises]} plan or {'error': '...'} for unknown goal."""
    # Synonym normalisation (currently empty — WB-TC-07 fix goes here)
    canonical = GOAL_SYNONYMS.get(goal.lower(), goal.lower())
    exercises = _EXERCISES.get(canonical)
    if exercises is None:
        return {"error": f"No exercises found for goal '{goal}'."}

    level = map_activity_level(activity_level)
    plan = {}
    for day in range(1, days + 1):
        plan[f"day_{day}"] = [
            adjust_exercise(ex, level, timeline_weeks)
            for ex in exercises
        ]
    return plan


# ══════════════════════════════════════════════════════════════════════════════
# meal_plan.py / foods filter  (mock)
# ══════════════════════════════════════════════════════════════════════════════

def filter_foods(
    category: str | None = None,
    max_calories: int | None = None,
    min_protein: float | None = None,
    vegan: bool | None = None,
    gluten_free: bool | None = None,
) -> list[dict]:
    """Filter _FOODS by the supplied criteria (all optional)."""
    results = list(_FOODS)
    if category is not None:
        results = [f for f in results if f["category"] == category]
    if max_calories is not None:
        results = [f for f in results if f["calories"] <= max_calories]
    if min_protein is not None:
        results = [f for f in results if f["protein"] >= min_protein]
    if vegan is not None:
        results = [f for f in results if f["vegan"] == vegan]
    if gluten_free is not None:
        results = [f for f in results if f["gluten_free"] == gluten_free]
    return results


def calculate_daily_calories(weight_kg: float, height_cm: float,
                              age: int, gender: str, goal: str) -> float:
    """Harris-Benedict BMR → TDEE → goal adjustment."""
    if gender.lower() == "male":
        bmr = 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)
    tdee = bmr * 1.55  # moderate activity default
    adjustments = {"weight_loss": -500, "weight_gain": +500, "maintenance": 0}
    return tdee + adjustments.get(goal.lower(), 0)


def generate_meal_plan(goal: str, daily_calories: float,
                        vegan: bool = False, gluten_free: bool = False) -> dict:
    """Return a simple 3-meal plan dict."""
    foods = filter_foods(vegan=vegan if vegan else None,
                         gluten_free=gluten_free if gluten_free else None)
    if not foods:
        return {"error": "No foods match dietary preferences."}
    protein_foods = [f for f in foods if f["category"] == "protein"]
    carb_foods    = [f for f in foods if f["category"] == "carbs"]
    fat_foods     = [f for f in foods if f["category"] == "fat"]
    return {
        "breakfast": {"food": carb_foods[0]["name"]    if carb_foods    else "Oats",   "calories": daily_calories * 0.25},
        "lunch":     {"food": protein_foods[0]["name"] if protein_foods else "Chicken", "calories": daily_calories * 0.40},
        "dinner":    {"food": protein_foods[1]["name"] if len(protein_foods) > 1 else protein_foods[0]["name"] if protein_foods else "Egg",
                      "calories": daily_calories * 0.35},
    }


# ══════════════════════════════════════════════════════════════════════════════
# profile_setup.py  (mock)
# ══════════════════════════════════════════════════════════════════════════════

def calculate_bmi(weight_kg: float, height_ft: float) -> dict:
    """Return BMI value + label.  height in decimal feet (e.g. 5.6)."""
    if weight_kg <= 0:
        raise ValueError("Weight must be positive.")
    if height_ft <= 0:
        raise ValueError("Height must be positive.")
    height_m = height_ft * 0.3048
    bmi = weight_kg / (height_m ** 2)
    if bmi < 18.5:
        label = "Underweight"
    elif bmi < 25:
        label = "Normal"
    elif bmi < 30:
        label = "Overweight"
    else:
        label = "Obese"
    return {"bmi": round(bmi, 2), "label": label}


# ══════════════════════════════════════════════════════════════════════════════
# track_progress.py  (mock)
# ══════════════════════════════════════════════════════════════════════════════

_progress_store: dict[str, list] = {}

def log_progress(user_id: str, date: str, weight_kg: float,
                  calories_consumed: float, workout_done: bool) -> dict:
    entry = {
        "date": date,
        "weight_kg": weight_kg,
        "calories_consumed": calories_consumed,
        "workout_done": workout_done,
    }
    _progress_store.setdefault(user_id, []).append(entry)
    return {"status": "logged", "entry": entry}


def get_progress(user_id: str) -> list:
    return _progress_store.get(user_id, [])


def clear_progress(user_id: str) -> None:
    _progress_store.pop(user_id, None)


def calculate_weekly_summary(user_id: str) -> dict:
    entries = get_progress(user_id)
    if not entries:
        return {"error": "No progress data found."}
    weights   = [e["weight_kg"] for e in entries]
    cals      = [e["calories_consumed"] for e in entries]
    workouts  = sum(1 for e in entries if e["workout_done"])
    return {
        "avg_weight_kg":         round(sum(weights) / len(weights), 2),
        "weight_change_kg":      round(weights[-1] - weights[0], 2),
        "avg_daily_calories":    round(sum(cals) / len(cals), 2),
        "workouts_completed":    workouts,
        "adherence_pct":         round((workouts / len(entries)) * 100, 1),
    }


# ══════════════════════════════════════════════════════════════════════════════
# gamification.py  (mock)
# ══════════════════════════════════════════════════════════════════════════════

_points_store: dict[str, int] = {}

POINT_RULES = {
    "workout_done":       50,
    "calories_on_target": 30,
    "weight_logged":      10,
    "streak_7_days":     100,
}

def award_points(user_id: str, event: str) -> dict:
    pts = POINT_RULES.get(event, 0)
    _points_store[user_id] = _points_store.get(user_id, 0) + pts
    return {"user_id": user_id, "event": event, "points_awarded": pts,
            "total_points": _points_store[user_id]}

def get_leaderboard() -> list[dict]:
    board = sorted(_points_store.items(), key=lambda x: x[1], reverse=True)
    return [{"rank": i+1, "user_id": uid, "points": pts}
            for i, (uid, pts) in enumerate(board)]

def get_user_points(user_id: str) -> int:
    return _points_store.get(user_id, 0)

def reset_points(user_id: str) -> None:
    _points_store.pop(user_id, None)


# ══════════════════════════════════════════════════════════════════════════════
# cheatmeal.py  (mock)
# ══════════════════════════════════════════════════════════════════════════════

_CHEATMEALS = {
    "weight_loss": [
        {"name": "Margherita Pizza (1 slice)", "calories": 285, "frequency": "once_a_week"},
        {"name": "Dark Chocolate (30g)",        "calories": 170, "frequency": "twice_a_week"},
    ],
    "weight_gain": [
        {"name": "Double Burger",              "calories": 700, "frequency": "once_a_week"},
        {"name": "Milkshake (large)",          "calories": 550, "frequency": "once_a_week"},
    ],
    "maintenance": [
        {"name": "Fish & Chips",               "calories": 800, "frequency": "once_a_week"},
        {"name": "Ice Cream (2 scoops)",       "calories": 280, "frequency": "twice_a_week"},
    ],
}

def get_cheatmeal_plan(goal: str) -> list[dict]:
    return list(_CHEATMEALS.get(goal.lower(), []))


# ══════════════════════════════════════════════════════════════════════════════
# cheatmeal.py  — extended mock
# ══════════════════════════════════════════════════════════════════════════════

CHEATMEAL_FREQUENCY_RULES = {
    "once_a_week":   1,
    "twice_a_week":  2,
    "daily":         7,
}

def validate_cheatmeal_frequency(frequency: str) -> bool:
    return frequency in CHEATMEAL_FREQUENCY_RULES

def cheatmeal_weekly_extra_calories(goal: str) -> float:
    """Sum of (calories * weekly_frequency) for all cheat meals of a goal."""
    meals = get_cheatmeal_plan(goal)
    if not meals:
        return 0.0
    total = 0.0
    for m in meals:
        freq = CHEATMEAL_FREQUENCY_RULES.get(m.get("frequency", "once_a_week"), 1)
        total += m["calories"] * freq
    return total


# ══════════════════════════════════════════════════════════════════════════════
# chatbot.py  — mock
# ══════════════════════════════════════════════════════════════════════════════

_CHAT_HISTORY: dict[str, list] = {}

INTENT_MAP = {
    "meal":     ["eat", "food", "meal", "diet", "nutrition", "calorie", "hungry"],
    "exercise": ["workout", "exercise", "gym", "training", "fitness", "sets", "reps"],
    "bmi":      ["bmi", "weight", "height", "overweight", "underweight", "obese"],
    "progress": ["progress", "track", "history", "summary", "log my"],
    "general":  [],
}

def detect_intent(message: str) -> str:
    msg = message.lower()
    for intent, keywords in INTENT_MAP.items():
        if any(kw in msg for kw in keywords):
            return intent
    return "general"

def generate_chatbot_response(user_id: str, message: str) -> dict:
    """Return intent-aware response and update chat history."""
    if not message or not message.strip():
        return {"error": "Message cannot be empty."}
    intent   = detect_intent(message)
    replies  = {
        "meal":     "Here are some healthy meal suggestions based on your goal.",
        "exercise": "I recommend starting with 3 sets of 10 reps for each exercise.",
        "bmi":      "Your BMI helps determine the right plan. Please provide weight and height.",
        "progress": "You can track your progress in the Track Progress section.",
        "general":  "I'm your NutriFit assistant. Ask me about meals, exercises, or BMI!",
    }
    response = {"intent": intent, "response": replies[intent], "user_id": user_id}
    _CHAT_HISTORY.setdefault(user_id, []).append(
        {"role": "user", "content": message}
    )
    _CHAT_HISTORY[user_id].append(
        {"role": "bot", "content": replies[intent]}
    )
    return response

def get_chat_history(user_id: str) -> list:
    return _CHAT_HISTORY.get(user_id, [])

def clear_chat_history(user_id: str) -> None:
    _CHAT_HISTORY.pop(user_id, None)

def count_chat_turns(user_id: str) -> int:
    """Number of complete user-bot turn pairs."""
    history = get_chat_history(user_id)
    return len([m for m in history if m["role"] == "user"])


# ══════════════════════════════════════════════════════════════════════════════
# meal_snap.py  — mock  (photo → food recognition → nutrition)
# ══════════════════════════════════════════════════════════════════════════════

import random as _random

_RECOGNIZABLE_FOODS = {
    "pizza":   {"name": "Pizza",         "calories": 285, "protein": 12, "carbs": 36, "fat": 10},
    "burger":  {"name": "Burger",        "calories": 540, "protein": 25, "carbs": 40, "fat": 28},
    "salad":   {"name": "Green Salad",   "calories": 120, "protein": 3,  "carbs": 10, "fat": 7},
    "rice":    {"name": "Rice Bowl",     "calories": 350, "protein": 8,  "carbs": 72, "fat": 2},
    "chicken": {"name": "Grilled Chicken","calories": 165,"protein": 31, "carbs": 0,  "fat": 4},
    "oats":    {"name": "Oatmeal",       "calories": 150, "protein": 5,  "carbs": 27, "fat": 3},
}

MEAL_SNAP_CONFIDENCE_THRESHOLD = 0.70

def analyse_meal_snap(image_label: str, portion_multiplier: float = 1.0) -> dict:
    """
    Simulate image recognition.
    image_label : lowercase food keyword (mocks what CV model returns)
    portion_multiplier : 0.5 = half portion, 2.0 = double portion
    Returns nutrition dict or error if unrecognised / bad input.
    """
    if not image_label or not isinstance(image_label, str):
        return {"error": "Invalid image input."}
    if portion_multiplier <= 0:
        return {"error": "Portion multiplier must be positive."}

    food = _RECOGNIZABLE_FOODS.get(image_label.lower().strip())
    if food is None:
        return {"error": f"Food '{image_label}' not recognised. Try a clearer photo."}

    confidence = round(_random.uniform(0.72, 0.99), 2)   # always above threshold in mock
    scaled = {
        "name":       food["name"],
        "calories":   round(food["calories"]  * portion_multiplier),
        "protein":    round(food["protein"]   * portion_multiplier, 1),
        "carbs":      round(food["carbs"]     * portion_multiplier, 1),
        "fat":        round(food["fat"]       * portion_multiplier, 1),
        "confidence": confidence,
        "portion":    portion_multiplier,
    }
    return scaled

def batch_analyse_snaps(image_labels: list, portion_multiplier: float = 1.0) -> list:
    """Analyse multiple meal snaps; returns list of results."""
    return [analyse_meal_snap(lbl, portion_multiplier) for lbl in image_labels]

def snap_daily_totals(image_labels: list) -> dict:
    """Aggregate nutrition across all recognised snaps for the day."""
    results = batch_analyse_snaps(image_labels)
    totals  = {"calories": 0, "protein": 0.0, "carbs": 0.0, "fat": 0.0,
               "recognised": 0, "unrecognised": 0}
    for r in results:
        if "error" in r:
            totals["unrecognised"] += 1
        else:
            totals["recognised"]  += 1
            totals["calories"]    += r["calories"]
            totals["protein"]     += r["protein"]
            totals["carbs"]       += r["carbs"]
            totals["fat"]         += r["fat"]
    totals["protein"] = round(totals["protein"], 1)
    totals["carbs"]   = round(totals["carbs"],   1)
    totals["fat"]     = round(totals["fat"],      1)
    return totals


# ══════════════════════════════════════════════════════════════════════════════
# ADDITIONS — functions required by white-box test suite
# ══════════════════════════════════════════════════════════════════════════════

import time as _time

# ── Sample datasets ───────────────────────────────────────────────────────────

SAMPLE_FOODS = [
    {"name": "Chicken Breast",   "calories": 165, "protein": 31,  "carbs": 0,  "fat": 3.6,
     "category": "protein",   "vegan": False, "gluten_free": True},
    {"name": "Brown Rice",       "calories": 216, "protein": 5,   "carbs": 45, "fat": 1.8,
     "category": "carbs",     "vegan": True,  "gluten_free": True},
    {"name": "Broccoli",         "calories": 55,  "protein": 3.7, "carbs": 11, "fat": 0.6,
     "category": "vegetable", "vegan": True,  "gluten_free": True},
    {"name": "Salmon",           "calories": 208, "protein": 20,  "carbs": 0,  "fat": 13,
     "category": "protein",   "vegan": False, "gluten_free": True},
    {"name": "Whole Wheat Bread","calories": 247, "protein": 13,  "carbs": 41, "fat": 3.4,
     "category": "carbs",     "vegan": True,  "gluten_free": False},
    {"name": "Greek Yogurt",     "calories": 100, "protein": 17,  "carbs": 6,  "fat": 0.7,
     "category": "dairy",     "vegan": False, "gluten_free": True},
    {"name": "Almonds",          "calories": 579, "protein": 21,  "carbs": 22, "fat": 50,
     "category": "fat",       "vegan": True,  "gluten_free": True},
    {"name": "Lentils",          "calories": 116, "protein": 9,   "carbs": 20, "fat": 0.4,
     "category": "protein",   "vegan": True,  "gluten_free": True},
    {"name": "Oats",             "calories": 389, "protein": 17,  "carbs": 66, "fat": 7,
     "category": "carbs",     "vegan": True,  "gluten_free": False},
    {"name": "Egg",              "calories": 155, "protein": 13,  "carbs": 1.1,"fat": 11,
     "category": "protein",   "vegan": False, "gluten_free": True},
]

SAMPLE_EXERCISES = {
    "weight loss": [
        {"exercise_name": "Jumping Jacks", "sets": 3, "repetitions": 20, "duration": 10},
        {"exercise_name": "Burpees",        "sets": 3, "repetitions": 10, "duration": 8},
        {"exercise_name": "Mountain Climbers","sets": 3,"repetitions": 15,"duration": 7},
        {"exercise_name": "High Knees",     "sets": 3, "repetitions": 30, "duration": 5},
    ],
    "weight gain": [
        {"exercise_name": "Bench Press",    "sets": 4, "repetitions": 8,  "duration": 12},
        {"exercise_name": "Deadlift",       "sets": 4, "repetitions": 6,  "duration": 15},
        {"exercise_name": "Squats",         "sets": 4, "repetitions": 10, "duration": 10},
        {"exercise_name": "Pull-ups",       "sets": 3, "repetitions": 8,  "duration": 8},
    ],
    "maintain": [
        {"exercise_name": "Jogging",        "sets": 1, "repetitions": 1,  "duration": 30},
        {"exercise_name": "Push-ups",       "sets": 3, "repetitions": 15, "duration": 8},
        {"exercise_name": "Plank",          "sets": 3, "repetitions": 1,  "duration": 5},
        {"exercise_name": "Cycling",        "sets": 1, "repetitions": 1,  "duration": 25},
    ],
}

_GOAL_ALIAS = {
    "weight lose":        "weight loss",
    "lose weight":        "weight loss",
    "fat loss":           "weight loss",
    "bulk":               "weight gain",
    "muscle gain":        "weight gain",
    "maintenance":        "maintain",
    "body recomposition": "maintain",   # synonym normalisation (WB-TC-07 fix area)
}


# ── profile_setup.py helper mocks ─────────────────────────────────────────────

def calculate_bmr(weight_kg: float, height_ft: float, age: int, gender: str) -> float:
    """Mifflin-St Jeor BMR.  height in decimal feet."""
    height_cm = height_ft * 30.48
    if gender.lower() == "male":
        return (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        return (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """Return TDEE from BMR × activity multiplier (mirrors profile_setup.py)."""
    multipliers = {
        "sedentary":         1.2,
        "lightly active":    1.375,
        "moderately active": 1.55,
        "very active":       1.725,
        "extra active":      1.9,
    }
    return bmr * multipliers.get(activity_level.lower(), 1.2)


def validate_profile(data: dict) -> dict:
    """
    Validate required profile fields (mirrors profile_setup.validate_required_fields
    + parse_numeric_fields).  Returns dict of {field: error_message}.
    """
    REQUIRED = ["age", "weight", "height", "gender", "activitylevel", "goal"]
    errors: dict = {}

    for field in REQUIRED:
        if field not in data or data[field] in [None, ""]:
            errors[field] = "This field is required"

    # Numeric validation (only if field is present)
    if "age" not in errors:
        try:
            age = int(data["age"])
            if age <= 0:
                errors["age"] = "Age must be greater than 0"
        except (ValueError, TypeError):
            errors["age"] = "Age must be a valid number"

    if "weight" not in errors:
        try:
            w = float(data["weight"])
            if w <= 0:
                errors["weight"] = "Weight must be positive"
        except (ValueError, TypeError):
            errors["weight"] = "Weight must be a valid number"

    if "height" not in errors:
        try:
            h = float(data["height"])
            if h <= 0:
                errors["height"] = "Height must be positive"
        except (ValueError, TypeError):
            errors["height"] = "Height must be a valid number"

    return errors


def apply_all_filters(foods: list, profile: dict) -> list:
    """
    Apply goal-aware dietary filters to a food list.
    Mirrors the filter chain inside exercise_plan / meal_plan pipeline.
    """
    goal = profile.get("target_goal", "").lower()
    allergies = [a.lower() for a in profile.get("allergies", [])]
    health_conditions = [h.lower() for h in profile.get("health_conditions", [])]

    results = list(foods)

    # Allergy filter
    if "gluten" in allergies:
        results = [f for f in results if f.get("gluten_free", True)]
    if "dairy" in allergies:
        results = [f for f in results if f.get("category") != "dairy"]

    # Vegan / health conditions
    if "vegan" in health_conditions or "vegan" in allergies:
        results = [f for f in results if f.get("vegan", False)]

    # Goal-based calorie cap
    if goal == "weight loss":
        results = [f for f in results if f.get("calories", 0) <= 400]
    elif goal == "weight gain":
        results = [f for f in results if f.get("protein", 0) >= 5]

    return results


def simulate_sequential_backend(profile: dict) -> dict:
    """
    Simulates the sequential backend call chain:
      1. model load  (~0.3 s real; 0.05 s mock)
      2. meal plan   (~0.1 s)
      3. exercise plan (~0.1 s)
    Returns dict with 'elapsed' key for SLA assertions.
    Real backend with XGBoost load ≈ 2.67 s → exceeds 2 s SLA (WB-TC-08).
    """
    start = _time.time()
    _time.sleep(0.05)   # model load simulation
    generate_meal_plan("weight loss", 2000)
    generate_exercise_plan(profile, days=7)
    elapsed = _time.time() - start
    return {"elapsed": round(elapsed, 3), "status": "done"}


# ── Overloaded filter_foods with 2-arg signature used by latency tests ────────

_original_filter_foods = filter_foods   # keep reference to original 5-arg version

def filter_foods(foods_or_category=None, profile_or_max_cal=None,
                 min_protein=None, vegan=None, gluten_free=None):
    """
    Dual-signature filter_foods:
      - filter_foods(food_list, profile_dict)  → used by latency / profile tests
      - filter_foods(category, max_cal, ...)   → original single-criteria API
    """
    # 2-arg call: filter_foods(food_list, profile)
    if isinstance(foods_or_category, list) and isinstance(profile_or_max_cal, dict):
        return apply_all_filters(foods_or_category, profile_or_max_cal)
    # original 5-arg / keyword call
    return _original_filter_foods(
        category=foods_or_category,
        max_calories=profile_or_max_cal,
        min_protein=min_protein,
        vegan=vegan,
        gluten_free=gluten_free,
    )


# ── Exercise-plan mock with richer signature (mirrors exercise_plan.py) ───────

def adjust_exercise(row, activity_level: str, goal: str, timeline_weeks: int):
    """
    Mirrors exercise_plan.adjust_exercise().
    row : dict or pd.Series with keys sets / repetitions / duration
    Returns (sets, reps, duration) tuple.
    """
    sets = int(row["sets"])
    reps = int(row["repetitions"])
    dur  = float(row["duration"])

    # Activity-level branch
    level = map_activity_level(activity_level)
    if level == "beginner":
        sets = max(1, round(sets * 0.8))
        reps = max(1, round(reps * 0.8))
        dur  = max(1, round(dur  * 0.8, 1))
    else:  # advanced
        sets = round(sets * 1.2)
        reps = round(reps * 1.2)
        dur  = round(dur  * 1.2, 1)

    # Goal branch
    canonical_goal = _GOAL_ALIAS.get(goal.lower(), goal.lower())
    if canonical_goal == "weight loss":
        dur = round(dur * 1.2, 1)
    elif canonical_goal == "weight gain":
        reps = round(reps * 1.2)

    # Timeline branch
    if timeline_weeks <= 4:
        multiplier = 1.1
    elif timeline_weeks <= 8:
        multiplier = 1.05
    else:
        multiplier = 1.0   # no boost for long timelines

    sets = round(sets * multiplier)
    reps = round(reps * multiplier)
    dur  = round(dur  * multiplier, 1)

    return (sets, reps, dur)


def generate_exercise_plan(profile: dict, days: int = 7) -> dict:
    """
    Mirrors exercise_plan.generate_exercise_plan().
    Accepts profile dict with target_goal / activity_level / timeline_weeks.
    Returns {Day 1: [...], Day 2: [...], ...} or {'error': '...'}.
    """
    goal_raw  = profile.get("target_goal", "").lower()
    canonical = _GOAL_ALIAS.get(goal_raw, goal_raw)
    exercises = SAMPLE_EXERCISES.get(canonical)
    if exercises is None:
        return {"error": f"No exercises found for goal '{goal_raw}'."}

    activity  = profile.get("activity_level", "sedentary")
    timeline  = int(profile.get("timeline_weeks", 8))

    plan: dict = {}
    for day in range(1, days + 1):
        day_exs = []
        for ex in exercises:
            row = {
                "sets":        ex["sets"],
                "repetitions": ex["repetitions"],
                "duration":    ex["duration"],
            }
            s, r, d = adjust_exercise(row, activity, goal_raw, timeline)
            day_exs.append({
                "exercise_name": ex["exercise_name"],
                "sets":          s,
                "repetitions":   r,
                "duration":      d,
            })
        plan[f"Day {day}"] = day_exs
    return plan


# ══════════════════════════════════════════════════════════════════════════════
# exercise_video.py — mock (pose-estimation / rep counting)
# ══════════════════════════════════════════════════════════════════════════════

EXERCISE_CONFIG = {
    "Models/Bench_rf.pkl": {
        "ups":   ["up", "up_close", "up_roll"],
        "downs": ["down", "down_close"],
        "bench": True,
    },
    "Models/Deadlift_rf.pkl": {
        "ups":   ["up", "up_back", "up_roll"],
        "downs": ["down", "down_low", "down_roll"],
        "bench": False,
    },
    "Models/Squat_rf.pkl": {
        "ups":   ["up"],
        "downs": ["down", "down_deep", "down_forward"],
        "bench": False,
    },
}

_SUGGESTION_MAP = {
    "Models/Deadlift_rf.pkl": {
        "up_back":   "Avoid leaning backward or overarching your lower back.",
        "up_roll":   "Never round your back while deadlifting.",
        "down_roll": "Try not to arch your back. Keep your chest elevated instead.",
        "down_low":  "This is not a squat! Try to have your hips above parallel.",
    },
    "Models/Squat_rf.pkl": {
        "down_deep":    "Try not to go down this much.",
        "down_forward": "Avoid leaning forward. Keep your back straight.",
    },
    "Models/Bench_rf.pkl": {
        "up_close":   "Make sure to keep your arms parallel to each other.",
        "up_roll":    "Try to lock your shoulders instead of extending them.",
        "down_close": "Try to keep your chest more open.",
    },
}


def get_suggestion(model_path: str, prediction: str, current_stage: str) -> str:
    """
    Mock of exercise_video.get_suggestion().
    Returns corrective message when prediction == current_stage and is a bad-form class.
    Returns '' for correct-form classes.
    """
    if prediction != current_stage:
        return ""
    return _SUGGESTION_MAP.get(model_path, {}).get(prediction, "")


def process_video(video_path: str, model_path: str = "Models/Bench_rf.pkl") -> dict:
    """
    Mock of exercise_video.process_video().
    Simulates processing a recorded exercise video without MediaPipe/OpenCV.
    Returns a JSON-serialisable result dict identical in shape to the real function.
    """
    import os as _os
    if not video_path or not isinstance(video_path, str):
        return {"reps": 0, "confidence": 0.0, "pose": "",
                "suggestion": "", "frames_processed": 0,
                "status": "error: invalid video path"}

    if not _os.path.exists(video_path) and not video_path.startswith("mock_"):
        return {"reps": 0, "confidence": 0.0, "pose": "",
                "suggestion": "", "frames_processed": 0,
                "status": "error: could not open video file"}

    config = EXERCISE_CONFIG.get(model_path, EXERCISE_CONFIG["Models/Bench_rf.pkl"])
    # Simulate a small set of frame predictions
    _simulated_sequence = config["downs"][:1] + config["ups"][:1]
    reps = 1   # one down→up transition
    last_pred = config["ups"][0]
    last_suggestion = ""
    return {
        "reps":             reps,
        "confidence":       0.92,
        "pose":             last_pred,
        "suggestion":       last_suggestion,
        "frames_processed": len(_simulated_sequence),
        "status":           "done",
    }


def get_suggestion_for_stage(model_path: str, stage: str) -> str:
    """Helper: returns the suggestion for a given bad-form stage, regardless of current."""
    return _SUGGESTION_MAP.get(model_path, {}).get(stage, "")


def list_bad_form_classes(model_path: str) -> list:
    """Returns all bad-form class names defined for a given model."""
    return list(_SUGGESTION_MAP.get(model_path, {}).keys())


def is_rep_counted(current_stage: str, new_pred: str,
                   model_path: str, confidence: float = 0.95) -> bool:
    """
    Mock rep-counting transition logic.
    A rep is counted when: current_stage in downs AND new_pred in ups AND confidence >= 0.3
    """
    config = EXERCISE_CONFIG.get(model_path, EXERCISE_CONFIG["Models/Bench_rf.pkl"])
    return (
        current_stage in config["downs"]
        and new_pred in config["ups"]
        and confidence >= 0.3
    )