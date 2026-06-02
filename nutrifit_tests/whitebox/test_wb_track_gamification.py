import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fixtures"))
from mock_backend import (
    log_progress, get_progress, clear_progress, calculate_weekly_summary,
    award_points, get_leaderboard, get_user_points, reset_points, POINT_RULES,
)


class TestTrackProgress:

    def setup_method(self):
        clear_progress("user_wb_01")
        clear_progress("user_wb_02")

    # ── log_progress ──────────────────────────────────────────────────────

    def test_log_returns_status_logged(self):
        """[WB-TP-01] log_progress returns status='logged'."""
        result = log_progress("user_wb_01", "2025-01-01", 70.0, 2000, True)
        assert result["status"] == "logged", (
            "WB-TP-01 FAIL: Expected status='logged'."
        )

    def test_log_entry_contains_all_keys(self):
        """[WB-TP-02] Logged entry must carry date, weight, calories, workout_done."""
        result = log_progress("user_wb_01", "2025-01-01", 72.0, 1800, False)
        entry = result["entry"]
        for key in ("date", "weight_kg", "calories_consumed", "workout_done"):
            assert key in entry, f"WB-TP-02 FAIL: Missing key '{key}' in entry."

    def test_log_persists_to_store(self):
        """[WB-TP-03] After logging, get_progress returns the same entry."""
        log_progress("user_wb_01", "2025-01-02", 71.5, 1950, True)
        entries = get_progress("user_wb_01")
        assert len(entries) == 1
        assert entries[0]["weight_kg"] == 71.5, (
            "WB-TP-03 FAIL: Retrieved entry weight does not match logged value."
        )

    def test_multiple_logs_accumulate(self):
        """[WB-TP-04] Loop: 5 entries logged → 5 entries in store."""
        for i in range(5):
            log_progress("user_wb_01", f"2025-01-0{i+1}", 70 - i*0.2, 2000, True)
        entries = get_progress("user_wb_01")
        assert len(entries) == 5, (
            f"WB-TP-04 FAIL: Expected 5 entries, got {len(entries)}."
        )

    def test_unknown_user_returns_empty_list(self):
        """[WB-TP-05] get_progress for unknown user returns [], not KeyError."""
        result = get_progress("nonexistent_user_xyz")
        assert result == [], "WB-TP-05 FAIL: Unknown user should return []."

    def test_clear_progress_removes_entries(self):
        """[WB-TP-06] clear_progress wipes all entries for a user."""
        log_progress("user_wb_01", "2025-01-01", 70, 2000, True)
        clear_progress("user_wb_01")
        assert get_progress("user_wb_01") == [], (
            "WB-TP-06 FAIL: Entries still present after clear_progress."
        )

    # ── calculate_weekly_summary ──────────────────────────────────────────

    def test_summary_error_on_no_data(self):
        """[WB-TP-07] Summary with no entries → error dict."""
        result = calculate_weekly_summary("user_wb_01")
        assert "error" in result, (
            "WB-TP-07 FAIL: Empty progress should return error dict."
        )

    def test_summary_avg_weight_correct(self):
        """[WB-TP-08] avg_weight_kg = arithmetic mean of logged weights."""
        weights = [70.0, 69.5, 69.0, 68.8, 68.5]
        for i, w in enumerate(weights):
            log_progress("user_wb_01", f"2025-01-0{i+1}", w, 2000, True)
        summary = calculate_weekly_summary("user_wb_01")
        expected_avg = round(sum(weights) / len(weights), 2)
        assert summary["avg_weight_kg"] == expected_avg, (
            f"WB-TP-08 FAIL: avg_weight_kg {summary['avg_weight_kg']} != {expected_avg}."
        )

    def test_summary_weight_change_direction(self):
        """[WB-TP-09] Negative weight_change_kg when weight decreases over time."""
        log_progress("user_wb_01", "2025-01-01", 75.0, 2000, True)
        log_progress("user_wb_01", "2025-01-07", 72.0, 1900, True)
        summary = calculate_weekly_summary("user_wb_01")
        assert summary["weight_change_kg"] < 0, (
            "WB-TP-09 FAIL: Decreasing weight should give negative weight_change_kg."
        )

    def test_summary_adherence_all_workouts(self):
        """[WB-TP-10] 7/7 workouts done → adherence_pct = 100.0."""
        for i in range(7):
            log_progress("user_wb_01", f"2025-01-0{i+1}", 70, 2000, True)
        summary = calculate_weekly_summary("user_wb_01")
        assert summary["adherence_pct"] == 100.0, (
            f"WB-TP-10 FAIL: Expected 100% adherence, got {summary['adherence_pct']}."
        )

    def test_summary_adherence_no_workouts(self):
        """[WB-TP-11] 0/3 workouts done → adherence_pct = 0.0."""
        for i in range(3):
            log_progress("user_wb_01", f"2025-01-0{i+1}", 70, 2000, False)
        summary = calculate_weekly_summary("user_wb_01")
        assert summary["adherence_pct"] == 0.0, (
            f"WB-TP-11 FAIL: Expected 0% adherence, got {summary['adherence_pct']}."
        )

    def test_summary_partial_adherence(self):
        """[WB-TP-12] 3/4 workouts → adherence_pct = 75.0."""
        for i, done in enumerate([True, True, True, False]):
            log_progress("user_wb_01", f"2025-01-0{i+1}", 70, 2000, done)
        summary = calculate_weekly_summary("user_wb_01")
        assert summary["adherence_pct"] == 75.0, (
            f"WB-TP-12 FAIL: Expected 75% adherence, got {summary['adherence_pct']}."
        )

    def test_two_users_isolated(self):
        """[WB-TP-13] Progress data is isolated per user_id — no cross-contamination."""
        log_progress("user_wb_01", "2025-01-01", 80, 2500, True)
        log_progress("user_wb_02", "2025-01-01", 60, 1500, False)
        assert get_progress("user_wb_01")[0]["weight_kg"] == 80
        assert get_progress("user_wb_02")[0]["weight_kg"] == 60


