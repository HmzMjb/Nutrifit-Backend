"""
BLACK BOX TESTS — NutriFit Mobile App
Tool: Appium (Python client) + pytest
Platform: Android (mirrors iOS with minimal changes)
Tests interface-level behaviour as a real user would see it.
"""

import pytest
import time
from appium import webdriver
from appium.options import AndroidOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# ════════════════════════════════════════════════════════════════
# APPIUM CAPABILITIES & DRIVER SETUP
# ════════════════════════════════════════════════════════════════

APPIUM_SERVER = "http://127.0.0.1:4723"

ANDROID_CAPS = {
    "platformName": "Android",
    "platformVersion": "13",
    "deviceName": "Pixel_7_API_33",
    "app": "/path/to/nutrifit.apk",          # ← update to real APK path
    "appPackage": "com.nutrifit.app",
    "appActivity": "com.nutrifit.app.MainActivity",
    "automationName": "UiAutomator2",
    "noReset": False,
    "newCommandTimeout": 60,
    "autoGrantPermissions": True,
}


@pytest.fixture(scope="class")
def driver():
    """Start Appium driver, yield, then quit."""
    options = AndroidOptions().load_capabilities(ANDROID_CAPS)
    d = webdriver.Remote(APPIUM_SERVER, options=options)
    d.implicitly_wait(10)
    yield d
    d.quit()


def wait_for(driver, locator, timeout=15):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(locator)
    )


def wait_for_text(driver, text, timeout=15):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(
            (AppiumBy.ANDROID_UIAUTOMATOR,
             f'new UiSelector().textContains("{text}")')
        )
    )


# ════════════════════════════════════════════════════════════════
# TEST CLASS 1 — Multi-Meal Image Confusion (Black Box)
# ════════════════════════════════════════════════════════════════

class TestMultiMealImageUI:
    """
    Failing case: Multiple dishes in one image — UI shows wrong/incomplete labels.
    Black-box perspective: tester uploads image, reads result screen.
    """

    def test_single_clear_dish_shows_correct_label(self, driver):
        """
        PASS — single biryani image → label 'Biryani' appears within 10s.
        """
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "scan_meal_button").click()
        time.sleep(1)
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "upload_image_button").click()
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("biryani_single.jpg")'
        ).click()

        label = wait_for_text(driver, "Biryani", timeout=15)
        assert label is not None, "FAIL: Biryani label not displayed."

    def test_two_dishes_both_labeled_on_screen(self, driver):
        """
        PASS — image with rice + curry → both labels appear.
        """
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "upload_image_button").click()
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("rice_curry.jpg")'
        ).click()

        rice = wait_for_text(driver, "Rice", timeout=15)
        curry = wait_for_text(driver, "Curry", timeout=15)
        assert rice is not None, "FAIL: Rice label missing for multi-dish image."
        assert curry is not None, "FAIL: Curry label missing for multi-dish image."

    def test_low_light_image_shows_warning_not_wrong_label(self, driver):
        """
        FAIL CASE — dark image returns 'Unknown Dish' label without any user guidance.
        Expected: 'Poor lighting detected – retake photo' toast/banner shown.
        Actual: wrong label shown or app freezes.
        """
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "upload_image_button").click()
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("dark_biryani.jpg")'
        ).click()

        try:
            warning = wait_for_text(driver, "Poor lighting", timeout=12)
            assert warning is not None, (
                "FAIL: Low-light warning not shown. "
                "Feedback: Add brightness check before sending to AI model. "
                "If mean pixel brightness < 80/255, show 'Improve lighting' snackbar."
            )
        except TimeoutException:
            # Check if wrong label was shown instead
            try:
                wrong_label = driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiSelector().textContains("Unknown")'
                )
                pytest.fail(
                    "FAIL: 'Unknown Dish' shown without lighting guidance. "
                    "Feedback: Surface actionable error message, not a silent wrong label."
                )
            except NoSuchElementException:
                pytest.fail("FAIL: App froze or no response shown for low-light image.")

    def test_overlapping_dishes_no_duplicate_entries_in_nutrition_list(self, driver):
        """
        FAIL CASE — overlapping dishes cause same entry twice in nutrition breakdown.
        Expected: de-duplicated list with one 'Naan' entry.
        """
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "upload_image_button").click()
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("naan_overlap.jpg")'
        ).click()

        time.sleep(5)
        nutrition_items = driver.find_elements(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Naan")'
        )
        assert len(nutrition_items) == 1, (
            f"FAIL: 'Naan' appears {len(nutrition_items)} times in nutrition list. "
            "Feedback: Apply deduplication on returned labels before rendering list."
        )


