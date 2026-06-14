from datetime import datetime, UTC, timedelta


# ================= LEVEL LOGIC =================

def calculate_level(xp: int):
    level = 1
    xp_required = 500
    total_xp = xp

    while total_xp >= xp_required:
        total_xp -= xp_required
        level += 1
        xp_required += 500

    return level


def calculate_level_data(xp: int):
    level = 1
    xp_required = 500
    remaining_xp = xp

    while remaining_xp >= xp_required:
        remaining_xp -= xp_required
        level += 1
        xp_required += 500

    progress = remaining_xp / xp_required

    return level, round(progress, 2)
# ================= ACHIEVEMENTS LOGIC =================
# ================= LEVEL TIERS =================

def get_level_badge(level: int):
    if 1 <= level <= 3:
        return "bronze"
    elif 4 <= level <= 9:
        return "silver"
    elif 10 <= level <= 15:
        return "gold"
    else:
        return None
def update_streak(current_streak: int, last_active_date: str):

    today = datetime.now(UTC).date()

    if last_active_date:
        last_date = datetime.fromisoformat(last_active_date).date()
    else:
        return 1, today.isoformat()

    if last_date == today:
        return current_streak, last_date.isoformat()

    if last_date == today - timedelta(days=1):
        return current_streak + 1, today.isoformat()

    return 1, today.isoformat()
def unlock_achievements(level: int, streak: int, eaten_foods: int, unlocked: list):

    new_unlocks = []
    # Level tier badge
    tier_badge = get_level_badge(level)

    if tier_badge and tier_badge not in unlocked:
        new_unlocks.append(tier_badge)

    # Streak Milestones
    streak_milestones = [7, 14, 30]
    for milestone in streak_milestones:
        badge_id = f"streak_{milestone}"
        if streak >= milestone and badge_id not in unlocked:
            new_unlocks.append(badge_id)

    # Food Logging Milestones
    food_milestones = [10, 25, 50]
    for milestone in food_milestones:
        badge_id = f"food_{milestone}"
        if eaten_foods >= milestone and badge_id not in unlocked:
            new_unlocks.append(badge_id)

    return new_unlocks
# ================= MAIN ROUTE =================

def gamification_sync_route(data: dict):
    try:
        xp = int(data.get("xp", 0))
        streak = int(data.get("streak", 0))
        matched_foods = int(data.get("matched_foods", 0))
        unmatched_foods = int(data.get("unmatched_foods", 0))
        last_synced_matched = int(data.get("last_synced_matched", 0))
        last_synced_unmatched = int(data.get("last_synced_unmatched", 0))

        exercise_minutes = float(data.get("exercise_minutes", 0))
        last_synced_exercise_minutes = float(data.get("last_synced_exercise_minutes", 0))

        achievements = data.get("achievements", [])
        last_active_date = data.get("last_active_date")

            # Streak update
        streak, updated_last_date = update_streak(streak, last_active_date)

        XP_PER_MATCHED = 15
        XP_PENALTY_PER_UNMATCHED = 5
        XP_PER_EXERCISE_MINUTE = 10

        new_matched = max(matched_foods - last_synced_matched, 0)
        new_unmatched = max(unmatched_foods - last_synced_unmatched, 0)
        new_exercise_minutes = max(exercise_minutes - last_synced_exercise_minutes, 0)

        bonus_xp = new_matched * XP_PER_MATCHED
        penalty_xp = new_unmatched * XP_PENALTY_PER_UNMATCHED
        exercise_xp = int(new_exercise_minutes * XP_PER_EXERCISE_MINUTE)

        total_xp = max(xp + bonus_xp - penalty_xp + exercise_xp, 0)
        print('XP', total_xp)
        server_level, level_progress = calculate_level_data(total_xp)

        # 🏆 Unlock achievements
        eaten_foods_total = matched_foods + unmatched_foods
        new_achievements = unlock_achievements(server_level, streak, eaten_foods_total, achievements)
        all_achievements = achievements.copy()

        for badge in new_achievements:
            if badge not in all_achievements:
                all_achievements.append(badge)

        current_badge = get_level_badge(server_level)
        print('Badge', current_badge)

        return {
            "status": "success",
            "server_level": server_level,
            "level_progress": level_progress,
            "server_xp": total_xp,
            "streak": streak,
            "last_active_date": updated_last_date,
            "new_achievements": new_achievements,
            "all_achievements": all_achievements,
            "timestamp": datetime.now(UTC).isoformat(),
            "current_badge": current_badge,
            "last_synced_matched": matched_foods,
            "last_synced_unmatched": unmatched_foods,
            "last_synced_exercise_minutes": exercise_minutes,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}