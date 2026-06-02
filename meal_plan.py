# meal_plan.py

import profile
from typing import List, Dict

import pandas as pd
import numpy as np
import joblib
import os
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor
from scipy.optimize import nnls

# ==================== FOOD CATEGORIES ====================
BREAKFAST_FOODS = ["Toasted Plain Waffles", "Chocolate Pudding", "Vanilla Wafers", "Apple Pie", "Banana Pudding",
                   "Sweet Roll", "Plain Muffin", "Yogurt", "Buttermilk Pancakes", "Pecan Pie", "Jelly Doughnut",
                   "Diet Cheesecake", "Pancakes", "Cupcakes with Frosting (Low Fat)", "Brownie", "Fruit Waffle",
                   "Peanut Butter Cookies", "Fruit and Nuts Muffin", "Peanut Butter Fudge", "Cupcake", "Cookie",
                   "French Toast", "Bread Stuffing", "Cheese Spread", "Protein Powder", "Chocolate Sponge Cake", "Oats",
                   "Boiled egg", "Egg omelette", "Paratha", "Brown bread", "Cereal", "Halwa", "Kheer", "Lassi", "Chai",
                   "Roti", "Garlic Naan", "Vanilla Yogurt", "Milk", "Buttermilk", "Green tea", "Coffee",
                   "Hot cocoa milk", "Milkshake", "Lemonade", "Orange juice", "Mango juice", "Pineapple juice",
                   "Grapefruit juice", "Vegetable juice", "Detox Water", "Skim Chocolate Milk", "Fruit smoothie",
                   "Biscuits", "Dried Fruit Mix", "Dried Apricot", "Raisins", "Figs", "Banana", "Apple", "Orange",
                   "Grapes", "Strawberries", "Kiwi", "Pineapple", "Mango", "Peach", "Pear", "Plum", "Avocado",
                   "Berries", "Fruit Salad", "Raspberries", "Coconut", "Fruit chaat"]

LUNCH_FOODS = ["Cabbage Salad or Coleslaw with Dressing", "Chicken or Turkey Salad",
               "Lettuce Salad with Avocado, Tomato, and/or Carrots", "Chicken or Turkey Garden Salad",
               "Mixed Salad Greens", "Vegetable Salad", "Fruit chaat", "Chickpea Salad", "Spaghetti", "Brown Rice",
               "Pasta with Meat Sauce", "Mushroom Risotto", "Egg Noodles", "Noodles", "Lasagna with Chicken or Turkey",
               "Whole Wheat Spaghetti", "Macaroni with Cheese", "White Rice", "Brown and Wild Rice",
               "Chicken Fried Rice", "Rice Pilaf", "Rice Noodles", "Fried Rice", "Spaghetti with Meatballs",
               "Shrimp Fried Rice", "Lasagna with Meat", "Vegetable Macaroni", "Chicken Soup", "Tomato Soup",
               "Vegetable Soup", "Chicken Rice Soup", "Beef Stock", "Chicken Chili", "Beef Noodle Soup",
               "Chicken Noodle Soup", "Chicken curry", "Beef Curry", "Mutton Curry", "Chicken biryani", "Beef biryani",
               "Mutton biryani", "Cooked lentils", "Nihari", "Haleem", "Chicken breast", "Chicken thigh",
               "Chicken wing", "Chicken drumstick", "Grilled chicken", "Roasted chicken", "Beef steak", "Lamb chop",
               "Fried fish", "Chicken patties", "Chicken corn soup", "Mashed potato", "Plain pancakes", "Palak paneer",
               "Egg fried rice", "Cooked mixed vegetable"]
DINNER_FOODS = ["Lasagna with Meat and Spinach", "Beef Curry", "Mutton Curry", "Chicken Curry", "Lamb Curry",
                "Beef biryani", "Chicken biryani", "Mutton biryani", "Nihari", "Haleem", "Chicken Sajji",
                "Murgh Mussallam", "Chapali Kabab", "Shami Kabab", "Dal makhani", "Shahi paneer", "Malai kofta",
                "Sarson ka saag", "Kashmiri rogan josh", "Dum aloo", "Matar paneer", "Chicken chow mein",
                "Stuffed eggplant", "Aloo keema", "Tawa chicken", "Fish tikka", "Grilled fish", "Lobster", "Shrimp",
                "Beef steak", "Lamb chop", "Fried mutton chop", "Roast beef", "Grilled chicken", "Roasted chicken",
                "Chicken thigh", "Chicken wing", "Chicken drumstick", "Chicken breast", "Beef meatballs",
                "Chicken meatballs", "Beef sausage", "Chicken sausage", "Salami", "Corned beef", "Pizza",
                "Cheese pizza", "Pepperoni pizza", "French bread pizza", "Cheeseburger", "Veggie burger",
                "Chicken nuggets", "Fish fillet", "Tempura roll", "Chicken spring roll", "Beef chow mein",
                "Egg roll with chicken", "Roti", "Kidney bean curry", "Kofta curry", "Chicken pulao", "Fried fish",
                "Chocolate cake", "Custard", "Vanilla fudge", "Ice cream cone", "Garlic Naan Bread", "Roti"]

