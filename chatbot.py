from typing import Dict, Any, Optional
from datetime import datetime
import ollama

DEFAULT_TIMEZONE = "Asia/Karachi"
DEFAULT_MODEL = "tomng/lfm2.5-instruct:1.2b"

WEEKDAYS = [
    "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday", "Sunday"
]

WEEKDAY_TO_DAY_KEY = {
    "Monday": "Day 1",
    "Tuesday": "Day 2",
    "Wednesday": "Day 3",
    "Thursday": "Day 4",
    "Friday": "Day 5",
    "Saturday": "Day 6",
    "Sunday": "Day 7",
}

MEAL_ORDER = ("breakfast", "lunch", "dinner")


class Chatbot:
    def get_current_day(self,user_data: dict, timezone: str = DEFAULT_TIMEZONE) -> str:
        user_profile = user_data.get("user_profile", {})
        if "current_day" in user_profile:
            return user_profile["current_day"]

        tz = datetime.now().astimezone().tzinfo
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(timezone)
        except Exception:
            pass

        today_index = datetime.now(tz).weekday()
        return WEEKDAYS[today_index]


    def split_health_and_allergies(self, profile: dict):
        raw_conditions = profile.get("healthConditions", [])
        allergies = profile.get("allergies", [])

        clean_health = []
        clean_allergies = list(allergies)

        for item in raw_conditions:
            if isinstance(item, str) and "allergy:" in item.lower():
                allergy_name = item.split(":")[1].strip()
                clean_allergies.append(allergy_name)
            else:
                clean_health.append(item)

        return clean_health, clean_allergies


    def flatten_today_plan(self,plan: dict, plan_type: str, today: str, day_key: Optional[str] = None) -> str:
        result = f"{plan_type} for {today}:\n"

        if not plan or "plan" not in plan:
            return result + "No plan available.\n"

        lookup_key = day_key if day_key else today
        day_details = plan.get("plan", {}).get(lookup_key)

        if not day_details:
            return result + f"No {plan_type.lower().split()[0]} assigned.\n"

        if plan_type == "Meal Plan":
            meals = day_details.get("meals", {})
            if not meals:
                return result + "No meals assigned.\n"

            daily_target = day_details.get("predicted_daily_calories", 0)
            if daily_target:
                result += f"Daily calorie target: {daily_target} kcal\n"

            ordered = [m for m in MEAL_ORDER if m in meals]
            ordered += [m for m in meals if m not in MEAL_ORDER]

            for meal_name in ordered:
                meal_info = meals.get(meal_name, {})
                items = meal_info.get("items", [])
                totals = meal_info.get("totals", {})
                meal_cal = totals.get("calories", 0)
                result += f"\n{meal_name.upper()} (~{meal_cal} kcal target):\n"
                if not items:
                    result += "  (no items)\n"
                    continue
                for item in items:
                    name = item.get("food_name", "")
                    qty = item.get("quantity", "")
                    unit = item.get("unit", "")
                    cal = item.get("calories", 0)
                    pro = item.get("protein_g", 0)
                    carb = item.get("carbs_g", 0)
                    fat = item.get("fat_g", 0)
                    if name:
                        result += (
                            f"  - {name}: {qty} {unit} | {cal} kcal "
                            f"| P:{pro}g C:{carb}g F:{fat}g\n"
                        )
            return result

        exercises = (
            day_details.get("exercises", [])
            if isinstance(day_details, dict)
            else day_details
        )

        for ex in exercises:
            name = ex.get("exercise_name", "Exercise")
            sets = ex.get("sets", 0)
            reps = ex.get("repetitions", 0)
            duration = ex.get("duration", 0)
            result += f"  • {name}: {sets} sets x {reps} reps, {duration} min\n"

        return result

    def _daily_progress_snapshot(self, profile: dict) -> dict:
        daily = profile.get("progress", {}).get("daily", {}).get("data", {}) or {}
        return {
            "plan_kcal": round(float(daily.get("totalEaten", 0) or 0), 1),
            "all_kcal": round(float(daily.get("totalAllEaten", 0) or 0), 1),
            "target_kcal": round(float(daily.get("dailyTarget", 0) or 0), 1),
            "pct": round(float(daily.get("progressPercentage", 0) or 0), 1),
            "unmatched": daily.get("unmatchedFoods", []) or [],
            "late": daily.get("lateMealAlerts", []) or [],
            "today": daily.get("today", ""),
            "meals": daily.get("dailyMeals", {}) or {},
            "has_data": bool(daily),
        }

    def _needs_honest_tone(self, snap: dict) -> bool:
        if not snap["has_data"]:
            return False
        if snap["pct"] < 25:
            return True
        statuses = [
            m.get("status", "under")
            for m in snap["meals"].values()
            if isinstance(m, dict)
        ]
        return bool(statuses) and all(s == "under" for s in statuses)

    def _build_verdict_block(self, profile: dict, snap: dict) -> str:
        if not snap["has_data"]:
            return ""

        name = profile.get("name", "User")
        goal = profile.get("goal", "")
        unmatched_str = ", ".join(snap["unmatched"]) if snap["unmatched"] else "none"
        off_plan_kcal = max(snap["all_kcal"] - snap["plan_kcal"], 0)

        if self._needs_honest_tone(snap):
            verdict = "NOT on track with the meal plan today"
            banned = (
                'doing great, great job, on track, keep it up, excellent, '
                'well done, every step counts, crush your goals'
            )
            required = (
                f'State plan progress is {snap["pct"]}% ({snap["plan_kcal"]} / '
                f'{snap["target_kcal"]} kcal plan-matched). Say user is UNDER target.'
            )
            if snap["unmatched"]:
                required += (
                    f' Name off-plan foods ({unmatched_str}) — NOT in meal plan, '
                    f'~{off_plan_kcal:.0f} kcal, do not count toward progress.'
                )
            if "gain" in str(goal).lower():
                required += f' For {goal}, urge today\'s planned meals from Meal Plan below.'
        else:
            verdict = "On track or close to meal-plan targets today"
            banned = ""
            required = "Summarize progress using the numbers below."

        return f"""
========================
TODAY'S VERDICT (read first)
========================
User: {name} | Goal: {goal} | Day: {snap["today"]}
Verdict: {verdict}
{required}
Forbidden phrases in your reply: {banned if banned else "none"}
"""

    def detect_query_intent(self, message: str) -> str:
        msg = message.lower().strip()

        weekly_kw = (
            "this week", "iss week", "is week", "weekly", "week progress",
            "week ke", "haftay", "hafte", "poora week", "pure week",
        )
        meal_kw = (
            "meal plan", "my plan", "your plan", "in my plan", "in the plan",
            "tell my meal", "what's in my plan", "whats in my plan",
            "what is in my plan", "plan mein", "kya hai plan", "khana plan",
            "menu", "planned meal", "planned food", "kya khana",
        )
        today_kw = (
            "how am i", "how im", "doing today", "today", "aaj",
            "right now", "daily progress", "kitna khaya aaj",
        )
        exercise_kw = (
            "workout", "exercise", "gym", "training", "exercise plan",
        )

        if any(k in msg for k in weekly_kw) or (
            "progress" in msg and ("week" in msg or "haft" in msg)
        ):
            return "weekly_progress"

        if any(k in msg for k in meal_kw) or (
            "plan" in msg and "progress" not in msg and "week" not in msg
        ):
            return "meal_plan"

        if any(k in msg for k in exercise_kw):
            return "exercise"

        if any(k in msg for k in today_kw):
            return "daily_progress"

        if "progress" in msg or "track" in msg or "status" in msg:
            return "daily_progress"

        return "general"

    def _primary_task_block(self, intent: str, today: str, profile: dict) -> str:
        goal = profile.get("goal", "")
        blocks = {
            "meal_plan": f"""
========================
PRIMARY TASK (answer ONLY this)
========================
The user wants their MEAL PLAN for {today} — NOT progress, NOT off-plan foods.
Copy foods from MEAL PLAN ({today}) below into three sections (use the same meal names and numbers):
🔹 Breakfast — list every breakfast item with quantity, unit, calories
🔹 Lunch — list every lunch item
🔹 Dinner — list every dinner item
End with daily calorie target from the data only (predicted_daily_calories). Do NOT invent totals.
Goal: {goal}. One short closing line is OK. Do NOT mention progress % or chai/samosa unless asked.
""",
            "weekly_progress": f"""
========================
PRIMARY TASK (answer ONLY this)
========================
The user wants THIS WEEK's progress (Monday–Sunday), not only today.
- Use the Weekly Progress / weeklyData section: each day, plan-matched calories vs target, status.
- Include weekly progressPercentage and off-plan foods if any.
- Today is {today} — include it as one day in the week, not the whole answer.
""",
            "daily_progress": f"""
========================
PRIMARY TASK (answer ONLY this)
========================
The user wants TODAY's progress ({today}).
- Use TODAY'S PROGRESS and Daily Progress sections (plan-matched %, meals, off-plan vs plan).
- Be honest if UNDER target; do not praise when plan progress is 0%.
""",
            "exercise": f"""
========================
PRIMARY TASK (answer ONLY this)
========================
The user wants their EXERCISE / WORKOUT plan for {today}.
- List exercises from EXERCISE PLAN section (sets, reps, duration).
- Do not focus on meal progress unless they asked.
""",
            "general": f"""
========================
PRIMARY TASK
========================
Answer the user's exact question using the data below. Do not default to progress if they asked something else.
""",
        }
        return blocks.get(intent, blocks["general"])

    def _build_example_reply(self, profile: dict, snap: dict) -> str:
        if not self._needs_honest_tone(snap):
            return ""

        name = profile.get("name", "User")
        unmatched = ", ".join(snap["unmatched"]) if snap["unmatched"] else "none"
        return f"""
========================
EXAMPLE (correct tone for this user today — match this honesty, not generic praise)
========================
Hey {name}!

🔹 Nutrition
- Plan progress today: {snap["pct"]}% — {snap["plan_kcal"]} / {snap["target_kcal"]} kcal from your meal plan (UNDER).
- Off-plan logged (not in your plan, not counted): {unmatched}.
- Focus on your planned breakfast, lunch, and dinner to work toward Weight Gain.

🔹 Workout
- Check your exercise plan when ready.

🔹 Tips
- Off-plan snacks do not replace planned meals.
"""

    def build_system_prompt(
        self, profile: Dict[str, Any], today: str, intent: str = "general"
    ) -> str:
        clean_health, clean_allergies = self.split_health_and_allergies(profile)
        snap = self._daily_progress_snapshot(profile)
        primary_task = self._primary_task_block(intent, today, profile)

        include_progress_tone = intent in (
            "daily_progress", "weekly_progress", "general"
        )
        verdict_block = (
            self._build_verdict_block(profile, snap) if include_progress_tone else ""
        )
        example_block = (
            self._build_example_reply(profile, snap)
            if include_progress_tone and self._needs_honest_tone(snap)
            else ""
        )

        meal_plan_str = self.flatten_today_plan(
            profile.get("meal_plan", {}), "Meal Plan", today, today
        )
        exercise_plan_str = self.flatten_today_plan(
            profile.get("exercise_plan", {}), "Exercise Plan", today, today
        )

        # ── Progress data ──────────────────────────────────────────
        weekly_progress = profile.get("progress", {}).get("weekly", {})
        monthly_progress = profile.get("progress", {}).get("monthly", {})
        daily_progress = profile.get("progress", {}).get("daily", {})

        weekly_data = weekly_progress.get("data", {})
        monthly_data = monthly_progress.get("data", {})
        daily_data = daily_progress.get("data", {})

        # ── Late meals & unmatched (weekly) ────────────────────────
        weekly_late_meals = weekly_data.get("lateMealAlerts", [])
        weekly_unmatched = weekly_data.get("unmatchedFoods", [])
        weekly_late_str = ', '.join(weekly_late_meals) if weekly_late_meals else "None"
        weekly_unmatched_str = ', '.join(weekly_unmatched) if weekly_unmatched else "None"

        # ── Late meals & unmatched (daily) ─────────────────────────
        daily_late_meals = daily_data.get("lateMealAlerts", [])
        daily_unmatched = daily_data.get("unmatchedFoods", [])
        daily_late_str = ', '.join(daily_late_meals) if daily_late_meals else "None"
        daily_unmatched_str = ', '.join(daily_unmatched) if daily_unmatched else "None"

        # ── Late meals & unmatched (monthly) ───────────────────────
        monthly_late_meals = monthly_data.get("lateMealAlerts", [])
        monthly_unmatched = monthly_data.get("unmatchedFoods", [])
        monthly_late_str = ', '.join(monthly_late_meals) if monthly_late_meals else "None"
        monthly_unmatched_str = ', '.join(monthly_unmatched) if monthly_unmatched else "None"

        # progressPercentage and macro *Percentage are already 0–100 from track_progress
        weekly_progress_pct = round(float(weekly_data.get("progressPercentage", 0) or 0), 1)
        monthly_progress_pct = round(float(monthly_data.get("progressPercentage", 0) or 0), 1)
        daily_progress_pct = round(float(daily_data.get("progressPercentage", 0) or 0), 1)

        daily_meal_data = daily_data.get("dailyMeals", {})
        daily_meal_breakdown = ""
        for meal_name, meal_info in daily_meal_data.items():
            eaten = meal_info.get("eaten_calories", 0)
            target = meal_info.get("target_calories", 0)
            status = meal_info.get("status", "under")
            protein = meal_info.get("protein_g", 0)
            fat = meal_info.get("fat_g", 0)
            carbs = meal_info.get("carbs_g", 0)
            daily_meal_breakdown += (
                f"  - {meal_name.capitalize()}: {eaten} kcal / {target} kcal — {status.upper()}\n"
                f"    P:{protein}g | C:{carbs}g | F:{fat}g\n"
            )
        if not daily_meal_breakdown:
            daily_meal_breakdown = "  - No food logged today.\n"

        daily_plan_kcal = round(float(daily_data.get("totalEaten", 0) or 0), 1)
        daily_all_kcal = round(float(daily_data.get("totalAllEaten", 0) or 0), 1)
        daily_target_kcal = round(float(daily_data.get("dailyTarget", 0) or 0), 1)

        daily_summary = f"""Daily Progress ({daily_data.get('today', today)}):
                - Plan-matched calories (counts toward goal): {daily_plan_kcal} / {daily_target_kcal} kcal — {daily_progress_pct}%
                - All food logged today (includes off-plan): {daily_all_kcal} kcal
                - Late Meals: {daily_late_str}
                - Out-of-Plan Foods (NOT counted in progress): {daily_unmatched_str}
                - Meal Breakdown:
                {daily_meal_breakdown}
                """ if daily_data else "No daily progress data."

        today_progress = ""
        if daily_data:
            meal_statuses = [
                m.get("status", "under")
                for m in daily_meal_data.values()
                if isinstance(m, dict)
            ]
            if meal_statuses and all(s == "under" for s in meal_statuses):
                meal_day_status = "UNDER target on all logged meals"
            elif meal_statuses and all(s == "over" for s in meal_statuses):
                meal_day_status = "OVER target on all logged meals"
            elif meal_statuses:
                meal_day_status = "mixed (see meal breakdown)"
            else:
                meal_day_status = "no plan meals logged yet"

            off_plan_kcal = max(daily_all_kcal - daily_plan_kcal, 0)
            today_progress = f"""AUTHORITATIVE STATUS FOR TODAY — use these facts exactly:
            - Plan-matched calories (from meal plan only): {daily_plan_kcal} / {daily_target_kcal} kcal — {daily_progress_pct}%
            - Meal status: {meal_day_status}
            - Foods NOT in meal plan (logged but excluded from progress): {daily_unmatched_str}
            - Off-plan calories only: {off_plan_kcal:.0f} kcal (do NOT describe as meeting daily targets)
            - Late meals today (only if eaten outside scheduled time): {daily_late_str}
            """


        # ── Weekly day breakdown ───────────────────────────────────
        weekly_day_data = weekly_data.get("weeklyData", {})
        weekly_day_breakdown = ""
        for day in WEEKDAYS:
            day_info = weekly_day_data.get(day, {})
            plan_matched = day_info.get("calories", 0)
            all_eaten = day_info.get("allEaten", 0)
            target = day_info.get("target", 0)
            status = day_info.get("status", "under")
            weekly_day_breakdown += (
                f"  - {day}: Plan-Matched={plan_matched} kcal, "
                f"All Logged={all_eaten} kcal, "
                f"Target={target} kcal — {status.upper()}\n"
            )

        if not weekly_day_data:
            weekly_day_breakdown = "  - No weekly progress data.\n"
        # ── Monthly week breakdown ─────────────────────────────────
        monthly_week_data = monthly_data.get("monthlyData", {})
        monthly_week_breakdown = ""
        for week, week_info in monthly_week_data.items():
            plan_matched = week_info.get("calories", 0)
            target = week_info.get("target", 0)
            percentage = week_info.get("percentage", 0)
            if plan_matched > 0:
                monthly_week_breakdown += (
                    f"  - {week}: {plan_matched} kcal / {target} kcal — {percentage}%\n"
                )
        if not monthly_week_breakdown:
            monthly_week_breakdown = "  - No plan-matched food logged this month.\n"

        weekly_plan_kcal = round(
            sum(
                float(d.get("calories", 0) or 0)
                for d in weekly_day_data.values()
                if isinstance(d, dict)
            ),
            1,
        )
        weekly_all_kcal = round(float(weekly_data.get("totalAllEaten", 0) or 0), 1)

        weekly_summary = f"""Weekly Progress:
        - Plan-matched calories (counts toward goal): {weekly_plan_kcal} kcal — {weekly_progress_pct}%
        - All food logged this week (includes off-plan): {weekly_all_kcal} kcal
        - Protein: {round(float(weekly_data.get('proteinPercentage', 0) or 0), 1)}%
        - Carbs: {round(float(weekly_data.get('carbsPercentage', 0) or 0), 1)}%
        - Fats: {round(float(weekly_data.get('fatsPercentage', 0) or 0), 1)}%
        - Late Meals: {weekly_late_str}
        - Out-of-Plan Foods (NOT counted in progress): {weekly_unmatched_str}
        - Daily Breakdown:
        {weekly_day_breakdown}
        """ if weekly_data else "No weekly progress data."
        monthly_plan_kcal = round(
            sum(
                float(w.get("calories", 0) or 0)
                for w in monthly_week_data.values()
                if isinstance(w, dict)
            ),
            1,
        )
        monthly_all_kcal = round(float(monthly_data.get("totalAllEaten", 0) or 0), 1)

        monthly_summary = f"""Monthly Progress:
                - Plan-matched calories: {monthly_plan_kcal} kcal — {monthly_progress_pct}%
                - All food logged (includes off-plan): {monthly_all_kcal} kcal
                - Protein: {round(float(monthly_data.get('proteinPercentage', 0) or 0), 1)}%
                - Carbs: {round(float(monthly_data.get('carbsPercentage', 0) or 0), 1)}%
                - Fats: {round(float(monthly_data.get('fatsPercentage', 0) or 0), 1)}%
                - Late Meals: {monthly_late_str}
                - Out-of-Plan Foods (NOT counted): {monthly_unmatched_str}
                - Weekly Breakdown:
                {monthly_week_breakdown}
                """ if monthly_data else "No monthly progress data."
        disclaimer = "Disclaimer: This is for informational purposes only. Consult a healthcare professional before making changes to your diet or exercise routine."
        if not clean_health:
            disclaimer = ""

        goal = profile.get("goal", "")

        critical_footer = ""
        if include_progress_tone and daily_unmatched_str != "None":
            critical_footer = f"""
            ========================
            CRITICAL — OFF-PLAN FOODS (MUST FOLLOW)
            ========================
            - These foods were logged but are NOT in the user's meal plan: {daily_unmatched_str}
            - They do NOT count toward plan progress or daily meal targets.
            - Do NOT praise, excuse, or minimize them (no "won't affect much", "it's okay", "keep it up" for off-plan snacks).
            - Do NOT call them late meals unless Late Meals above lists them (today: {daily_late_str}).
            - Do NOT say the user met their calorie goal using off-plan food; plan-matched today is {daily_plan_kcal} kcal only.
            - For goal "{goal}" while UNDER plan targets: encourage today's planned meals from the Meal Plan section, not off-plan snacks.
            """
        elif (
            include_progress_tone
            and daily_data
            and daily_plan_kcal <= 0
            and "gain" in str(goal).lower()
        ):
            critical_footer = f"""
            ========================
            CRITICAL — UNDER PLAN TODAY
            ========================
            - Plan-matched calories today: 0. User goal: {goal}.
            - Encourage following today's planned breakfast/lunch/dinner from the Meal Plan — do not invent foods.
            """

        honest_tone = include_progress_tone and self._needs_honest_tone(snap)
        tone_rule = (
            "- Be supportive but HONEST. If Verdict says NOT on track, do NOT praise progress."
            if honest_tone
            else "- Be supportive and clear. Answer what was asked."
        )

        progress_sections = ""
        if intent != "meal_plan":
            progress_sections = f"""
            ========================
            TODAY'S PROGRESS
            ========================
            {today_progress}

            ========================
            DAILY, WEEKLY & MONTHLY SUMMARY
            ========================
            {daily_summary}
            {weekly_summary}
            {monthly_summary}
            """

        meal_section = ""
        exercise_section = ""
        if intent in ("meal_plan", "general", "daily_progress", "weekly_progress"):
            meal_section = f"""
            ========================
            MEAL PLAN ({today})
            ========================
            {meal_plan_str}
            """
        if intent in ("exercise", "general", "daily_progress"):
            exercise_section = f"""
            ========================
            EXERCISE PLAN ({today})
            ========================
            {exercise_plan_str}
            """

        return f"""
            You are NutriFit AI Coach — nutrition and fitness assistant in a fitness app.

            {primary_task}

            {verdict_block}
            {example_block}

            ========================
            BEHAVIOR RULES
            ========================
            - Use ONLY the data below. Do not invent numbers.
            - Follow PRIMARY TASK — do not ignore the user's question type.
            {tone_rule}
            - Plan-matched calories = totalEaten. Off-plan = unmatchedFoods (not in Meal Plan).
            - Match the user's message language (English / Roman Urdu / Urdu script).
            - Short, structured reply.

            ========================
            USER PROFILE
            ========================
            - Name: {profile.get("name")}
            - Age: {profile.get("age")}
            - Weight: {profile.get("weight")} kg
            - Height: {profile.get("height")} ft
            - Gender: {profile.get("gender")}
            - Activity Level: {profile.get("activitylevel")}
            - Target Goal: {profile.get("goal")}
            - Health Conditions: {clean_health}
            - Allergies: {clean_allergies}
            - BMI: {profile.get("bmi")}
            - BMR: {profile.get("bmr")}
            - TDEE: {profile.get("tdee")}

            {meal_section}
            {exercise_section}
            {progress_sections}

            ========================
            SAFETY
            ========================
            If user asks for medical advice: "Please consult a qualified healthcare professional for medical advice."

            {critical_footer}

            ========================
            DISCLAIMER
            ========================
            {disclaimer}
        """

    _PRAISE_WHEN_UNDER = (
        "doing great", "doing well", "great job", "on track", "keep it up",
        "excellent", "well done", "every step counts", "right track",
    )

    def _reply_praises_when_under(self, reply: str) -> bool:
        text = reply.lower()
        return any(phrase in text for phrase in self._PRAISE_WHEN_UNDER)

    def _reply_ignores_intent(self, reply: str, intent: str) -> bool:
        text = reply.lower()
        if intent == "meal_plan":
            return not (
                "breakfast" in text
                and "lunch" in text
                and "dinner" in text
            )
        if intent == "weekly_progress":
            return "monday" not in text and "week" not in text[:80]
        return False

    def call_ai(
        self,
        system_prompt: str,
        user_message: str,
        model: str = DEFAULT_MODEL,
        must_be_honest: bool = False,
        intent: str = "general",
    ) -> str:
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            response = ollama.chat(
                model=model,
                messages=messages,
                options={"temperature": 0.1, "top_p": 0.7},
            )
            reply = response["message"]["content"]

            if must_be_honest and self._reply_praises_when_under(reply):
                messages.append({"role": "assistant", "content": reply})
                messages.append({
                    "role": "user",
                    "content": (
                        "Wrong tone: user is at 0% plan progress and UNDER target. "
                        "Rewrite without saying doing great, on track, or keep it up. "
                        "State 0% plan-matched progress and off-plan foods if any."
                    ),
                })
                retry = ollama.chat(
                    model=model,
                    messages=messages,
                    options={"temperature": 0.05, "top_p": 0.6},
                )
                reply = retry["message"]["content"]

            if self._reply_ignores_intent(reply, intent):
                messages.append({"role": "assistant", "content": reply})
                refocus = {
                    "meal_plan": (
                        "Format the meal plan with three sections: Breakfast, Lunch, Dinner. "
                        "Under each section list the foods from MEAL PLAN with portions and kcal. "
                        "Use predicted_daily_calories for daily total. No progress stats."
                    ),
                    "weekly_progress": (
                        "Answer THIS WEEK (Mon–Sun) using weeklyData. "
                        "Do not only describe today."
                    ),
                }.get(intent)
                if refocus:
                    messages.append({"role": "user", "content": refocus})
                    retry2 = ollama.chat(
                        model=model,
                        messages=messages,
                        options={"temperature": 0.05, "top_p": 0.6},
                    )
                    reply = retry2["message"]["content"]

            return reply

        except Exception as e:
            print("Ollama Error:", str(e))
            return "AI is temporarily unavailable. Please try again."


    def generate_chat_response(self,user_data: dict):
        user_profile = user_data.get("user_profile")
        user_message = user_data.get("message", "").strip()

        if not user_profile or not user_message:
            return {
                "status": "error",
                "message": "Missing user profile or message"
            }

        timezone = user_data.get("timezone", DEFAULT_TIMEZONE)
        today = self.get_current_day(user_data, timezone)

        intent = self.detect_query_intent(user_message)
        system_prompt = self.build_system_prompt(user_profile, today, intent)
        snap = self._daily_progress_snapshot(user_profile)
        use_honest_tone = intent in ("daily_progress", "weekly_progress") and self._needs_honest_tone(snap)

        ai_reply = self.call_ai(
            system_prompt,
            user_message,
            must_be_honest=use_honest_tone,
            intent=intent,
        )

        return {
            "status": "success",
            "reply": ai_reply
        }
chatbot = Chatbot()