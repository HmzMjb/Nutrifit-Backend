"""
mock_backend.py
───────────────
Mirrors the actual NutriFit AI backend functions (meal_plan.py,
exercise_plan.py, meal_snap.py) so pytest can import and test them
without needing the full Flask server running.

Place this file alongside your actual backend files, or point
sys.path to your real backend folder and remove these stubs.
"""

import pandas as pd
import numpy as np
import time
import re
import os
import sys



# ─────────────────────────────────────────────────────────────────
# SAMPLE FOOD DATASET  (mirrors foods.csv)
# ─────────────────────────────────────────────────────────────────
SAMPLE_FOODS = pd.DataFrame({
    "food_name": [
        "oats", "boiled egg", "egg omelette", "paratha",
        "halwa", "kheer", "nihari", "biryani",
        "chicken curry", "mango shake", "brown bread",
        "lentils", "vegetable salad", "yogurt",
    ],
    "calories":  [150, 80,  120, 250, 300, 250, 450, 400, 300, 200, 120, 180, 60,  100],
    "protein_g": [5,   6,   8,   4,   3,   5,   20,  15,  25,  3,   4,   12,  2,   6  ],
    "carbs_g":   [27,  1,   2,   30,  45,  40,  10,  50,  5,   35,  22,  30,  10,  12 ],
    "fat_g":     [3,   5,   7,   12,  10,  8,   25,  18,  12,  4,   2,   3,   1,   3  ],
})
SAMPLE_FOODS["food_name_lower"] = SAMPLE_FOODS["food_name"].str.lower()


# ─────────────────────────────────────────────────────────────────
# EXERCISE DATASET  (mirrors exercise.csv)
# ─────────────────────────────────────────────────────────────────
SAMPLE_EXERCISES = pd.DataFrame({
    "exercise_name": ["Squats","Push-ups","Lunges","Plank","Deadlift",
                      "Bench Press","Pull-ups","Bicep Curl","Tricep Dip","Jogging"],
    "sets":          [3, 3, 3, 3, 3, 3, 3, 3, 3, 1],
    "repetitions":   [12,15,12,1,10,12,10,15,15,1],
    "duration":      [30,20,30,60,30,30,20,20,20,1800],
    "muscle_group":  ["legs","chest","legs","core","back","chest","back","arms","arms","cardio"],
    "type":          ["strength"]*9 + ["cardio"],
    "intensity":     ["medium","medium","medium","low","high","high","high","low","low","medium"],
    "target_goal":   ["weight loss","weight loss","weight loss","maintain",
                      "weight gain","weight gain","weight gain","weight gain",
                      "maintain","weight loss"],
})


# ─────────────────────────────────────────────────────────────────
# filter_foods()  ←  exact replica from meal_plan.py
# ─────────────────────────────────────────────────────────────────
def filter_foods(df: pd.DataFrame, profile: dict) -> pd.DataFrame:
    allergies = [a.lower() for a in profile.get("allergies", [])]
    health    = [h.lower() for h in profile.get("health_conditions", [])]
    out = df.copy()

    if len(allergies) > 0:                              # Node 2
        pattern = "|".join(re.escape(a) for a in allergies)
        out = out[~out["food_name_lower"].str.contains(pattern, na=False)]

    if "diabetes" in health:                            # Node 3
        out = out[~out["food_name_lower"].str.contains(
            "halwa|kheer|milkshake|lassi|mango shake|cereal|pancake",
            case=False, na=False)]

    if "hypertension" in health:                        # Node 4
        out = out[~out["food_name_lower"].str.contains(
            "fried|paratha|biryani|nihari|haleem|kabab|butter chicken",
            case=False, na=False)]

    return out.reset_index(drop=True)                   # Node 5


# ─────────────────────────────────────────────────────────────────
# map_activity_level()  ←  from exercise_plan.py
# ─────────────────────────────────────────────────────────────────
def map_activity_level(activity_level: str) -> str:
    al = activity_level.lower()
    if al in ["sedentary", "lightly active"]:
        return "beginner"
    elif al in ["moderately active", "very active", "extra active"]:
        return "advanced"
    return "beginner"