# DINNER_FOODS = LUNCH_FOODS


# ==================== MACRO & MEAL SPLITS ====================

MACRO_SPLITS = {
    "weight loss": (0.40, 0.35, 0.25),  # carbs, protein, fat
    "weight gain": (0.50, 0.30, 0.20),
    "maintain": (0.45, 0.30, 0.25)
}

MEAL_SPLITS = {
    "weight loss": {"breakfast": 0.30, "lunch": 0.40, "dinner": 0.30},
    "weight gain": {"breakfast": 0.30, "lunch": 0.45, "dinner": 0.25},
    "maintain": {"breakfast": 0.30, "lunch": 0.40, "dinner": 0.30}
}

# ==================== ALLERGEN MAPPINGS ====================

ALLERGEN_FILTERS = {
    "egg": [
        "egg", "omelette", "boiled egg", "pancake", "mayonnaise",
        "egg fried rice", "custard", "meringue"
    ],
    "gluten": [
        "roti", "paratha", "bread", "cereal", "pancake", "sandwich",
        "pasta", "naan", "chapati", "biscuit", "cake"
    ],
    "nuts": [
        "cashew", "almond", "peanut", "walnut", "pistachio",
        "halwa", "kheer", "baklava"
    ],
    "seafood": [
        "fish", "shrimp", "prawn", "crab", "lobster", "salmon",
        "tuna", "sardine"
    ],
    "mushroom": [
        "mushroom", "fungus"
    ],
    "dairy": [
        "milk", "yogurt", "cheese", "paneer", "lassi", "butter",
        "cream", "ghee", "kheer", "shake"
    ]
}

# ==================== HEALTH CONDITION FILTERS ====================

HEALTH_RESTRICTIONS = {
    "diabetes": {
        "avoid": [
            "halwa", "kheer", "milkshake", "lassi", "fruit chaat",
            "cereal", "pancake", "chai", "biryani", "pulao",
            "sweet", "sugar", "honey", "jam", "juice"
        ],
        "prefer_low_gi": True
    },
    "hypertension": {
        "avoid": [
            "fried", "paratha", "nihari", "haleem", "kabab",
            "kofte", "pulao", "sajji", "biryani", "pickles",
            "chips", "processed", "canned", "butter chicken"
        ],
        "limit_sodium": True
    },
    "heart disease": {
        "avoid": [
            "fried", "butter", "ghee", "fatty meat", "biryani",
            "nihari", "haleem", "cream", "cheese"
        ],
        "prefer_lean": True
    }
}

print("✓ Configuration loaded successfully!")
print(f"  - {len(BREAKFAST_FOODS)} breakfast foods")
print(f"  - {len(LUNCH_FOODS)} lunch/dinner foods")
print(f"  - {len(ALLERGEN_FILTERS)} allergen types")
print(f"  - {len(HEALTH_RESTRICTIONS)} health conditions")


