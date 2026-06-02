"""
mock_backend.py
───────────────
Mirrors the actual NutriFit AI backend functions exactly as they
exist in the real codebase (meal_plan.py, exercise_plan.py,
profile_setup.py) so pytest can import and test them without
needing Flask, Firebase, or XGBoost running.

All function signatures, variable names, filter logic, and class
structures match the real backend 1-to-1.
"""

import pandas as pd
import numpy as np
import time
import re
import hashlib

# ─────────────────────────────────────────────────────────────────
# ALLERGEN MAPPINGS  (exact copy from meal_plan.py)
# ─────────────────────────────────────────────────────────────────
ALLERGEN_FILTERS = {
    "egg":      ["egg", "omelette", "boiled egg", "pancake", "mayonnaise",
                 "egg fried rice", "custard", "meringue"],
    "gluten":   ["roti", "paratha", "bread", "cereal", "pancake", "sandwich",
                 "pasta", "naan", "chapati", "biscuit", "cake"],
    "nuts":     ["cashew", "almond", "peanut", "walnut", "pistachio",
                 "halwa", "kheer", "baklava"],
    "seafood":  ["fish", "shrimp", "prawn", "crab", "lobster", "salmon",
                 "tuna", "sardine"],
    "mushroom": ["mushroom", "fungus"],
    "dairy":    ["milk", "yogurt", "cheese", "paneer", "lassi", "butter",
                 "cream", "ghee", "kheer", "shake"],
}

# ─────────────────────────────────────────────────────────────────
# HEALTH CONDITION FILTERS  (exact copy from meal_plan.py)
# ─────────────────────────────────────────────────────────────────
HEALTH_RESTRICTIONS = {
    "diabetes": {
        "avoid": ["halwa", "kheer", "milkshake", "lassi", "fruit chaat",
                  "cereal", "pancake", "chai", "biryani", "pulao",
                  "sweet", "sugar", "honey", "jam", "juice"],
        "prefer_low_gi": True,
    },
    "hypertension": {
        "avoid": ["fried", "paratha", "nihari", "haleem", "kabab",
                  "kofte", "pulao", "sajji", "biryani", "pickles",
                  "chips", "processed", "canned", "butter chicken"],
        "limit_sodium": True,
    },
    "heart disease": {
        "avoid": ["fried", "butter", "ghee", "fatty meat", "biryani",
                  "nihari", "haleem", "cream", "cheese"],
        "prefer_lean": True,
    },
}

# ─────────────────────────────────────────────────────────────────
# MACRO & MEAL SPLITS  (exact copy from meal_plan.py)
# ─────────────────────────────────────────────────────────────────
MACRO_SPLITS = {
    "weight loss": (0.40, 0.35, 0.25),
    "weight gain": (0.50, 0.30, 0.20),
    "maintain":    (0.45, 0.30, 0.25),
}

MEAL_SPLITS = {
    "weight loss": {"breakfast": 0.30, "lunch": 0.40, "dinner": 0.30},
    "weight gain": {"breakfast": 0.30, "lunch": 0.45, "dinner": 0.25},
    "maintain":    {"breakfast": 0.30, "lunch": 0.40, "dinner": 0.30},
}

# ─────────────────────────────────────────────────────────────────
# SAMPLE FOOD DATASET  (subset of foods (3).csv)
# ─────────────────────────────────────────────────────────────────
SAMPLE_FOODS = pd.DataFrame({
    "food_name": [
        "Oats", "Boiled egg", "Egg omelette", "Paratha",
        "Halwa", "Kheer", "Nihari", "Chicken biryani",
        "Chicken curry", "Milkshake", "Brown bread",
        "Cooked lentils", "Vegetable Salad", "Yogurt",
        "Grilled chicken", "Brown Rice", "Fruit chaat",
        "Lassi", "Chicken breast", "Mango juice",
    ],
    "calories":  [150, 80,  120, 250, 300, 250, 450, 400, 300, 200, 120, 180, 60,  100, 165, 215, 130, 150, 165, 120],
    "protein_g": [5,   6,   8,   4,   3,   5,   20,  15,  25,  3,   4,   12,  2,   6,   31,  4,   2,   3,   31,  1],
    "carbs_g":   [27,  1,   2,   30,  45,  40,  10,  50,  5,   35,  22,  30,  10,  12,  0,   45,  25,  18,  0,   30],
    "fat_g":     [3,   5,   7,   12,  10,  8,   25,  18,  12,  4,   2,   3,   1,   3,   3,   1,   1,   2,   3,   0],
})
SAMPLE_FOODS["food_name_lower"] = SAMPLE_FOODS["food_name"].str.lower()

