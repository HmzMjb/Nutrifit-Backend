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
        eaten_foods = int(data.get("eaten_foods", 0))
        achievements = data.get("achievements", [])

        last_active_date = data.get("last_active_date")
        streak, updated_last_date = update_streak(streak, last_active_date)

        bonus_xp = eaten_foods * 15
        total_xp = xp + bonus_xp
        print('XP',total_xp)

        server_level, level_progress = calculate_level_data(total_xp)

        # 🏆 Unlock achievements
        new_achievements = unlock_achievements(server_level, streak, eaten_foods, achievements)
        all_achievements = achievements.copy()

        for badge in new_achievements:
            if badge not in all_achievements:
                all_achievements.append(badge)
        current_badge = get_level_badge(server_level)
        print('Badge',current_badge)

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

        }

    except Exception as e:
        return {"status": "error", "message": str(e)}