# ==================== PROFESSIONAL MEAL PLANNER ====================
class ProfessionalMealPlanner:

    def __init__(
            self,
            foods_csv: str = "foods4.csv",
            profiles_csv: str = "pakistan_user_profiles.csv",
            model_path: str = "models/calorie_model.pkl"
    ):
        """Initialize the meal planner with food database and ML model"""
        self.food_df = self._load_food_data(foods_csv)
        self.model = self._load_or_train_model(profiles_csv, model_path)

    def _load_food_data(self, path: str) -> pd.DataFrame:
        """Load and preprocess food nutrition database"""
        df = pd.read_csv(path)
        df.fillna(0, inplace=True)


        df["food_name_lower"] = df["food_name"].str.lower()

        return df

    def _load_or_train_model(self, profiles_csv: str, model_path: str):
        """Load existing model or train new one for calorie prediction"""
        if os.path.exists(model_path):
            print(f"Loading existing model from {model_path}")
            return joblib.load(model_path)

        print("Training new calorie prediction model...")
        df = pd.read_csv(profiles_csv)

        # Handle missing values
        df["gender"].fillna("Male", inplace=True)
        df["activity_level"].fillna("Moderate", inplace=True)
        df["target_goal"].fillna("maintain", inplace=True)

        # Prepare features and target
        X = df[["age", "weight_kg", "height_cm", "gender", "activity_level", "target_goal"]]
        y = df["calories"]

        # Build preprocessing pipeline
        preprocessor = ColumnTransformer([
            ("cat", OneHotEncoder(handle_unknown="ignore"),
             ["gender", "activity_level", "target_goal"]),
            ("num", "passthrough", ["age", "weight_kg", "height_cm"])
        ])

        model = XGBRegressor(
            n_estimators=400,
            learning_rate=0.06,
            max_depth=4,
            objective="reg:squarederror",
            random_state=42
        )

        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("model", model)
        ])

        # Train model
        pipeline.fit(X, y)

        # Save model
        os.makedirs("models", exist_ok=True)
        joblib.dump(pipeline, model_path)
        print(f"Model trained and saved to {model_path}")

        return pipeline

    # ==================== CONTENT-BASED FILTERING ====================
    @staticmethod
    def _cosine_similarity(a, b):
        norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
        return float(np.dot(a, b) / (norm_a * norm_b)) if norm_a > 0 and norm_b > 0 else 0.0

    def _get_top_foods(
            self,
            food_pool: pd.DataFrame,
            target_macros: np.ndarray,
            top_n: int = 3,
            diversity_weight: float = 0.1
    ) -> List[pd.Series]:
        """Select top N foods based on macro similarity to target"""
        scores = []

        for idx, row in food_pool.iterrows():
            food_vector = np.array([
                row["protein_g"],
                row["carbs_g"],
                row["fat_g"]
            ])

            similarity = self._cosine_similarity(food_vector, target_macros)
            diversity_bonus = np.random.uniform(0, diversity_weight)
            final_score = similarity + diversity_bonus

            scores.append((final_score, row))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [row for _, row in scores[:top_n]]

    @staticmethod
    def _solve_portions(selected_foods, target_calories, target_protein):
        A = np.array([[f["calories"] / 100 for f in selected_foods], [f["protein_g"] / 100 for f in selected_foods]])
        b = np.array([target_calories, target_protein])
        portions, _ = nnls(A, b)
        return np.clip(portions, 60, 350)

    # ==================== FILTERING LOGIC ====================
    def _filter_by_allergies(self, df, allergies) -> pd.DataFrame:
        """Filter out foods containing allergens"""
        df = df.copy()
        for allergen in allergies:
            if allergen.lower() in ALLERGEN_FILTERS:
                pattern = "|".join(ALLERGEN_FILTERS[allergen.lower()])
                df = df[~df["food_name_lower"].str.contains(pattern, case=False, na=False, regex=True)]
        return df.reset_index(drop=True)

    def _filter_by_health_conditions(
            self,
            food_df: pd.DataFrame,
            conditions: List[str]
    ) -> pd.DataFrame:
        """Filter foods based on health conditions"""
        df = food_df.copy()

        for condition in conditions:
            condition_lower = condition.lower()

            if condition_lower in HEALTH_RESTRICTIONS:
                restrictions = HEALTH_RESTRICTIONS[condition_lower]
                avoid_foods = restrictions.get("avoid", [])

                if avoid_foods:
                    pattern = "|".join(avoid_foods)
                    df = df[~df["food_name_lower"].str.contains(
                        pattern,
                        case=False,
                        na=False,
                        regex=True
                    )]

        return df.reset_index(drop=True)

    def _apply_all_filters(self, profile) -> pd.DataFrame:
        """Apply all filtering criteria to food database"""
        df = self.food_df.copy()
        if profile.get("allergies"):
            df = self._filter_by_allergies(df, profile["allergies"])
        if profile.get("health_conditions"):
            df = self._filter_by_health_conditions(df, profile["health_conditions"])
        return df

    # ==================== MEAL GENERATION ====================
    def _generate_meal(self, meal_type, meal_calories, macros_target, recent_foods, filtered_foods: pd.DataFrame,
                       cooldown: int = 2) -> List[Dict]:
        if meal_type == "breakfast":
            food_list = BREAKFAST_FOODS
        elif meal_type == "lunch":
            food_list = LUNCH_FOODS
        else:
            food_list = DINNER_FOODS

        meal_pool = filtered_foods[
            filtered_foods["food_name_lower"].isin([f.lower() for f in food_list])
        ].copy()

        meal_pool = meal_pool[~meal_pool["food_name"].isin(recent_foods)]
        if meal_pool.empty:
            meal_pool = filtered_foods[
                filtered_foods["food_name_lower"].isin([f.lower() for f in food_list])
            ].copy()
        target_vector = np.array([
            macros_target["protein_g"],
            macros_target["carbs_g"],
            macros_target["fat_g"]
        ])

        top_foods = self._get_top_foods(meal_pool, target_vector, top_n=3)
        if not top_foods:
            return []

        portions = self._solve_portions(top_foods, meal_calories, macros_target["protein_g"])
        meal_items = []
        for grams, food_row in zip(portions, top_foods):
            multiplier = grams / 100

            item = {
                "food_name": food_row["food_name"],
                "grams": round(float(grams), 1),
                "quantity": round(food_row["quantity"] * multiplier, 1),
                "unit": food_row["unit"],
                "calories": round(food_row["calories"] * multiplier, 1),
                "protein_g": round(food_row["protein_g"] * multiplier, 1),
                "carbs_g": round(food_row["carbs_g"] * multiplier, 1),
                "fat_g": round(food_row["fat_g"] * multiplier, 1)
            }
            meal_items.append(item)

        return meal_items

    # ---------- MAIN MEAL PLAN ----------
    def generate_meal_plan(self, profile, days=7, cooldown: int = 2) -> Dict:
        """Generate a complete personalized meal plan"""

        weekly_plan = {}
        recent_foods = {
            "breakfast": [],
            "lunch": [],
            "dinner": []
        }

        goal = profile.get("target_goal", "maintain").lower()
        if goal not in MACRO_SPLITS:
            goal = "maintain"

        filtered_foods = self._apply_all_filters(profile)

        if filtered_foods.empty:
            raise ValueError(
                "No foods available after applying filters. "
                "Please review your dietary restrictions."
            )

        for day_num in range(1, days + 1):

            profile_df = pd.DataFrame([profile])
            daily_calories = float(self.model.predict(profile_df)[0])

            carb_ratio, protein_ratio, fat_ratio = MACRO_SPLITS[goal]

            total_protein = (daily_calories * protein_ratio) / 4
            total_carbs = (daily_calories * carb_ratio) / 4
            total_fat = (daily_calories * fat_ratio) / 9

            day_plan = {
                "predicted_daily_calories": round(daily_calories, 1),
                "daily_macros_target": {
                    "protein_g": round(total_protein, 1),
                    "carbs_g": round(total_carbs, 1),
                    "fat_g": round(total_fat, 1)
                },
                "meals": {}
            }

            for meal_type, meal_percentage in MEAL_SPLITS[goal].items():

                meal_calories = daily_calories * meal_percentage

                meal_macros = {
                    "protein_g": total_protein * meal_percentage,
                    "carbs_g": total_carbs * meal_percentage,
                    "fat_g": total_fat * meal_percentage
                }

                meal_items = self._generate_meal(
                    meal_type=meal_type,
                    meal_calories=meal_calories,
                    macros_target=meal_macros,
                    filtered_foods=filtered_foods,
                    recent_foods=recent_foods[meal_type],
                    cooldown=cooldown
                )

                for item in meal_items:
                    recent_foods[meal_type].append(item["food_name"])

                recent_foods[meal_type] = recent_foods[meal_type][-cooldown:]

                meal_totals = {
                    "calories": sum(item["calories"] for item in meal_items),
                    "protein_g": sum(item["protein_g"] for item in meal_items),
                    "carbs_g": sum(item["carbs_g"] for item in meal_items),
                    "fat_g": sum(item["fat_g"] for item in meal_items)
                }

                day_plan["meals"][meal_type] = {
                    "items": meal_items,
                    "totals": {k: round(v, 1) for k, v in meal_totals.items()}
                }

            weekly_plan[f"day_{day_num}"] = day_plan

        return self._add_summary(weekly_plan, profile)

    def _add_summary(
            self,
            meal_plan: Dict,
            user_profile: profile
    ) -> Dict:
        """Add summary information to meal plan"""

        summary = {
            "user_info": {
                "age": user_profile.get("age"),
                "weight_kg": user_profile.get("weight_kg"),
                "height_cm": user_profile.get("height_cm"),
                "gender": user_profile.get("gender"),
                "activity_level": user_profile.get("activity_level"),
                "target_goal": user_profile.get("target_goal")
            },
            "restrictions": {
                "health_conditions": user_profile.get("health_conditions", []),
                "allergies": user_profile.get("allergies", [])
            },
            "meal_plan": meal_plan
        }
        return summary

    print("✓ ProfessionalMealPlanner class defined!")


def generate_meal_plan_route(user_data: dict):
    # Convert comma-separated strings to lists
    if isinstance(user_data.get("health_conditions"), str):
        user_data["health_conditions"] = [hc.strip() for hc in user_data["health_conditions"].split(",")]
    if isinstance(user_data.get("allergies"), str):
        user_data["allergies"] = [
            a.strip() for a in user_data["allergies"].split(",")
        ]
    planner = ProfessionalMealPlanner(
        foods_csv="foods4.csv",
        profiles_csv="pakistan_user_profiles.csv",
        model_path="models/calorie_model.pkl"
    )

    try:
        plan = planner.generate_meal_plan(user_data, days=7)
        return {"status": "success", **plan}
    except Exception as e:
        return {"status": "error", "message": str(e)}