# ─────────────────────────────────────────────────────────────────
# SAMPLE EXERCISE DATASET  (subset of excercise.csv)
# ─────────────────────────────────────────────────────────────────
SAMPLE_EXERCISES = pd.DataFrame({
    "exercise_name": ["Squats", "Push-ups", "Lunges", "Plank", "Deadlift",
                      "Bench Press", "Pull-ups", "Bicep Curl", "Tricep Dip", "Jogging"],
    "sets":          [3, 3, 3, 3, 3, 3, 3, 3, 3, 1],
    "repetitions":   [12, 15, 12, 1, 10, 12, 10, 15, 15, 1],
    "duration":      [30, 20, 30, 60, 30, 30, 20, 20, 20, 1800],
    "muscle_group":  ["legs", "chest", "legs", "core", "back",
                      "chest", "back", "arms", "arms", "cardio"],
    "type":          ["strength"] * 9 + ["cardio"],
    "intensity":     ["medium", "medium", "medium", "low", "high",
                      "high", "high", "low", "low", "medium"],
    "target_goal":   ["weight loss", "weight loss", "weight loss", "maintain",
                      "weight gain", "weight gain", "weight gain", "weight gain",
                      "maintain", "weight loss"],
})


# ═══════════════════════════════════════════════════════════════════
#  MEAL PLAN — filter functions  (mirrors ProfessionalMealPlanner)
# ═══════════════════════════════════════════════════════════════════

def filter_by_allergies(df: pd.DataFrame, allergies: list) -> pd.DataFrame:
    """Mirrors ProfessionalMealPlanner._filter_by_allergies()"""
    df = df.copy()
    for allergen in allergies:
        if allergen.lower() in ALLERGEN_FILTERS:
            pattern = "|".join(ALLERGEN_FILTERS[allergen.lower()])
            df = df[~df["food_name_lower"].str.contains(
                pattern, case=False, na=False, regex=True)]
    return df.reset_index(drop=True)


def filter_by_health_conditions(df: pd.DataFrame, conditions: list) -> pd.DataFrame:
    """Mirrors ProfessionalMealPlanner._filter_by_health_conditions()"""
    df = df.copy()
    for condition in conditions:
        condition_lower = condition.lower()
        if condition_lower in HEALTH_RESTRICTIONS:
            avoid_foods = HEALTH_RESTRICTIONS[condition_lower].get("avoid", [])
            if avoid_foods:
                pattern = "|".join(avoid_foods)
                df = df[~df["food_name_lower"].str.contains(
                    pattern, case=False, na=False, regex=True)]
    return df.reset_index(drop=True)


def apply_all_filters(df: pd.DataFrame, profile: dict) -> pd.DataFrame:
    """Mirrors ProfessionalMealPlanner._apply_all_filters()"""
    if profile.get("allergies"):
        df = filter_by_allergies(df, profile["allergies"])
    if profile.get("health_conditions"):
        df = filter_by_health_conditions(df, profile["health_conditions"])
    return df


# ═══════════════════════════════════════════════════════════════════
#  EXERCISE PLAN  (mirrors exercise_plan class)
# ═══════════════════════════════════════════════════════════════════

def map_activity_level(activity_level: str) -> str:
    """Mirrors exercise_plan.map_activity_level() — static method"""
    al = activity_level.lower()
    if al in ["sedentary", "lightly active"]:
        return "beginner"
    elif al in ["moderately active", "very active", "extra active"]:
        return "advanced"
    return "beginner"


def adjust_exercise(row, activity: str, target_goal: str, timeline_weeks: int):
    """Mirrors exercise_plan.adjust_exercise()"""
    sets, reps, dur = row["sets"], row["repetitions"], row["duration"]
    level = map_activity_level(activity)

    if level == "beginner":
        sets *= 0.8;  reps *= 0.8;  dur *= 0.8
    elif level == "advanced":
        sets *= 1.2;  reps *= 1.2;  dur *= 1.2

    goal = target_goal.lower()
    if goal in ["weight loss", "lose weight", "fat loss", "weight lose"]:
        dur *= 1.2
    elif goal in ["weight gain", "gain weight", "muscle gain"]:
        reps *= 1.2

    if timeline_weeks <= 4:
        sets *= 1.1;  reps *= 1.1;  dur *= 1.1
    elif 5 <= timeline_weeks <= 8:
        sets *= 1.05; reps *= 1.05; dur *= 1.05

    return pd.Series([round(sets), round(reps), round(dur)])


