from datetime import datetime, timedelta
import calendar


def clean_numpy(data):
    if isinstance(data, dict):
        return {k: clean_numpy(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_numpy(i) for i in data]
    elif isinstance(data, bool):
        return data
    elif hasattr(data, "item"):
        return round(float(data.item()), 2)
    elif isinstance(data, (float, int)):
        return round(float(data), 2)
    return data


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

MEAL_WINDOWS = {
    "breakfast": (5, 11),
    "lunch":     (11, 16),
    "dinner":    (16, 24),
}


class TrackProgress:

    def __init__(self, data):
        self.data = data
        self.period = data.get("period", "weekly")
        self.meal_plan = data.get("meal_plan", {})
        self.eaten_foods = data.get("eaten_foods", [])
        self.today = datetime.today()
        self.days_in_month = calendar.monthrange(self.today.year, self.today.month)[1]
        self.exercise_videos = data.get("exercise_videos", [])

        profile_updated_at = data.get("profile_updated_at")
        try:
            if profile_updated_at and "seconds=" in str(profile_updated_at):
                seconds = int(str(profile_updated_at).split("seconds=")[1].split(",")[0])
                self.profile_start_date = datetime.fromtimestamp(seconds)
            else:
                self.profile_start_date = self.today
        except Exception:
            self.profile_start_date = self.today

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------

    @staticmethod
    def _parse_date(created_at):
        if isinstance(created_at, dict) and "seconds" in created_at:
            return datetime.fromtimestamp(created_at["seconds"])
        try:
            return datetime.fromisoformat(str(created_at))
        except Exception:
            return datetime.fromisoformat(str(created_at).split(".")[0])

    @staticmethod
    def _normalize(name: str) -> str:
        return name.strip().lower()

    def _workout_hours(self, date_filter_fn) -> float:
        total = 0.0
        for video in self.exercise_videos:
            created_at = video.get("createdAt")
            if not created_at:
                continue
            try:
                dt = self._parse_date(created_at)
                if date_filter_fn(dt):
                    total += float(video.get("duration", 0))
            except Exception:
                continue
        return round(total, 2)
    def _build_meal_plan_by_day(self):
        plan = {}
        for day_index, day_name in enumerate(DAYS):
            day_info = self.meal_plan.get(day_name)
            if not day_info:
                continue
            foods = set()
            meal_windows = {}
            for meal_name, meal in day_info.get("meals", {}).items():
                key = meal_name.lower()
                window = MEAL_WINDOWS.get(key, (0, 24))
                meal_foods = set()
                for item in meal.get("items", []):
                    n = item.get("food_name", "")
                    if n:
                        normalized = self._normalize(n)
                        foods.add(normalized)
                        meal_foods.add(normalized)
                meal_windows[key] = {
                    "foods":  meal_foods,
                    "window": window,
                }
            plan[day_index] = {
                "foods":           foods,
                "target_calories": float(day_info.get("predicted_daily_calories", 0)),
                "macros_target":   day_info.get("daily_macros_target", {}),
                "meals":           day_info.get("meals", {}),
                "meal_windows":    meal_windows,
            }
        return plan

    def check_adaptive_plan(self):
        weight_history = self.data.get("weightHistory", [])
        goal = str(self.data.get("goal", "")).lower()
        meal_plan_last_updated = self.data.get("meal_plan_last_updated")

        if not meal_plan_last_updated:
            return {
                "should_regenerate": False,
                "reason": "no_last_updated",
                "14_days_passed": False,
                "no_of_days_passed": 0,
                "progress": False,
            }
        try:
            last_date = datetime.fromisoformat(str(meal_plan_last_updated))
        except:
            return {
                "should_regenerate": False,
                "reason": "invalid_date",
                "14_days_passed": False,
                "no_of_days_passed": 0,
                "progress": False,
            }

        days_passed = (datetime.now() - last_date).days
        fourteen_days_passed = days_passed >= 14

        # ── Progress check (weight history se) ──────────────────────────────
        progress = False
        if len(weight_history) >= 2:
            sorted_history = sorted(weight_history, key=lambda x: x["date"])
            latest   = float(sorted_history[-1]["weight"])
            previous = float(sorted_history[-2]["weight"])
            diff = latest - previous
            if goal == "weight loss" and diff < 0:
                progress = True
            elif goal == "weight gain" and diff > 0:
                progress = True
            elif goal == "maintain" and abs(diff) < 0.5:
                progress = True

        if not fourteen_days_passed:
            return {
                "should_regenerate": False,
                "reason": "not_2_weeks_yet",
                "days_remaining": 14 - days_passed,
                "14_days_passed": False,
                "no_of_days_passed": days_passed,
                "progress": progress,
            }

        # Step 2: Meal plan follow kiya? (last 14 din mein 70%+ din)
        eaten_foods = self.data.get("eaten_foods", [])
        last_14_days = datetime.now() - timedelta(days=14)
        plan_by_day = self._build_meal_plan_by_day()

        daily_calories = {}
        daily_target = {}

        for food in eaten_foods:
            if not food.get("consumed", False):
                continue
            created_at = food.get("created_at")
            if not created_at:
                continue
            try:
                food_date = self._parse_date(created_at)
                if food_date < last_14_days:
                    continue
                day_key = food_date.date()
                day_index = food_date.weekday()
                name = self._normalize(food.get("food_name", ""))
                hour = food_date.hour
                matched, _, _ = self._is_matched_with_time(name, hour, day_index, plan_by_day)
                if matched:
                    daily_calories[day_key] = daily_calories.get(day_key, 0) + float(food.get("calories", 0))
                if day_index in plan_by_day:
                    daily_target[day_key] = plan_by_day[day_index]["target_calories"]
            except:
                continue

        matched_days = sum(
            1 for day, eaten in daily_calories.items()
            if daily_target.get(day, 0) > 0 and (eaten / daily_target[day]) >= 0.70
        )
        total_days_checked = len(daily_target)
        plan_followed = total_days_checked >= 10 and matched_days >= 10

        if not plan_followed:
            return {
                "should_regenerate": False,
                "reason": "plan_not_followed",
                "followed_days": matched_days,
                "14_days_passed": True,
                "no_of_days_passed": days_passed,
                "progress": progress,
            }

        # Step 3: Weight improve hua?
        if len(weight_history) < 2:
            return {
                "should_regenerate": False,
                "reason": "not_enough_weight_data",
                "14_days_passed": True,
                "no_of_days_passed": days_passed,
                "progress": False,
            }

        sorted_history = sorted(weight_history, key=lambda x: x["date"])
        latest   = float(sorted_history[-1]["weight"])
        previous = float(sorted_history[-2]["weight"])
        diff = latest - previous

        if goal == "weight loss" and diff < -0.5:
            return {
                "should_regenerate": False,
                "reason": "progress_ok",
                "14_days_passed": True,
                "no_of_days_passed": days_passed,
                "progress": True,
            }
        elif goal == "weight gain" and diff > 0.5:
            return {
                "should_regenerate": False,
                "reason": "progress_ok",
                "14_days_passed": True,
                "no_of_days_passed": days_passed,
                "progress": True,
            }
        elif goal == "maintain" and abs(diff) < 0.5:
            return {
                "should_regenerate": False,
                "reason": "progress_ok",
                "14_days_passed": True,
                "no_of_days_passed": days_passed,
                "progress": True,
            }

        return {
            "should_regenerate": True,
            "reason": "followed_but_no_progress",
            "followed_days": matched_days,
            "weight_diff": round(diff, 2),
            "14_days_passed": True,
            "no_of_days_passed": days_passed,
            "progress": False,
        }
    def _is_matched_with_time(self, food_name: str, hour: int, day_index: int, plan_by_day: dict):
        """
        Returns: (matched: bool, late: bool, expected_meal: str)
        matched = naam aur time dono sahi
        late    = naam match lekin galat waqt
        """
        if day_index not in plan_by_day:
            return False, False, ""

        name = self._normalize(food_name)
        meal_windows = plan_by_day[day_index].get("meal_windows", {})

        for meal_name, info in meal_windows.items():
            name_hit = any(name in pf or pf in name for pf in info["foods"])
            if name_hit:
                w_start, w_end = info["window"]
                in_time = w_start <= hour < w_end
                if in_time:
                    return True, False, meal_name   # sahi waqt, sahi khana
                else:
                    return False, True, meal_name   # sahi khana, galat waqt

        return False, False, ""  # naam bhi match nahi

    def _macro_percentages(self, eaten: dict, target: dict) -> dict:
        return {
            "proteinPercentage": min((eaten["protein"] / target["protein"]) * 100, 100) if target.get("protein") else 0,
            "fatsPercentage":    min((eaten["fat"]     / target["fat"])     * 100, 100) if target.get("fat")     else 0,
            "carbsPercentage":   min((eaten["carbs"]   / target["carbs"])   * 100, 100) if target.get("carbs")   else 0,
        }

    # --------------------------------------------------
    # DAILY PROGRESS
    # --------------------------------------------------

    def daily_progress(self):
        today         = self.today.date()
        today_index   = self.today.weekday()
        plan_by_day   = self._build_meal_plan_by_day()
        day_plan      = plan_by_day.get(today_index, {})
        planned_meals = day_plan.get("meals", {})

        meal_slots = {}
        for meal_name, meal_data in planned_meals.items():
            key        = meal_name.lower()
            window     = MEAL_WINDOWS.get(key, (0, 24))
            foods      = {self._normalize(i.get("food_name", "")) for i in meal_data.get("items", [])}
            target_cal = sum(float(i.get("calories", 0)) for i in meal_data.get("items", []))
            meal_slots[key] = {
                "window":          window,
                "planned_foods":   foods,
                "target_calories": target_cal,
                "eaten_calories":  0.0,
                "protein":         0.0,
                "fat":             0.0,
                "carbs":           0.0,
            }

        unmatched        = []
        late_meal_alerts = []
        total_all_eaten  = 0.0

        for food in self.eaten_foods:
            try:
                if not food.get("consumed", False):
                    continue
                created_at = food.get("created_at")
                if not created_at:
                    continue

                food_date = self._parse_date(created_at)
                if food_date.date() != today:
                    continue

                name  = self._normalize(food.get("food_name", ""))
                hour  = food_date.hour
                cal   = float(food.get("calories",  0))
                prot  = float(food.get("protein_g", 0))
                fat   = float(food.get("fat_g",     0))
                carbs = float(food.get("carbs_g",   0))
                total_all_eaten += cal

                matched = False

                for slot_name, slot in meal_slots.items():
                    w_start, w_end = slot["window"]
                    in_time  = w_start <= hour < w_end
                    name_hit = any(name in pf or pf in name for pf in slot["planned_foods"])
                    if in_time and name_hit:
                        slot["eaten_calories"] += cal
                        slot["protein"]        += prot
                        slot["fat"]            += fat
                        slot["carbs"]          += carbs
                        matched = True
                        break

                if not matched:
                    late = False
                    for slot_name, slot in meal_slots.items():
                        name_hit = any(name in pf or pf in name for pf in slot["planned_foods"])
                        if name_hit:
                            # Sirf tab alert do jab meal window abhi guzri nahi
                            meal_end_hour = slot["window"][1]
                            if hour < meal_end_hour:
                                msg = f"'{name}' {slot_name} time pe nahi khaya"
                                print(f"[LATE MEAL - DAILY] {msg}")
                                late_meal_alerts.append(msg)
                            late = True
                            break
                    if not late:
                        unmatched.append(name)
            except Exception:
                continue

        meals_summary = {}
        for slot_name, slot in meal_slots.items():
            slot_target_cal = slot["target_calories"]
            slot_eaten_cal  = slot["eaten_calories"]

            if slot_target_cal == 0:
                status = "on track"
            elif slot_eaten_cal < slot_target_cal * 0.9:
                status = "under"
            elif slot_eaten_cal > slot_target_cal * 1.1:
                status = "over"
            else:
                status = "on track"

            meals_summary[slot_name] = {
                "eaten_calories":  round(slot_eaten_cal, 2),
                "target_calories": round(slot_target_cal, 2),
                "protein_g":  round(slot["protein"], 2),
                "fat_g":      round(slot["fat"],     2),
                "carbs_g":    round(slot["carbs"],   2),
                "percentage": round(min((slot_eaten_cal / slot_target_cal) * 100, 100) if slot_target_cal > 0 else 0, 2),
                "status":     status,
            }

        daily_target  = day_plan.get("target_calories", 0)
        macros_t      = day_plan.get("macros_target", {})
        total_eaten   = sum(s["eaten_calories"] for s in meal_slots.values())
        progress_pct  = min((total_eaten / daily_target) * 100, 100) if daily_target > 0 else 0

        total_protein = sum(s["protein"] for s in meal_slots.values())
        total_fat     = sum(s["fat"]     for s in meal_slots.values())
        total_carbs   = sum(s["carbs"]   for s in meal_slots.values())

        macro_pcts = self._macro_percentages(
            {"protein": total_protein, "fat": total_fat, "carbs": total_carbs},
            {
                "protein": float(macros_t.get("protein_g", 0)),
                "fat":     float(macros_t.get("fat_g",     0)),
                "carbs":   float(macros_t.get("carbs_g",   0)),
            }
        )

        return clean_numpy({
            "unmatchedFoods":     list(set(unmatched)),
            "hasUnmatchedFoods":  len(unmatched) > 0,
            "lateMealAlerts":     late_meal_alerts,
            "hasLateMeals":       len(late_meal_alerts) > 0,
            "dailyMeals":         meals_summary,
            "totalAllEaten": round(total_all_eaten, 2),

            "workoutHours": self._workout_hours(lambda dt: dt.date() == today),
            "totalEaten":         round(total_eaten, 2),
            "dailyTarget":        round(daily_target, 2),
            "progressPercentage": round(progress_pct, 2),
            **macro_pcts,
            "today": DAYS[today_index],
        })

    # --------------------------------------------------
    # WEEKLY PROGRESS
    # --------------------------------------------------

    def weekly_progress(self):
        plan_by_day = self._build_meal_plan_by_day()
        week_start = self.today - timedelta(days=self.today.weekday())
        week_start = week_start.date()
        week_end = (week_start + timedelta(days=6))
        today      = self.today
        week_start = today - timedelta(days=today.weekday())
        week_end   = week_start + timedelta(days=6)

        weekly_calories  = [0.0] * 7
        weekly_all_eaten = [0.0] * 7
        weekly_protein   = [0.0] * 7
        weekly_fat       = [0.0] * 7
        weekly_carbs     = [0.0] * 7
        weekly_target    = [plan_by_day[i]["target_calories"]                          if i in plan_by_day else 0.0 for i in range(7)]
        weekly_protein_t = [float(plan_by_day[i]["macros_target"].get("protein_g", 0)) if i in plan_by_day else 0.0 for i in range(7)]
        weekly_fat_t     = [float(plan_by_day[i]["macros_target"].get("fat_g",     0)) if i in plan_by_day else 0.0 for i in range(7)]
        weekly_carbs_t   = [float(plan_by_day[i]["macros_target"].get("carbs_g",   0)) if i in plan_by_day else 0.0 for i in range(7)]

        unmatched        = []
        late_meal_alerts = []

        for food in self.eaten_foods:
            try:
                if not food.get("consumed", False):
                    continue
                created_at = food.get("created_at")
                if not created_at:
                    continue

                food_date = self._parse_date(created_at)
                if not (week_start.date() <= food_date.date() <= week_end.date()):
                    continue

                day_index = food_date.weekday()
                name  = self._normalize(food.get("food_name", ""))
                hour  = food_date.hour
                cal   = float(food.get("calories",  0))
                prot  = float(food.get("protein_g", 0))
                fat   = float(food.get("fat_g",     0))
                carbs = float(food.get("carbs_g",   0))

                weekly_all_eaten[day_index] += cal

                matched, late, expected_meal = self._is_matched_with_time(name, hour, day_index, plan_by_day)

                if matched:
                    weekly_calories[day_index] += cal
                    weekly_protein[day_index]  += prot
                    weekly_fat[day_index]      += fat
                    weekly_carbs[day_index]    += carbs
                elif late:
                    if food_date.date() == today.date():
                        meal_end_hour = MEAL_WINDOWS.get(expected_meal, (0, 23))[1]
                        if self.today.hour < meal_end_hour:
                            msg = f"'{name}' {expected_meal} time pe nahi khaya"
                            print(f"[LATE MEAL - WEEKLY] {msg}")
                            late_meal_alerts.append(msg)
                else:
                    unmatched.append(name)

            except Exception:
                continue

        progress_status = []
        for i in range(7):
            if weekly_target[i] == 0:
                progress_status.append("on track")
            elif weekly_calories[i] < weekly_target[i]:
                progress_status.append("under")
            elif weekly_calories[i] > weekly_target[i]:
                progress_status.append("over")
            else:
                progress_status.append("on track")

        weekly_trend = []
        running, count = 0.0, 0
        for v in weekly_all_eaten:
            if v > 0:
                running += v
                count   += 1
            weekly_trend.append(running / count if count > 0 else 0)

        total_eaten  = sum(weekly_calories)
        total_target = sum(weekly_target)
        total_all_eaten = sum(weekly_all_eaten)
        progress_pct = min((total_eaten / total_target) * 100, 100) if total_target > 0 else 0

        macro_pcts = self._macro_percentages(
            {"protein": sum(weekly_protein), "fat": sum(weekly_fat), "carbs": sum(weekly_carbs)},
            {"protein": sum(weekly_protein_t), "fat": sum(weekly_fat_t), "carbs": sum(weekly_carbs_t)},
        )

        weekly_data = {}
        for i, day_name in enumerate(DAYS):
            weekly_data[day_name] = {
                "calories": round(weekly_calories[i],  2),
                "allEaten": round(weekly_all_eaten[i], 2),
                "target":   round(weekly_target[i],    2),
                "trend":    round(weekly_trend[i],     2),
                "status":   progress_status[i],
            }

        return clean_numpy({
            "workoutHours": self._workout_hours(lambda dt: week_start.date() <= dt.date() <= week_end.date()),
            "totalAllEaten": round(total_all_eaten, 2),
            "unmatchedFoods":     list(set(unmatched)),
            "hasUnmatchedFoods":  len(unmatched) > 0,
            "lateMealAlerts":     late_meal_alerts,
            "hasLateMeals":       len(late_meal_alerts) > 0,
            "weeklyData":         weekly_data,
            "progressStatus":     progress_status,
            "progressPercentage": round(progress_pct, 2),
            **macro_pcts,
        })

    # --------------------------------------------------
    # MONTHLY PROGRESS
    # --------------------------------------------------

    def monthly_progress(self):
        plan_by_day    = self._build_meal_plan_by_day()
        today          = self.today
        weeks_in_month = 4

        monthly_calories  = [0.0] * weeks_in_month
        monthly_all_eaten = [0.0] * weeks_in_month
        monthly_protein   = [0.0] * weeks_in_month
        monthly_fat       = [0.0] * weeks_in_month
        monthly_carbs     = [0.0] * weeks_in_month

        weekly_target_sum  = sum(plan_by_day[i]["target_calories"]                          for i in range(7) if i in plan_by_day)
        weekly_protein_sum = sum(float(plan_by_day[i]["macros_target"].get("protein_g", 0)) for i in range(7) if i in plan_by_day)
        weekly_fat_sum     = sum(float(plan_by_day[i]["macros_target"].get("fat_g",     0)) for i in range(7) if i in plan_by_day)
        weekly_carbs_sum   = sum(float(plan_by_day[i]["macros_target"].get("carbs_g",   0)) for i in range(7) if i in plan_by_day)

        monthly_target    = [weekly_target_sum]  * weeks_in_month
        monthly_protein_t = [weekly_protein_sum] * weeks_in_month
        monthly_fat_t     = [weekly_fat_sum]     * weeks_in_month
        monthly_carbs_t   = [weekly_carbs_sum]   * weeks_in_month

        unmatched        = []
        late_meal_alerts = []

        for food in self.eaten_foods:
            try:
                if not food.get("consumed", False):
                    continue
                created_at = food.get("created_at")
                if not created_at:
                    continue

                food_date = self._parse_date(created_at)
                if food_date.year != today.year or food_date.month != today.month:
                    continue

                week_index = min((food_date.day - 1) // 7, 3)
                day_index  = food_date.weekday()
                name  = self._normalize(food.get("food_name", ""))
                hour  = food_date.hour
                cal   = float(food.get("calories",  0))
                prot  = float(food.get("protein_g", 0))
                fat   = float(food.get("fat_g",     0))
                carbs = float(food.get("carbs_g",   0))

                monthly_all_eaten[week_index] += cal

                matched, late, expected_meal = self._is_matched_with_time(name, hour, day_index, plan_by_day)

                if matched:
                    monthly_calories[week_index] += cal
                    monthly_protein[week_index]  += prot
                    monthly_fat[week_index]      += fat
                    monthly_carbs[week_index]    += carbs
                elif late:
                    if food_date.date() == today.date():
                        meal_end_hour = MEAL_WINDOWS.get(expected_meal, (0, 23))[1]
                        if self.today.hour < meal_end_hour:
                            msg = f"'{name}' {expected_meal} time pe nahi khaya"
                            print(f"[LATE MEAL - MONTHLY] {msg}")
                            late_meal_alerts.append(msg)
                else:
                    unmatched.append(name)

            except Exception:
                continue

        monthly_trend = []
        running, count = 0.0, 0
        for v in monthly_calories:
            if v > 0:
                running += v
                count   += 1
            monthly_trend.append(running / count if count > 0 else 0)

        total_cal    = sum(monthly_calories)
        total_target = sum(monthly_target)
        total_all_eaten = sum(monthly_all_eaten)
        progress_pct = min((total_cal / total_target) * 100, 100) if total_target > 0 else 0

        macro_pcts = self._macro_percentages(
            {"protein": sum(monthly_protein), "fat": sum(monthly_fat), "carbs": sum(monthly_carbs)},
            {"protein": sum(monthly_protein_t), "fat": sum(monthly_fat_t), "carbs": sum(monthly_carbs_t)},
        )

        monthly_days = {}
        for i in range(weeks_in_month):
            eaten_cal  = monthly_calories[i]
            target_cal = monthly_target[i]
            monthly_days[f"Week {i + 1}"] = {
                "calories":   round(eaten_cal, 2),
                "allEaten":   round(monthly_all_eaten[i], 2),
                "target":     round(target_cal, 2),
                "trend":      round(monthly_trend[i], 2),
                "percentage": round(min((eaten_cal / target_cal) * 100, 100) if target_cal > 0 else 0, 2),
            }

        return clean_numpy({
            "workoutHours": self._workout_hours(
                lambda dt: dt.month == self.today.month
            ),
            "unmatchedFoods":     list(set(unmatched)),
            "totalAllEaten": round(total_all_eaten, 2),
            "hasUnmatchedFoods":  len(unmatched) > 0,
            "lateMealAlerts":     late_meal_alerts,
            "hasLateMeals":       len(late_meal_alerts) > 0,
            "monthlyData":        monthly_days,
            "progressPercentage": round(progress_pct, 2),
            **macro_pcts,
        })

    # --------------------------------------------------
    # MAIN ENTRY
    # --------------------------------------------------

    def track_progress(self):
        if self.period == "daily":
            result = self.daily_progress()
        elif self.period == "monthly":
            result = self.monthly_progress()
        else:
            result = self.weekly_progress()

        result["ongoingWeek"] = (self.today - self.profile_start_date).days // 7 + 1
        result["adaptivePlan"] = self.check_adaptive_plan()
        return clean_numpy(result)