# ════════════════════════════════════════════════════════════════
# TEST CLASS 2 — Ingredient Obfuscation (Black Box)
# ════════════════════════════════════════════════════════════════

class TestIngredientObfuscationUI:
    """
    Failing case: Hidden meat misidentified — user receives wrong nutrition info.
    """

    def test_visible_chicken_shows_correct_protein(self, driver):
        """PASS — visible chicken → protein ~28g per serving shown."""
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "scan_meal_button").click()
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "upload_image_button").click()
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("chicken_clear.jpg")'
        ).click()

        protein_el = wait_for(
            driver,
            (AppiumBy.ACCESSIBILITY_ID, "protein_value"),
            timeout=15
        )
        protein_val = int(protein_el.text.replace("g", "").strip())
        assert 20 <= protein_val <= 40, (
            f"FAIL: Protein value {protein_val}g is out of expected range for chicken."
        )

    def test_buried_meat_biryani_shows_ambiguous_ingredient_prompt(self, driver):
        """
        FAIL CASE — biryani with hidden beef shows 'Potato' as ingredient.
        Expected: 'Ingredient unclear – possible: chicken, mutton, beef' chips shown.
        """
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "upload_image_button").click()
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("biryani_hidden_meat.jpg")'
        ).click()

        try:
            ambiguous_chip = wait_for_text(driver, "Ingredient unclear", timeout=15)
            assert ambiguous_chip is not None
        except TimeoutException:
            try:
                potato = driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiSelector().textContains("Potato")'
                )
                pytest.fail(
                    "FAIL: 'Potato' shown as definitive ingredient for hidden meat. "
                    "Feedback: When model confidence < 0.65 for protein type, show "
                    "'Possible ingredients: X / Y / Z' UI chips instead of a single wrong label."
                )
            except NoSuchElementException:
                pytest.fail("FAIL: No ingredient label shown at all.")

    def test_user_can_manually_correct_ingredient(self, driver):
        """PASS — user taps wrong ingredient chip → correction modal opens."""
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "ingredient_chip_0").click()
        time.sleep(1)
        modal = wait_for(
            driver,
            (AppiumBy.ACCESSIBILITY_ID, "ingredient_correction_modal"),
            timeout=8
        )
        assert modal.is_displayed(), (
            "FAIL: Ingredient correction modal did not open. "
            "Feedback: Each ingredient chip should be tappable to open 'Correct ingredient' modal."
        )
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "modal_close").click()


# ════════════════════════════════════════════════════════════════
# TEST CLASS 3 — Complex Health Profile Meal Plan UI
# ════════════════════════════════════════════════════════════════

