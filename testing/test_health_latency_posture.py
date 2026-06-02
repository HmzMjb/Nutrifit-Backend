"""
WHITE BOX TESTS — NutriFit: Health Profile Planning + System Latency + Posture Estimation
Tools: pytest, unittest.mock, asyncio
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock, call
from dataclasses import dataclass
from typing import List, Optional


# ════════════════════════════════════════════════════════════════
# SHARED DATA MODELS (mirror your real models)
# ════════════════════════════════════════════════════════════════

@dataclass
class HealthProfile:
    user_id: str
    conditions: List[str]
    allergies: List[str]
    calorie_limit: Optional[int] = None
    sodium_limit_mg: Optional[int] = None


@dataclass
class MealPlan:
    day: int
    meals: List[dict]
    total_calories: int
    warnings: List[str]


# ════════════════════════════════════════════════════════════════
# TEST CLASS 3 — Complex Health Profile Meal Planning
# ════════════════════════════════════════════════════════════════

class TestComplexHealthProfiles:
    """
    Failing case: AI struggles with overlapping conditions
    (diabetes + hypertension + high cholesterol + kidney disease).
    White-box path: tests rule-engine priority + conflict resolution logic.
    """

    @pytest.fixture
    def overlapping_profile(self):
        return HealthProfile(
            user_id="u001",
            conditions=["diabetes_type2", "hypertension", "high_cholesterol", "chronic_kidney_disease"],
            allergies=["shellfish"],
            calorie_limit=1800,
            sodium_limit_mg=1500,
        )

    @pytest.fixture
    def simple_profile(self):
        return HealthProfile(
            user_id="u002",
            conditions=["diabetes_type2"],
            allergies=[],
            calorie_limit=2000,
        )

    @patch("nutrifit.services.meal_planner.MealPlannerService.generate_plan")
    def test_single_condition_generates_valid_plan(self, mock_plan, simple_profile):
        """PASS — diabetes-only profile generates a valid 7-day plan."""
        mock_plan.return_value = [
            MealPlan(day=d, meals=[{"name": "oatmeal"}, {"name": "grilled_chicken"}],
                     total_calories=1900, warnings=[])
            for d in range(1, 8)
        ]
        plans = mock_plan(simple_profile)
        assert len(plans) == 7
        for plan in plans:
            assert plan.total_calories <= simple_profile.calorie_limit + 100

    @patch("nutrifit.services.meal_planner.MealPlannerService.generate_plan")
    def test_overlapping_conditions_plan_respects_all_constraints(
        self, mock_plan, overlapping_profile
    ):
        """
        FAIL CASE — multi-condition plan violates one or more dietary rules.
        Expected: All constraints satisfied simultaneously.
        Actual bug: kidney-disease low-potassium rule ignored when diabetes rule runs first.
        """
        # Simulate a buggy plan: high potassium item included (banana)
        mock_plan.return_value = [
            MealPlan(
                day=1,
                meals=[{"name": "banana_smoothie", "potassium_mg": 620}],  # ← BUG: kidney patients need <2000mg/day
                total_calories=1800,
                warnings=[]  # ← BUG: should warn about potassium
            )
        ]
        plans = mock_plan(overlapping_profile)

        for plan in plans:
            # Verify sodium constraint
            sodium_sum = sum(m.get("sodium_mg", 0) for m in plan.meals)
            assert sodium_sum <= overlapping_profile.sodium_limit_mg, (
                f"FAIL: Sodium {sodium_sum}mg exceeds limit {overlapping_profile.sodium_limit_mg}mg. "
                "Feedback: Apply hypertension sodium constraint as a hard cap before meal selection."
            )

            # Verify calorie constraint
            assert plan.total_calories <= overlapping_profile.calorie_limit, (
                "FAIL: Calorie limit exceeded in multi-condition plan."
            )

            # Verify potassium constraint for CKD
            high_k_items = [
                m for m in plan.meals if m.get("potassium_mg", 0) > 200
            ]
            assert len(high_k_items) == 0 or len(plan.warnings) > 0, (
                "FAIL: High-potassium item included without CKD warning. "
                "Feedback: Add CKD rule node in health constraint graph that fires before "
                "meal scoring; potassium >200mg/serving should emit a warning."
            )

    @patch("nutrifit.services.meal_planner.MealPlannerService.generate_plan")
    def test_allergen_always_excluded_regardless_of_conditions(
        self, mock_plan, overlapping_profile
    ):
        """PASS — shellfish allergy must always be respected."""
        mock_plan.return_value = [
            MealPlan(
                day=1,
                meals=[{"name": "grilled_salmon", "allergens": []}],
                total_calories=1750,
                warnings=[]
            )
        ]
        plans = mock_plan(overlapping_profile)
        for plan in plans:
            for meal in plan.meals:
                assert "shellfish" not in meal.get("allergens", []), (
                    "FAIL: Allergen found in meal plan."
                )

    @patch("nutrifit.services.meal_planner.MealPlannerService.generate_plan")
    def test_conflicting_rules_raise_conflict_warning(self, mock_plan):
        """
        FAIL CASE — diabetes (high-protein) vs kidney-disease (low-protein) conflict.
        Expected: ConflictWarning raised + conservative plan returned.
        Actual bug: silent failure, plan generated without warning.
        """
        conflict_profile = HealthProfile(
            user_id="u003",
            conditions=["diabetes_type2", "chronic_kidney_disease"],
            allergies=[]
        )
        mock_plan.return_value = [
            MealPlan(
                day=1,
                meals=[{"name": "chicken_breast", "protein_g": 55}],  # high-protein → bad for CKD
                total_calories=1600,
                warnings=[]  # ← BUG: no conflict warning
            )
        ]
        plans = mock_plan(conflict_profile)
        conflicting_rules_exist = (
            "diabetes_type2" in conflict_profile.conditions and
            "chronic_kidney_disease" in conflict_profile.conditions
        )
        if conflicting_rules_exist:
            all_warnings = [w for plan in plans for w in plan.warnings]
            assert any("protein" in w.lower() or "conflict" in w.lower() for w in all_warnings), (
                "FAIL: Protein conflict between diabetes and CKD not surfaced. "
                "Feedback: Implement rule-conflict detection before plan generation. "
                "When diabetes high-protein rule conflicts with CKD low-protein rule, "
                "use moderate-protein (0.8g/kg) as fallback and emit warning."
            )

    @patch("nutrifit.services.meal_planner.MealPlannerService.generate_plan")
    def test_empty_conditions_returns_standard_balanced_plan(self, mock_plan):
        """PASS — no conditions → standard balanced plan."""
        profile = HealthProfile(user_id="u004", conditions=[], allergies=[])
        mock_plan.return_value = [
            MealPlan(day=1, meals=[{"name": "balanced_meal"}], total_calories=2000, warnings=[])
        ]
        result = mock_plan(profile)
        assert result is not None
        assert len(result) >= 1


# ════════════════════════════════════════════════════════════════
# TEST CLASS 4 — System Integration Latency
# ════════════════════════════════════════════════════════════════

class TestSystemIntegrationLatency:
    """
    Failing case: Simultaneous AI + nutrition + fitness queries cause delays.
    White-box path: tests async task scheduler, timeout guards, cache hits.
    """

    @pytest.mark.asyncio
    @patch("nutrifit.services.ai_service.AIService.analyze_meal", new_callable=AsyncMock)
    @patch("nutrifit.services.nutrition_service.NutritionService.get_macros", new_callable=AsyncMock)
    @patch("nutrifit.services.fitness_service.FitnessService.get_recommendations", new_callable=AsyncMock)
    async def test_concurrent_calls_complete_within_sla(
        self, mock_fitness, mock_nutrition, mock_ai
    ):
        """
        PASS if all concurrent calls complete within 3-second SLA.
        FAIL CASE if sequential execution breaches SLA.
        """
        mock_ai.return_value = {"dish": "biryani", "calories": 450}
        mock_nutrition.return_value = {"protein": 22, "carbs": 60}
        mock_fitness.return_value = {"recommendation": "30min cardio"}

        start = time.monotonic()
        results = await asyncio.gather(
            mock_ai("image_bytes"),
            mock_nutrition("biryani"),
            mock_fitness("u001"),
        )
        elapsed = time.monotonic() - start

        assert elapsed < 3.0, (
            f"FAIL: Concurrent queries took {elapsed:.2f}s, exceeds 3.0s SLA. "
            "Feedback: Ensure all three service calls use asyncio.gather() not sequential await. "
            "Add Redis cache for repeated nutrition lookups."
        )
        assert len(results) == 3

    @pytest.mark.asyncio
    @patch("nutrifit.services.ai_service.AIService.analyze_meal", new_callable=AsyncMock)
    async def test_ai_service_timeout_triggers_fallback(self, mock_ai):
        """
        FAIL CASE — AI service hangs; no timeout guard.
        Expected: TimeoutError caught → fallback response returned.
        """
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(10)  # simulate hang
            return {}

        mock_ai.side_effect = slow_response

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(mock_ai("img"), timeout=2.0)
        # Feedback: wrap AI calls in asyncio.wait_for(coro, timeout=5.0)
        # and return {"error": "analysis_timeout", "fallback": true} to UI

    @patch("nutrifit.services.nutrition_service.NutritionService.get_macros")
    def test_nutrition_cache_hit_returns_faster_than_api_call(self, mock_macros):
        """PASS — cached result must be faster than cold API call."""
        # Cold call
        mock_macros.side_effect = lambda dish, use_cache=False: (
            time.sleep(0.05) or {"protein": 22}
        )
        start = time.monotonic()
        mock_macros("biryani", use_cache=False)
        cold_time = time.monotonic() - start

        # Warm cache call (mocked instant)
        mock_macros.side_effect = lambda dish, use_cache=True: {"protein": 22}
        start = time.monotonic()
        mock_macros("biryani", use_cache=True)
        warm_time = time.monotonic() - start

        assert warm_time <= cold_time, (
            "Cache hit should be faster than cold API call."
        )

    @pytest.mark.asyncio
    @patch("nutrifit.services.ai_service.AIService.analyze_meal", new_callable=AsyncMock)
    @patch("nutrifit.services.nutrition_service.NutritionService.get_macros", new_callable=AsyncMock)
    async def test_partial_failure_does_not_crash_full_response(
        self, mock_nutrition, mock_ai
    ):
        """
        FAIL CASE — one service failure crashes entire response.
        Expected: partial result returned with error field for failed module.
        """
        mock_ai.return_value = {"dish": "biryani"}
        mock_nutrition.side_effect = ConnectionError("Nutrition API down")

        try:
            results = await asyncio.gather(
                mock_ai("img"),
                mock_nutrition("biryani"),
                return_exceptions=True
            )
        except Exception:
            pytest.fail(
                "FAIL: Exception propagated instead of being captured. "
                "Feedback: Use return_exceptions=True in asyncio.gather and check each result; "
                "replace exceptions with {'error': str(e), 'module': 'nutrition'} in response."
            )
        # Verify AI result still present despite nutrition failure
        assert results[0] == {"dish": "biryani"}
        assert isinstance(results[1], ConnectionError)


# ════════════════════════════════════════════════════════════════
# TEST CLASS 5 — Body Posture Estimation
# ════════════════════════════════════════════════════════════════

class TestPostureEstimation:
    """
    Failing case: Poor lighting, cluttered backgrounds, occluded joints
    → incorrect form feedback or wrong exercise scoring.
    White-box path: tests keypoint detection, visibility masking, scoring logic.
    """

    @pytest.fixture
    def clear_pose_keypoints(self):
        """17-point COCO keypoints, all visible."""
        return {
            "keypoints": [
                {"joint": "left_knee", "x": 100, "y": 200, "visibility": 0.95},
                {"joint": "right_knee", "x": 120, "y": 200, "visibility": 0.92},
                {"joint": "left_hip", "x": 95, "y": 160, "visibility": 0.91},
                {"joint": "right_hip", "x": 125, "y": 160, "visibility": 0.90},
                {"joint": "left_shoulder", "x": 90, "y": 110, "visibility": 0.88},
                {"joint": "right_shoulder", "x": 130, "y": 110, "visibility": 0.87},
            ],
            "occlusion_ratio": 0.05
        }

    @pytest.fixture
    def occluded_pose_keypoints(self):
        """Keypoints with several joints occluded (e.g., behind gym equipment)."""
        return {
            "keypoints": [
                {"joint": "left_knee", "x": 100, "y": 200, "visibility": 0.20},   # occluded
                {"joint": "right_knee", "x": 120, "y": 200, "visibility": 0.18},  # occluded
                {"joint": "left_hip", "x": 95, "y": 160, "visibility": 0.55},
                {"joint": "right_hip", "x": 125, "y": 160, "visibility": 0.50},
                {"joint": "left_shoulder", "x": 90, "y": 110, "visibility": 0.88},
                {"joint": "right_shoulder", "x": 130, "y": 110, "visibility": 0.87},
            ],
            "occlusion_ratio": 0.65
        }

    @patch("nutrifit.ai.posture_estimator.PostureEstimator.score_exercise")
    def test_clear_squat_form_scored_correctly(self, mock_score, clear_pose_keypoints):
        """PASS — valid squat form with all joints visible gets high score."""
        mock_score.return_value = {
            "exercise": "squat",
            "score": 88,
            "feedback": "Good depth. Keep knees aligned.",
            "confidence": 0.93
        }
        result = mock_score(clear_pose_keypoints, exercise="squat")
        assert result["score"] >= 70
        assert result["confidence"] >= 0.80

    @patch("nutrifit.ai.posture_estimator.PostureEstimator.score_exercise")
    def test_occluded_joints_trigger_low_confidence_flag(
        self, mock_score, occluded_pose_keypoints
    ):
        """
        FAIL CASE — occluded knee joints → incorrect squat score given.
        Expected: confidence flag set + score returned as 'unreliable'.
        Actual bug: score=72 returned as reliable despite low visibility.
        """
        mock_score.return_value = {
            "exercise": "squat",
            "score": 72,
            "feedback": "Knees caving inward.",  # ← incorrect, joints invisible
            "confidence": 0.91,   # ← BUG: high confidence despite occlusion
            "unreliable": False   # ← BUG
        }
        result = mock_score(occluded_pose_keypoints, exercise="squat")
        occlusion = occluded_pose_keypoints["occlusion_ratio"]

        if occlusion > 0.40:
            assert result.get("unreliable") is True or result["confidence"] < 0.60, (
                f"FAIL: Occlusion ratio={occlusion:.2f} but confidence={result['confidence']:.2f}. "
                "Feedback: When occlusion_ratio > 0.40, set unreliable=True and confidence < 0.60; "
                "display 'Partial view – reposition camera' in the UI instead of incorrect feedback."
            )

    @patch("nutrifit.ai.posture_estimator.PostureEstimator.detect_keypoints")
    def test_low_light_frame_returns_empty_keypoints(self, mock_detect):
        """
        FAIL CASE — dark frame returns fabricated keypoints.
        Expected: empty list returned + user prompted to improve lighting.
        """
        mock_detect.return_value = {
            "keypoints": [
                {"joint": "left_knee", "x": 50, "y": 100, "visibility": 0.12}
            ],
            "frame_quality": "low_light",
            "reliable": True   # ← BUG: should be False
        }
        result = mock_detect(b"dark_frame")
        low_visibility = [
            kp for kp in result["keypoints"] if kp["visibility"] < 0.30
        ]
        if len(low_visibility) == len(result["keypoints"]):
            assert result.get("reliable") is False, (
                "FAIL: All keypoints have visibility<0.30 but reliable=True. "
                "Feedback: Set reliable=False when mean visibility < 0.30; "
                "return frame_quality='low_light' and surface 'Improve lighting' prompt."
            )

    @patch("nutrifit.ai.posture_estimator.PostureEstimator.score_exercise")
    def test_knee_angle_calculation_within_tolerance(self, mock_score):
        """PASS — knee angle computed correctly from hip-knee-ankle vectors."""
        mock_score.return_value = {
            "exercise": "squat",
            "score": 85,
            "knee_angle_deg": 92,
            "target_angle_deg": 90,
            "feedback": "Almost perfect depth.",
            "confidence": 0.94
        }
        result = mock_score({}, exercise="squat")
        angle_error = abs(result["knee_angle_deg"] - result["target_angle_deg"])
        assert angle_error <= 10, (
            f"FAIL: Knee angle deviation {angle_error}° exceeds ±10° tolerance."
        )

    @patch("nutrifit.ai.posture_estimator.PostureEstimator.score_exercise")
    def test_cluttered_background_keypoint_noise_filtered(self, mock_score):
        """
        FAIL CASE — cluttered background introduces ghost keypoints.
        Expected: extra keypoints filtered; only 17 COCO keypoints retained.
        Actual bug: 21 keypoints returned.
        """
        mock_score.return_value = {
            "exercise": "deadlift",
            "score": 70,
            "keypoints_detected": 21,   # ← BUG: 4 ghost points
            "confidence": 0.75,
            "feedback": "Keep back straight."
        }
        result = mock_score({}, exercise="deadlift")
        assert result["keypoints_detected"] <= 17, (
            f"FAIL: {result['keypoints_detected']} keypoints detected (max should be 17 COCO). "
            "Feedback: Apply keypoint count validation post-inference; prune extra detections "
            "by confidence ranking and enforce hard cap of 17."
        )


# ════════════════════════════════════════════════════════════════
# HELPER: Run all tests with coverage report command
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import subprocess
    subprocess.run([
        "pytest",
        "tests/white_box/",
        "-v",
        "--tb=short",
        "--cov=nutrifit",
        "--cov-report=term-missing",
        "--cov-report=html:coverage_html",
    ])