# ─────────────────────────────────────────────────────────────────
# adjust_exercise()  ←  from exercise_plan.py
# ─────────────────────────────────────────────────────────────────
def adjust_exercise(row, activity: str, target_goal: str, timeline_weeks: int):
    sets, reps, dur = row["sets"], row["repetitions"], row["duration"]
    level = map_activity_level(activity)

    if level == "beginner":
        sets *= 0.8; reps *= 0.8; dur *= 0.8
    elif level == "advanced":
        sets *= 1.2; reps *= 1.2; dur *= 1.2

    goal = target_goal.lower()
    if goal in ["weight loss", "lose weight", "fat loss"]:
        dur *= 1.2
    elif goal in ["weight gain", "gain weight", "muscle gain"]:
        reps *= 1.2

    if timeline_weeks <= 4:
        sets *= 1.1; reps *= 1.1; dur *= 1.1
    elif 5 <= timeline_weeks <= 8:
        sets *= 1.05; reps *= 1.05; dur *= 1.05

    return pd.Series([round(sets), round(reps), round(dur)])


# ─────────────────────────────────────────────────────────────────
# generate_exercise_plan()  ←  from exercise_plan.py
# ─────────────────────────────────────────────────────────────────
def generate_exercise_plan(user_profile: dict, days: int = 7) -> dict:
    goal     = user_profile["target_goal"].lower()
    activity = user_profile["activity_level"]
    timeline = user_profile.get("timeline_weeks", 8)

    filtered = SAMPLE_EXERCISES[
        SAMPLE_EXERCISES["target_goal"].str.lower() == goal
    ].copy()

    if filtered.empty:
        return {"error": f"No exercises found for goal '{goal}'."}

    filtered[["sets","repetitions","duration"]] = filtered.apply(
        lambda r: adjust_exercise(r, activity, goal, timeline), axis=1
    )

    exercises_per_day = max(3, len(filtered) // days)
    daily_plan = {}
    for day in range(1, days + 1):
        s = (day - 1) * exercises_per_day
        day_ex = filtered.iloc[s : s + exercises_per_day]
        if len(day_ex) < 3:
            day_ex = filtered.iloc[:3]
        daily_plan[f"Day {day}"] = day_ex[
            ["exercise_name","sets","repetitions","duration"]
        ].to_dict(orient="records")

    return daily_plan


# ─────────────────────────────────────────────────────────────────
# calculate_bmi()
# ─────────────────────────────────────────────────────────────────
def calculate_bmi(weight_kg: float, height_ft: float) -> dict:
    if weight_kg <= 0 or height_ft <= 0:
        raise ValueError("Weight and height must be positive values.")
    height_m = height_ft * 0.3048
    bmi = round(weight_kg / (height_m ** 2), 2)
    if   bmi < 18.5: label = "Underweight"
    elif bmi < 25.0: label = "Normal"
    elif bmi < 30.0: label = "Overweight"
    else:            label = "Obese"
    return {"bmi": bmi, "label": label}


# ─────────────────────────────────────────────────────────────────
# simulate_sequential_backend()  ← mirrors the latency issue
# ─────────────────────────────────────────────────────────────────
def simulate_sequential_backend(profile: dict) -> dict:
    """Simulates the sequential module calls in /submit_profile."""
    start = time.time()

    # Step 1 – model load (simulated)
    time.sleep(0.3)   # stripped-down sim; real XGBoost load ~0.8s

    # Step 2 – meal plan
    filtered = filter_foods(SAMPLE_FOODS, profile)
    time.sleep(0.1)

    # Step 3 – exercise plan
    ep = generate_exercise_plan(profile)
    time.sleep(0.1)

    elapsed = time.time() - start
    return {"elapsed": elapsed, "meal_foods": len(filtered), "exercise_plan": ep}