class TestHealthProfileMealPlanUI:
    """Failing case: Overlapping conditions → incorrect or empty meal plan."""

    def _set_health_conditions(self, driver, conditions: list):
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "profile_tab").click()
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "health_conditions_edit").click()
        for condition in conditions:
            driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().textContains("{condition}")'
            ).click()
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "save_conditions_button").click()
        time.sleep(1)

    def test_single_condition_generates_meal_plan(self, driver):
        """PASS — diabetes only → valid meal plan displayed."""
        self._set_health_conditions(driver, ["Type 2 Diabetes"])
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "meal_plan_tab").click()
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "generate_plan_button").click()

        plan_card = wait_for(
            driver,
            (AppiumBy.ACCESSIBILITY_ID, "meal_plan_day_1"),
            timeout=20
        )
        assert plan_card.is_displayed(), "FAIL: Meal plan day-1 card not shown."

    def test_multi_condition_plan_loads_not_empty(self, driver):
        """
        FAIL CASE — diabetes + hypertension + CKD → app shows 'No meals available'.
        Expected: restricted but valid plan shown.
        """
        self._set_health_conditions(
            driver, ["Type 2 Diabetes", "Hypertension", "Kidney Disease"]
        )
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "meal_plan_tab").click()
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "generate_plan_button").click()

        try:
            plan_card = wait_for(
                driver,
                (AppiumBy.ACCESSIBILITY_ID, "meal_plan_day_1"),
                timeout=25
            )
            assert plan_card.is_displayed()
        except TimeoutException:
            empty_state = driver.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().textContains("No meals available")'
            )
            if empty_state:
                pytest.fail(
                    "FAIL: 'No meals available' shown for multi-condition profile. "
                    "Feedback: Rule engine must fall back to lowest-common-denominator safe foods "
                    "(boiled vegetables, plain rice, lean protein) when conditions over-constrain."
                )
            else:
                pytest.fail("FAIL: Plan generation timed out — spinner never resolved.")

    def test_conflicting_conditions_show_dietary_conflict_banner(self, driver):
        """
        FAIL CASE — diabetes (high protein) + CKD (low protein) → no conflict warning.
        Expected: yellow banner 'Conflicting dietary needs detected – consult your doctor'.
        """
        self._set_health_conditions(
            driver, ["Type 2 Diabetes", "Kidney Disease"]
        )
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "meal_plan_tab").click()
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "generate_plan_button").click()
        time.sleep(6)

        try:
            banner = wait_for_text(driver, "Conflicting dietary", timeout=10)
            assert banner is not None
        except TimeoutException:
            pytest.fail(
                "FAIL: Conflict banner not shown for diabetes+CKD combination. "
                "Feedback: Detect protein-conflict pair in health conditions before plan render; "
                "show persistent banner with 'consult your doctor' CTA."
            )


# ════════════════════════════════════════════════════════════════
# TEST CLASS 4 — Response Time / Latency (Black Box)
# ════════════════════════════════════════════════════════════════

class TestResponseTimeUI:
    """Failing case: Simultaneous queries cause visible lag or spinner freeze."""

    def test_meal_analysis_completes_within_10_seconds(self, driver):
        """PASS — meal analysis spinner resolves within 10 seconds."""
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "scan_meal_button").click()
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "upload_image_button").click()
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("test_meal.jpg")'
        ).click()

        start = time.monotonic()
        try:
            result = wait_for(
                driver,
                (AppiumBy.ACCESSIBILITY_ID, "meal_result_card"),
                timeout=10
            )
            elapsed = time.monotonic() - start
            assert result.is_displayed()
            assert elapsed <= 10.0, (
                f"FAIL: Meal analysis took {elapsed:.1f}s. "
                "Feedback: Offload AI inference to background worker; show skeleton loader in UI."
            )
        except TimeoutException:
            elapsed = time.monotonic() - start
            pytest.fail(
                f"FAIL: Meal analysis did not complete after {elapsed:.1f}s. "
                "Feedback: Add 10s hard timeout on AI call; show 'Analysis failed – retry' button."
            )

    def test_spinner_not_frozen_during_simultaneous_module_load(self, driver):
        """
        FAIL CASE — simultaneous AI + nutrition + fitness load freezes spinner.
        Expected: spinner animates throughout, result appears ≤ 15s.
        """
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "dashboard_tab").click()
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "full_analysis_button").click()

        spinner = wait_for(
            driver,
            (AppiumBy.ACCESSIBILITY_ID, "loading_spinner"),
            timeout=5
        )
        assert spinner.is_displayed(), "Spinner should appear immediately."
        time.sleep(2)
        # Spinner should still be animated (not frozen UI)
        assert spinner.is_displayed(), (
            "FAIL: Spinner disappeared too early (possible UI freeze). "
            "Feedback: Use separate loading states per module; animate with Lottie."
        )
        try:
            wait_for(
                driver,
                (AppiumBy.ACCESSIBILITY_ID, "analysis_result_screen"),
                timeout=15
            )
        except TimeoutException:
            pytest.fail(
                "FAIL: Full analysis did not complete within 15s. "
                "Feedback: Use parallel async calls; cache nutrition lookups in Redis."
            )