def generate_exercise_plan(user_profile: dict, days: int = 7) -> dict:
    """Mirrors exercise_plan.generate_exercise_plan()"""
    goal     = user_profile["target_goal"].lower()
    activity = user_profile["activity_level"].lower()
    timeline = user_profile.get("timeline_weeks", 8)

    filtered = SAMPLE_EXERCISES[
        SAMPLE_EXERCISES["target_goal"].str.lower() == goal
    ].copy()

    if filtered.empty:
        return {"error": f"No exercises found for goal '{goal}'. "
                         "Please update your goal or try a different one."}

    filtered[["sets", "repetitions", "duration"]] = filtered.apply(
        lambda r: adjust_exercise(r, activity, goal, timeline), axis=1
    )

    # Deterministic shuffle (mirrors real backend)
    user_hash = int(hashlib.md5(str(user_profile).encode()).hexdigest(), 16) % (2 ** 32)
    filtered = filtered.sample(frac=1, random_state=user_hash).reset_index(drop=True)

    exercises_per_day = max(3, len(filtered) // days)
    daily_plan = {}
    for day in range(1, days + 1):
        start_idx = (day - 1) * exercises_per_day
        end_idx   = start_idx + exercises_per_day
        day_ex    = filtered.iloc[start_idx:end_idx]
        if len(day_ex) < 3:
            day_ex = filtered.iloc[:3]
        daily_plan[f"Day {day}"] = day_ex[
            ["exercise_name", "sets", "repetitions", "duration"]
        ].to_dict(orient="records")

    return daily_plan


# ═══════════════════════════════════════════════════════════════════
#  PROFILE SETUP — BMI / BMR / TDEE  (mirrors profile_setup class)
# ═══════════════════════════════════════════════════════════════════

ACTIVITY_MULTIPLIERS = {
    "sedentary":        1.2,
    "lightly active":   1.375,
    "moderately active":1.55,
    "very active":      1.725,
    "extra active":     1.9,
}


def calculate_bmi(weight_kg: float, height_ft: float) -> dict:
    """Mirrors profile_setup.calculate_metrics() — BMI portion"""
    if weight_kg <= 0 or height_ft <= 0:
        raise ValueError("Weight and height must be positive values.")
    height_m  = height_ft * 0.3048
    bmi       = round(weight_kg / (height_m ** 2), 2)
    if   bmi < 18.5: label = "Underweight"
    elif bmi < 25.0: label = "Normal"
    elif bmi < 30.0: label = "Overweight"
    else:            label = "Obese"
    return {"bmi": bmi, "label": label}


def calculate_bmr(weight_kg: float, height_ft: float,
                  age: int, gender: str) -> float:
    """Mirrors profile_setup.calculate_metrics() — BMR (Mifflin-St Jeor)"""
    height_cm = height_ft * 0.3048 * 100
    if gender.lower() == "male":
        return (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    return (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """Mirrors profile_setup TDEE calculation"""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level.lower(), 1.2)
    return round(bmr * multiplier, 2)


def validate_profile(data: dict) -> dict:
    """Mirrors profile_setup.run() — returns errors dict"""
    errors = {}
    required = ["age", "weight", "height", "gender", "activitylevel", "goal"]
    for field in required:
        if field not in data or data[field] in [None, ""]:
            errors[field] = "This field is required"
    if errors:
        return errors

    try:
        age = int(data["age"])
        if age <= 0:
            errors["age"] = "Age must be greater than 0"
    except:
        errors["age"] = "Age must be a valid number"

    try:
        weight = float(data["weight"])
        if weight <= 0:
            errors["weight"] = "Weight must be positive"
    except:
        errors["weight"] = "Weight must be a valid number"

    try:
        height = float(data["height"])
        if height <= 0:
            errors["height"] = "Height must be positive"
    except:
        errors["height"] = "Height must be a valid number"

    return errors


# ═══════════════════════════════════════════════════════════════════
#  BACKEND LATENCY SIMULATOR
# ═══════════════════════════════════════════════════════════════════

def simulate_sequential_backend(profile: dict) -> dict:
    """Simulates the sequential module calls — mirrors /submit_profile route"""
    start = time.time()
    time.sleep(0.3)   # XGBoost model load (~0.8s real)
    filtered = apply_all_filters(SAMPLE_FOODS, profile)
    time.sleep(0.1)
    ep = generate_exercise_plan(profile)
    time.sleep(0.1)
    elapsed = time.time() - start
    return {"elapsed": elapsed, "meal_foods": len(filtered), "exercise_plan": ep}