# TestGamification

class TestGamification:

    def setup_method(self):
        reset_points("player_01")
        reset_points("player_02")
        reset_points("player_03")

    # ── award_points ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("event,expected_pts", list(POINT_RULES.items()))
    def test_correct_points_per_event(self, event, expected_pts):
        """[WB-GM-01] Each event awards the correct points per POINT_RULES."""
        result = award_points("player_01", event)
        assert result["points_awarded"] == expected_pts, (
            f"WB-GM-01 FAIL: Event '{event}' awarded {result['points_awarded']}, "
            f"expected {expected_pts}."
        )

    def test_unknown_event_awards_zero(self):
        """[WB-GM-02] Unrecognised event awards 0 points."""
        result = award_points("player_01", "fly_to_moon")
        assert result["points_awarded"] == 0, (
            "WB-GM-02 FAIL: Unknown event should award 0 points."
        )

    def test_points_accumulate_over_events(self):
        """[WB-GM-03] Loop: multiple events accumulate in total_points."""
        award_points("player_01", "workout_done")       # 50
        award_points("player_01", "calories_on_target") # 30
        award_points("player_01", "weight_logged")      # 10
        total = get_user_points("player_01")
        assert total == 90, (
            f"WB-GM-03 FAIL: Expected 90 total points, got {total}."
        )

    def test_total_points_in_response(self):
        """[WB-GM-04] award_points response carries correct running total."""
        award_points("player_01", "workout_done")       # 50
        result = award_points("player_01", "workout_done")  # 100
        assert result["total_points"] == 100, (
            f"WB-GM-04 FAIL: total_points in response should be 100, got {result['total_points']}."
        )

    def test_fresh_user_has_zero_points(self):
        """[WB-GM-05] New user starts with 0 points."""
        assert get_user_points("brand_new_user_xyz") == 0, (
            "WB-GM-05 FAIL: New user should have 0 points."
        )

    def test_reset_clears_points(self):
        """[WB-GM-06] reset_points → user drops back to 0."""
        award_points("player_01", "streak_7_days")
        reset_points("player_01")
        assert get_user_points("player_01") == 0, (
            "WB-GM-06 FAIL: Points not cleared after reset."
        )

    # ── leaderboard ───────────────────────────────────────────────────────

    def test_leaderboard_sorted_descending(self):
        """[WB-GM-07] Leaderboard ranks highest points first."""
        award_points("player_01", "workout_done")        # 50
        award_points("player_02", "streak_7_days")       # 100
        award_points("player_03", "calories_on_target")  # 30
        board = get_leaderboard()
        scores = [entry["points"] for entry in board
                  if entry["user_id"] in {"player_01","player_02","player_03"}]
        assert scores == sorted(scores, reverse=True), (
            "WB-GM-07 FAIL: Leaderboard is not sorted descending."
        )

    def test_leaderboard_rank_1_is_highest(self):
        """[WB-GM-08] Rank 1 entry has highest points of all players."""
        award_points("player_01", "streak_7_days")  # 100 → should be rank 1
        award_points("player_02", "workout_done")   # 50
        board = get_leaderboard()
        # Filter to our two test players
        relevant = [e for e in board if e["user_id"] in {"player_01","player_02"}]
        top = min(relevant, key=lambda e: e["rank"])
        assert top["user_id"] == "player_01", (
            f"WB-GM-08 FAIL: Rank 1 should be player_01, got {top['user_id']}."
        )

    def test_leaderboard_contains_rank_field(self):
        """[WB-GM-09] Every leaderboard entry has 'rank', 'user_id', 'points'."""
        award_points("player_01", "workout_done")
        board = get_leaderboard()
        for entry in board:
            for key in ("rank", "user_id", "points"):
                assert key in entry, f"WB-GM-09 FAIL: Missing '{key}' in leaderboard entry."

    def test_streak_bonus_is_largest_reward(self):
        """[WB-GM-10] streak_7_days awards more points than any single daily event."""
        streak_pts = POINT_RULES["streak_7_days"]
        daily_max  = max(v for k, v in POINT_RULES.items() if k != "streak_7_days")
        assert streak_pts > daily_max, (
            "WB-GM-10 FAIL: Streak bonus should exceed all single-day rewards."
        )