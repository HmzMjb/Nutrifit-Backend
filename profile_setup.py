from datetime import datetime, timedelta
from flask import jsonify, request
# =========================================================
# PROFILE CALCULATOR CLASS
# =========================================================
class profile_setup:
    SAFE_LOSS_PER_WEEK = 1.0
    SAFE_GAIN_PER_WEEK = 1.0
    REQUIRED_FIELDS = ["age", "weight", "height", "gender", "activitylevel", "goal"]

    def __init__(self, data):
        self.data = data or {}
        self.meal_plan_last_updated = self.data.get("meal_plan_last_updated")
        self.errors = {}
        self.warnings = {}
        self.suggested_target_weight = None
        self.timeline_weeks = None
        self.weight_history = self.data.get("weightHistory", [])

        # Parsed values
        self.age = 0
        self.weight_kg = 0
        self.height_ft = 0
        self.height_m = 0
        self.height_cm = 0
        self.target_weight = 0
        self.gender = ""
        self.activity = ""
        self.goal = ""
        self.timeline_str = None

        # Calculated values
        self.bmi = None
        self.bmr = None
        self.tdee = None
        self.suggested_goal = None
        self.min_healthy_weight = None
        self.max_healthy_weight = None
        self.max_safe_loss = None
        self.max_safe_gain = None
        self.target_min = None
        self.target_max = None


    # ---------- VALIDATION ----------
    def validate_required_fields(self):
        for field in self.REQUIRED_FIELDS:
            if field not in self.data or self.data[field] in [None, ""]:
                self.errors[field] = "This field is required"

    def parse_numeric_fields(self):
        try:
            self.age = int(self.data.get("age", 0))
            if self.age <= 0:
                self.errors["age"] = "Age must be greater than 0"
        except:
            self.errors["age"] = "Age must be a valid number"

        try:
            self.weight_kg = float(self.data.get("weight", 0))
            if self.weight_kg <= 0:
                self.errors["weight"] = "Weight must be positive"
        except:
            self.errors["weight"] = "Weight must be a valid number"

        try:
            self.target_weight = float(self.data.get("targetWeight", 0))
            if self.target_weight <= 0:
                self.errors["targetWeight"] = "Target weight must be positive"
        except:
            self.errors["targetWeight"] = "Target weight must be a valid number"

        try:
            self.height_ft = float(self.data.get("height", 0))
            if self.height_ft <= 0:
                self.errors["height"] = "Height must be positive"
        except:
            self.errors["height"] = "Height must be a valid number"

        self.gender = str(self.data.get("gender", "")).lower()
        self.activity = str(self.data.get("activitylevel", "")).lower()
        self.goal = str(self.data.get("goal", "")).lower()
        self.timeline_str = self.data.get("timeline")

    def calculate_metrics(self):
        self.height_m = self.height_ft * 0.3048
        self.height_cm = self.height_m * 100
        self.bmi = self.weight_kg / (self.height_m ** 2)

        if self.gender == "male":
            self.bmr = (10 * self.weight_kg) + (6.25 * self.height_cm) - (5 * self.age) + 5
        else:
            self.bmr = (10 * self.weight_kg) + (6.25 * self.height_cm) - (5 * self.age) - 161

        activity_multipliers = {
            "sedentary": 1.2,
            "lightly active": 1.375,
            "moderately active": 1.55,
            "very active": 1.725,
            "extra active": 1.9
        }

        self.tdee = self.bmr * activity_multipliers.get(self.activity, 1.2)
        self.calories_burned = self.tdee - self.bmr
        print("Calories Burned: ",self.calories_burned)

    def validate_goal(self):
        # Determine suggested goal based on BMI
        if self.bmi <= 18.5:
            self.suggested_goal = "weight gain"
            self.goal_warning = "You are underweight."
        elif self.bmi <= 25:
            self.suggested_goal = "maintain"
            self.goal_warning = "You are fit."
        else:
            self.suggested_goal = "weight loss"
            self.goal_warning = "You are overweight"

        # If user's selected goal doesn't match BMI suggestion
        if self.goal != self.suggested_goal:
            self.warnings["goal"] = (
                f"{self.goal_warning} Suggested goal based on BMI: {self.suggested_goal}"
            )

    def process_timeline(self):
        if not self.timeline_str:
            return
        try:
            timeline_date = datetime.strptime(self.timeline_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            delta_days = (timeline_date - today).days
            if delta_days < 7:
                self.errors["timeline"] = "Timeline must be at least 1 week ahead"
            else:
                self.timeline_weeks = delta_days // 7
                print(f"Number of weeks: {self.timeline_weeks}")
        except:
            self.errors["timeline"] = "Invalid date format (YYYY-MM-DD)"


    def validate_timeline_against_goal(self):
        if not self.timeline_str:
            return

        try:
            # parse the user's chosen date
            timeline_date = datetime.strptime(self.timeline_str, "%Y-%m-%d").date()
            today = datetime.now().date()

            if self.goal == "weight loss":
                required_loss = max(self.weight_kg - self.target_weight, 0)
                required_weeks = required_loss / self.SAFE_LOSS_PER_WEEK
            elif self.goal == "weight gain":
                required_gain = max(self.target_weight - self.weight_kg, 0)
                required_weeks = required_gain / self.SAFE_GAIN_PER_WEEK
            else:  # maintain
                required_weeks = 0

            # calculate suggested safe date
            suggested_date = today + timedelta(weeks=int(required_weeks))
            self.suggested_date = suggested_date  # store for frontend

            # check if user's selected date is too early
            if timeline_date < suggested_date:
                self.errors["timeline"] = (
                    f"Timeline too short. To safely achieve your goal, "
                    f"choose a date on or after {suggested_date.strftime('%Y-%m-%d')}."
                )

        except:
            self.errors["timeline"] = "Invalid date format (YYYY-MM-DD)"
    def calculate_healthy_weights(self):
        self.min_healthy_weight = 18.5 * (self.height_m ** 2)
        self.max_healthy_weight = 24.9 * (self.height_m ** 2)
        if self.timeline_weeks:
            self.max_safe_loss = self.SAFE_LOSS_PER_WEEK * self.timeline_weeks
            self.max_safe_gain = self.SAFE_GAIN_PER_WEEK * self.timeline_weeks

    def validate_target_weight(self):
        if self.goal == "weight loss":

            if self.max_safe_loss and (self.weight_kg - self.target_weight > self.max_safe_loss):
                self.errors["targetWeight"] = (
                    f"Target weight too low. Max safe loss: {self.max_safe_loss} kg"
                )
                self.suggested_target_weight = max(
                    self.min_healthy_weight,
                    self.weight_kg - self.max_safe_loss
                )

            if self.target_weight < self.min_healthy_weight:
                self.errors["targetWeight"] = (
                    f"Target weight below healthy BMI. "
                    f"Min safe: {round(self.min_healthy_weight, 2)} kg"
                )
                self.suggested_target_weight = self.min_healthy_weight

        elif self.goal == "weight gain":


            if self.max_safe_gain and (self.target_weight - self.weight_kg > self.max_safe_gain):
                self.errors["targetWeight"] = f"Max safe gain: {self.max_safe_gain} kg"
                self.suggested_target_weight = min(
                    self.max_healthy_weight,
                    self.weight_kg + self.max_safe_gain
                )

            if self.target_weight > self.max_healthy_weight:
                self.errors["targetWeight"] = (
                    f"Max safe: {round(self.max_healthy_weight, 2)} kg"
                )
                self.suggested_target_weight = self.max_healthy_weight

        elif self.goal == "maintain":

            if (
                    self.target_weight < self.min_healthy_weight or
                    self.target_weight > self.max_healthy_weight
            ):
                self.errors["targetWeight"] = (
                    f"Maintain weight outside healthy BMI range "
                    f"({round(self.min_healthy_weight, 2)}–{round(self.max_healthy_weight, 2)} kg)"
                )
                self.suggested_target_weight = max(
                    min(self.target_weight, self.max_healthy_weight),
                    self.min_healthy_weight
                )

        # -------------------------------------------------
        # FINAL GLOBAL SAFETY CHECK (applies to ALL goals)
        # -------------------------------------------------
        if (
                self.min_healthy_weight is not None and
                self.max_healthy_weight is not None and
                (
                        self.target_weight < self.min_healthy_weight or
                        self.target_weight > self.max_healthy_weight
                )
        ):
            self.errors["targetWeight"] = (
                f"Target weight must be within healthy BMI range "
                f"({round(self.min_healthy_weight, 2)}–{round(self.max_healthy_weight, 2)} kg)"
            )
            self.suggested_target_weight = max(
                min(self.target_weight, self.max_healthy_weight),
                self.min_healthy_weight
            )

    def calculate_target_range(self):
        if self.goal == "weight loss":
            self.target_min = round(self.min_healthy_weight, 2)
            self.target_max = round(self.weight_kg - (self.max_safe_loss if self.max_safe_loss else 0.5), 2)
            self.target_max = min(self.target_max, self.weight_kg - 0.1)
        elif self.goal == "weight gain":
            self.target_min = round(self.weight_kg + (self.max_safe_gain if self.max_safe_gain else 0.5), 2)
            self.target_max = round(self.max_healthy_weight, 2)
        elif self.goal == "maintain":
            self.target_min = round(max(self.weight_kg, self.min_healthy_weight), 2)
            self.target_max = round(min(self.weight_kg, self.max_healthy_weight), 2)

    def get_result(self):
        return {
            "bmi": round(self.bmi, 2),
            "bmr": round(self.bmr, 2),
            "tdee": round(self.tdee, 2),
            "calories_burned": round(self.tdee - self.bmr, 2),
            "suggested_goal": self.suggested_goal,
            "timeline_weeks": self.timeline_weeks,
            "suggested_target_weight": round(self.suggested_target_weight, 2) if self.suggested_target_weight else None,
            "target_weight_range": {
                "min": self.target_min,
                "max": self.target_max
            }
        }

    def run(self):
        self.validate_required_fields()

        # STEP 1: Parse fields — reuse the method, don't duplicate code
        self.parse_numeric_fields()

        if self.errors:
            return self.errors, self.warnings, {}

        # STEP 2: Calculate BMI/BMR
        self.calculate_metrics()

        # STEP 3: Validate goal
        self.validate_goal()

        # STEP 4: Process timeline + healthy range
        self.process_timeline()
        self.calculate_healthy_weights()
        self.calculate_target_range()

        # STEP 5: Validate target weight
        if not self.data.get("targetWeight"):
            self.errors["targetWeight"] = (
                f"Ideal Weight ({round(self.min_healthy_weight, 2)}–{round(self.max_healthy_weight, 2)} kg)"
            )

        else:
            try:
                self.target_weight = float(self.data.get("targetWeight"))
                if self.target_weight <= 0:
                    self.errors["targetWeight"] = "Target weight must be positive"
            except:
                self.errors["targetWeight"] = "Target weight must be a valid number"

            self.validate_timeline_against_goal()
            self.validate_target_weight()

        # ----------------------------
        # STEP 6: Generate meal plan — only if no errors
        # ----------------------------
        if self.errors:
            return self.errors, self.warnings, {**self.get_result(), "meal_plan": {}}

        return self.errors, self.warnings, {
            **self.get_result(),
        }
# =========================================================
# RUNTIME FUNCTIONS FOR FLASK
# =========================================================
def profile_validate():
    data = request.get_json() or {}

    errors, warnings, result = profile_setup(data).run()

    if errors:
        return jsonify({
            "status": "error",
            "errors": errors,
            "warnings": warnings,
            "suggested_target_weight": result.get("suggested_target_weight"),
            "target_weight_range": result.get("target_weight_range")
        }), 400

    return jsonify({
        "status": "success",
        "errors": {},
        "warnings": warnings,
        **result
    }), 200
def profile_setup_route():
    data = request.get_json() or {}
    errors, warnings, result = profile_setup(data).run()

    if errors:
        return jsonify({
            "status": "error",
            "errors": errors,
            "warnings": warnings,
            "suggested_target_weight": result.get("suggested_target_weight"),
            "target_weight_range": result.get("target_weight_range")
        }), 400

    return jsonify({
        "status": "success",
        "message": "Profile saved successfully",
        **result,
        "warnings": warnings,
        "timeline_weeks": result.get("timeline_weeks")
    })