# ════════════════════════════════════════════════════════════════
# TEST CLASS 5 — Posture Estimation UI
# ════════════════════════════════════════════════════════════════

class TestPostureEstimationUI:
    """Failing case: Poor lighting / cluttered background → wrong form feedback shown."""

    def test_clear_squat_shows_score_and_feedback(self, driver):
        """PASS — well-lit squat video gives score ≥ 70 and feedback text."""
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "workout_tab").click()
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "start_exercise_button").click()
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Squat")'
        ).click()
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "upload_video_button").click()
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("squat_clear.mp4")'
        ).click()

        score_el = wait_for(
            driver,
            (AppiumBy.ACCESSIBILITY_ID, "posture_score"),
            timeout=20
        )
        score = int(score_el.text)
        assert score >= 70, f"FAIL: Expected score ≥70, got {score} for clear squat."

        feedback_el = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "posture_feedback")
        assert len(feedback_el.text.strip()) > 0, "FAIL: No feedback text shown."

    def test_dark_video_shows_lighting_warning_not_wrong_score(self, driver):
        """
        FAIL CASE — dark exercise video shows confident but wrong posture score.
        Expected: 'Improve lighting for accurate feedback' message shown.
        """
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "upload_video_button").click()
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("squat_dark.mp4")'
        ).click()
        time.sleep(8)

        try:
            warning = wait_for_text(driver, "Improve lighting", timeout=12)
            assert warning is not None
        except TimeoutException:
            try:
                score_el = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "posture_score")
                pytest.fail(
                    f"FAIL: Score '{score_el.text}' shown for dark video without lighting warning. "
                    "Feedback: Check frame brightness before pose estimation; "
                    "if mean brightness < 80, surface 'Improve lighting' message and skip scoring."
                )
            except NoSuchElementException:
                pytest.fail("FAIL: No response shown for dark exercise video.")

    def test_cluttered_background_shows_reposition_prompt(self, driver):
        """
        FAIL CASE — cluttered gym background → ghost keypoints → incorrect feedback.
        Expected: 'Clear background recommended' advisory shown.
        """
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "upload_video_button").click()
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("squat_cluttered.mp4")'
        ).click()
        time.sleep(8)

        try:
            prompt = wait_for_text(driver, "Clear background", timeout=12)
            assert prompt is not None
        except TimeoutException:
            pytest.fail(
                "FAIL: No background advisory shown for cluttered video. "
                "Feedback: Add background complexity check (edge density heuristic); "
                "if score > threshold, show 'Stand against a plain wall for best results'."
            )

    def test_occluded_joints_score_shown_as_unreliable(self, driver):
        """
        FAIL CASE — workout with equipment blocking knees → normal confident score shown.
        Expected: score card shows 'Partial view – results may be inaccurate' label.
        """
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "upload_video_button").click()
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("squat_occluded.mp4")'
        ).click()
        time.sleep(10)

        try:
            unreliable_badge = wait_for(
                driver,
                (AppiumBy.ACCESSIBILITY_ID, "unreliable_score_badge"),
                timeout=12
            )
            assert unreliable_badge.is_displayed()
        except TimeoutException:
            pytest.fail(
                "FAIL: Unreliable score badge not shown for occluded joint video. "
                "Feedback: When occlusion_ratio > 0.40, attach 'Partial view' badge to score card "
                "and disable the 'Share my score' button."
            )
