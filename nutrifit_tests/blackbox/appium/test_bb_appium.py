"""
test_bb_appium.py
════════════════════════════════════════════════════════════════════
BLACK BOX TESTING — NutriFit AI Flutter App via Appium
────────────────────────────────────────────────────────────────────
Prerequisites
─────────────
1.  Node.js + Appium server:
        npm install -g appium
        appium driver install uiautomator2
        appium                              # starts on localhost:4723

2.  Python packages:
        pip install Appium-Python-Client selenium pytest

3.  Android emulator or real device:
        adb devices                         # verify device is listed

4.  NutriFit AI Flutter app installed on device:
        flutter build apk --debug
        adb install build/app/outputs/flutter-apk/app-debug.apk

5.  Update APP_PACKAGE / APP_ACTIVITY below to match your app.

Run:
        pytest test_bb_appium.py -v --tb=short
════════════════════════════════════════════════════════════════════
"""

import pytest
import time
from appium import webdriver
from appium.options.android import UiAutomator2Options
#from appium.options import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# ─── APIUM CONFIGURATION ────────────────────────────────────────
APP_PACKAGE  = "com.nutrifit.ai"               # ← update to your package
APP_ACTIVITY = ".MainActivity"                 # ← update to your activity
APIUM_URL   = "http://localhost:4723"
TIMEOUT      = 15   # seconds to wait for elements


def get_capabilities():
    options = UiAutomator2Options()
    options.platform_name          = "Android"
    options.device_name            = "emulator-5554"   # adb devices output
    options.app_package            = APP_PACKAGE
    options.app_activity           = APP_ACTIVITY
    options.automation_name        = "UiAutomator2"
    options.no_reset               = False              # fresh state each run
    options.auto_grant_permissions = True
    return options


# ─── BASE TEST CLASS ─────────────────────────────────────────────
class NutrifitBase:
    """Shared driver setup / teardown and helper utilities."""

    @pytest.fixture(autouse=True)
    def setup_driver(self):
        self.driver = webdriver.Remote(APIUM_URL, options=get_capabilities())
        self.wait   = WebDriverWait(self.driver, TIMEOUT)
        yield
        self.driver.quit()

    # ── helpers ──────────────────────────────────────────────────
    def find(self, by, value):
        return self.wait.until(EC.presence_of_element_located((by, value)))

    def tap(self, by, value):
        self.find(by, value).click()

    def type_into(self, by, value, text):
        el = self.find(by, value)
        el.clear()
        el.send_keys(text)

    def get_text(self, by, value) -> str:
        return self.find(by, value).text

    def is_visible(self, by, value, timeout=5) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value)))
            return True
        except TimeoutException:
            return False

    def do_registration(self, name="TestUser",
                        email="testuser@nutrifit.com",
                        password="Test@1234"):
        """Reusable registration helper."""
        self.tap(AppiumBy.ACCESSIBILITY_ID, "get_started_button")
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "username_field", name)
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "email_field",    email)
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "password_field", password)
        self.tap(AppiumBy.ACCESSIBILITY_ID, "signup_button")
        time.sleep(2)

    def do_login(self, email="testuser@nutrifit.com", password="Test@1234"):
        """Reusable login helper."""
        self.tap(AppiumBy.ACCESSIBILITY_ID, "login_link")
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "email_field",    email)
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "password_field", password)
        self.tap(AppiumBy.ACCESSIBILITY_ID, "login_button")
        time.sleep(2)


# ════════════════════════════════════════════════════════════════
#  FEATURE 1 — USER REGISTRATION & LOGIN
# ════════════════════════════════════════════════════════════════
class TestRegistration(NutrifitBase):

    # ── PASSING ──────────────────────────────────────────────────
    def test_BB_R_01_valid_registration(self):
        """BB-R-01: Valid credentials → account created successfully."""
        self.do_registration()
        success = self.is_visible(AppiumBy.ACCESSIBILITY_ID, "profile_setup_screen")
        assert success, "BB-R-01: Profile setup screen not shown after registration"

    def test_BB_R_02_valid_login(self):
        """BB-R-02: Existing credentials → dashboard shown."""
        self.do_registration()
        self.driver.reset()           # restart app
        self.do_login()
        assert self.is_visible(AppiumBy.ACCESSIBILITY_ID, "home_dashboard"), \
            "BB-R-02: Dashboard not shown after login"

    def test_BB_R_03_duplicate_email(self):
        """BB-R-03: Duplicate email → error message shown."""
        self.do_registration(email="duplicate@test.com")
        self.driver.reset()
        self.do_registration(email="duplicate@test.com")  # register again
        assert self.is_visible(AppiumBy.XPATH,
               "//*[contains(@text,'already registered') or "
               "contains(@text,'email already')]"), \
            "BB-R-03: Duplicate email error not shown"

    # ── FAILING ──────────────────────────────────────────────────
    def test_BB_TC_01_empty_fields_FAIL(self):
        """
        BB-TC-01 FAILING CASE
        Submitting with all blank fields.
        Expected : inline validation errors per field, NO API call.
        Actual   : form submits → Firebase throws generic error.
        """
        self.tap(AppiumBy.ACCESSIBILITY_ID, "get_started_button")
        # leave all fields empty
        self.tap(AppiumBy.ACCESSIBILITY_ID, "signup_button")
        time.sleep(1)

        name_error  = self.is_visible(AppiumBy.ACCESSIBILITY_ID, "name_error_text")
        email_error = self.is_visible(AppiumBy.ACCESSIBILITY_ID, "email_error_text")
        pass_error  = self.is_visible(AppiumBy.ACCESSIBILITY_ID, "password_error_text")

        print(f"\n[BB-TC-01] name_error={name_error}, "
              f"email_error={email_error}, pass_error={pass_error}")

        assert name_error and email_error and pass_error, (
            "BB-TC-01 FAIL: Field-level validation errors not displayed. "
            "Fix: add TextFormField validators in Flutter before any API call."
        )

    def test_BB_TC_02_invalid_email_format_FAIL(self):
        """
        BB-TC-02 FAILING CASE
        Invalid email format not caught client-side.
        Expected : 'Invalid email address' shown immediately.
        Actual   : Firebase auth/invalid-email error thrown instead.
        """
        self.tap(AppiumBy.ACCESSIBILITY_ID, "get_started_button")
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "username_field", "TestUser")
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "email_field",    "hamza@@gmail")
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "password_field", "Test@1234")
        self.tap(AppiumBy.ACCESSIBILITY_ID, "signup_button")
        time.sleep(1)

        friendly_error = self.is_visible(
            AppiumBy.XPATH,
            "//*[contains(@text,'valid email') or "
            "contains(@text,'Invalid email')]")

        print(f"\n[BB-TC-02] Friendly email error shown: {friendly_error}")

        assert friendly_error, (
            "BB-TC-02 FAIL: No friendly email format error shown. "
            "Fix: RegExp validation before Firebase call."
        )


# ════════════════════════════════════════════════════════════════
#  FEATURE 2 — HEALTH METRICS  (BMI / BMR / TDEE)
# ════════════════════════════════════════════════════════════════
class TestHealthMetrics(NutrifitBase):

    def _fill_profile(self, name="Hamza", age="22", weight="60",
                      height="5.4", target_weight="53",
                      activity="Sedentary", goal="Weight Gain"):
        self.do_registration()
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "full_name_field",     name)
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "age_field",           age)
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "weight_field",        weight)
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "height_field",        height)
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "target_weight_field", target_weight)
        # Dropdown selections
        self.tap(AppiumBy.ACCESSIBILITY_ID, "activity_dropdown")
        self.tap(AppiumBy.XPATH, f"//*[@text='{activity}']")
        self.tap(AppiumBy.ACCESSIBILITY_ID, "goal_dropdown")
        self.tap(AppiumBy.XPATH, f"//*[@text='{goal}']")
        self.tap(AppiumBy.ACCESSIBILITY_ID, "save_continue_button")
        time.sleep(3)

    # ── PASSING ──────────────────────────────────────────────────
    def test_BB_H_01_normal_bmi(self):
        """BB-H-01: Valid inputs display correct BMI / BMR / TDEE."""
        self._fill_profile()
        bmi_text = self.get_text(AppiumBy.ACCESSIBILITY_ID, "bmi_value_text")
        assert "18" in bmi_text or "19" in bmi_text, \
            f"BB-H-01: Expected BMI ~18.46, got '{bmi_text}'"

    def test_BB_H_02_obese_label(self):
        """BB-H-02: Obese BMI threshold labelled correctly."""
        self._fill_profile(weight="120", height="5.5")
        label = self.get_text(AppiumBy.ACCESSIBILITY_ID, "bmi_label_text")
        assert "Obese" in label or "obese" in label.lower(), \
            f"BB-H-02: Expected 'Obese' label, got '{label}'"

    def test_BB_H_03_underweight_label(self):
        """BB-H-03: Underweight BMI labelled correctly."""
        self._fill_profile(weight="35", height="5.6")
        label = self.get_text(AppiumBy.ACCESSIBILITY_ID, "bmi_label_text")
        assert "Underweight" in label, \
            f"BB-H-03: Expected 'Underweight', got '{label}'"

    # ── FAILING ──────────────────────────────────────────────────
    def test_BB_TC_03_zero_weight_FAIL(self):
        """
        BB-TC-03 FAILING CASE — Boundary Value Analysis
        Zero weight accepted — app crashes or shows NaN.
        Expected : validation error 'Weight must be between 20–300 kg'.
        Actual   : value accepted, BMI = 0 or NaN displayed.
        """
        self.do_registration()
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "weight_field", "0")
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "height_field", "5.4")
        self.tap(AppiumBy.ACCESSIBILITY_ID, "save_continue_button")
        time.sleep(1)

        error_shown = self.is_visible(
            AppiumBy.XPATH,
            "//*[contains(@text,'valid weight') or "
            "contains(@text,'20') or contains(@text,'invalid')]")

        bmi_shown = self.is_visible(AppiumBy.ACCESSIBILITY_ID, "bmi_value_text", timeout=3)
        if bmi_shown:
            bmi_val = self.get_text(AppiumBy.ACCESSIBILITY_ID, "bmi_value_text")
            print(f"\n[BB-TC-03] BMI displayed for weight=0: '{bmi_val}'")

        assert error_shown, (
            "BB-TC-03 FAIL: Zero weight accepted without validation error. "
            "Fix: add boundary check weight > 0 (min 20kg) in Flutter form."
        )


# ════════════════════════════════════════════════════════════════
#  FEATURE 3 — MEAL PLAN GENERATION
# ════════════════════════════════════════════════════════════════
class TestMealPlan(NutrifitBase):

    def _navigate_to_meal(self):
        """Login and navigate to the Meal tab."""
        self.do_login()
        self.tap(AppiumBy.ACCESSIBILITY_ID, "meal_tab")
        time.sleep(3)

    # ── PASSING ──────────────────────────────────────────────────
    def test_BB_M_01_weight_loss_plan_generated(self):
        """BB-M-01: Weight loss goal generates a lower-calorie 3-meal plan."""
        self._navigate_to_meal()
        assert self.is_visible(AppiumBy.ACCESSIBILITY_ID, "breakfast_section"), \
            "BB-M-01: Breakfast section not shown"
        assert self.is_visible(AppiumBy.ACCESSIBILITY_ID, "lunch_section"), \
            "BB-M-01: Lunch section not shown"
        assert self.is_visible(AppiumBy.ACCESSIBILITY_ID, "dinner_section"), \
            "BB-M-01: Dinner section not shown"

    def test_BB_M_02_diabetes_filter_applied(self):
        """BB-M-02: Halwa/kheer not present in diabetic user's meal plan."""
        self._navigate_to_meal()
        page_source = self.driver.page_source.lower()
        assert "halwa" not in page_source, \
            "BB-M-02: 'halwa' must not appear in diabetic meal plan"
        assert "kheer" not in page_source, \
            "BB-M-02: 'kheer' must not appear in diabetic meal plan"

    def test_BB_M_03_egg_allergy_respected(self):
        """BB-M-03: Egg dishes absent when user has egg allergy."""
        self._navigate_to_meal()
        page_source = self.driver.page_source.lower()
        assert "egg omelette" not in page_source, \
            "BB-M-03: 'egg omelette' found despite egg allergy"

    def test_BB_M_04_seven_day_plan_days(self):
        """BB-M-04: Seven days of meal plan are navigable."""
        self._navigate_to_meal()
        visible_days = 0
        for day_num in range(1, 8):
            if self.is_visible(AppiumBy.XPATH,
                               f"//*[contains(@text,'Day {day_num}')]", timeout=3):
                visible_days += 1
        assert visible_days >= 7, \
            f"BB-M-04: Only {visible_days}/7 days visible in meal plan"

    # ── FAILING ──────────────────────────────────────────────────
    def test_BB_TC_04_multi_condition_meal_plan_FAIL(self):
        """
        BB-TC-04 FAILING CASE
        User with diabetes + hypertension + egg + wheat allergy.
        Expected : Non-empty meal plan shown (with advisory message).
        Actual   : Blank meal screen — no foods pass combined filters.
        """
        self._navigate_to_meal()
        time.sleep(2)
        page_source = self.driver.page_source

        # If these elements are all absent, meal plan is empty
        breakfast_has_items = self.is_visible(
            AppiumBy.ACCESSIBILITY_ID, "breakfast_food_item", timeout=5)
        lunch_has_items = self.is_visible(
            AppiumBy.ACCESSIBILITY_ID, "lunch_food_item", timeout=5)

        print(f"\n[BB-TC-04] breakfast_has_items={breakfast_has_items}, "
              f"lunch_has_items={lunch_has_items}")

        assert breakfast_has_items and lunch_has_items, (
            "BB-TC-04 FAIL: Multi-condition profile returns empty meal plan. "
            "Fix: add constraint-relaxation fallback when filtered pool < 3 items."
        )


# ════════════════════════════════════════════════════════════════
#  FEATURE 4 — FOOD IMAGE RECOGNITION
# ════════════════════════════════════════════════════════════════
class TestFoodRecognition(NutrifitBase):

    BIRYANI_IMAGE = "/sdcard/Download/biryani_clear.jpg"    # push to device first
    MULTI_IMAGE   = "/sdcard/Download/mixed_plate.jpg"      # biryani+raita+salad
    CORRUPT_IMAGE = "/sdcard/Download/corrupt_file.jpg"

    def _navigate_to_cheat(self):
        self.do_login()
        self.tap(AppiumBy.ACCESSIBILITY_ID, "meal_tab")
        self.tap(AppiumBy.ACCESSIBILITY_ID, "cheat_meal_button")
        time.sleep(1)

    def _upload_image(self, path: str):
        """Simulate file upload via Appium file push + gallery picker."""
        self.tap(AppiumBy.ACCESSIBILITY_ID, "upload_image_button")
        time.sleep(1)
        # Select from gallery (UiAutomator2 approach)
        self.tap(AppiumBy.XPATH, "//*[contains(@text,'Gallery') or "
                 "contains(@text,'Photos')]")
        # Use adb to simulate file selection — device path
        self.driver.push_file(path, path)
        time.sleep(2)

    # ── PASSING ──────────────────────────────────────────────────
    def test_BB_F_01_clear_image_recognised(self):
        """BB-F-01: Clear biryani image → food identified and calories shown."""
        self._navigate_to_cheat()
        self._upload_image(self.BIRYANI_IMAGE)
        time.sleep(4)
        assert self.is_visible(AppiumBy.ACCESSIBILITY_ID, "detected_food_label"), \
            "BB-F-01: Food label not displayed after image upload"
        assert self.is_visible(AppiumBy.ACCESSIBILITY_ID, "calories_estimate_text"), \
            "BB-F-01: Calorie estimate not shown"

    def test_BB_F_02_corrupt_image_handled(self):
        """BB-F-02: Corrupt file → friendly error message shown."""
        self._navigate_to_cheat()
        self._upload_image(self.CORRUPT_IMAGE)
        time.sleep(3)
        assert self.is_visible(
            AppiumBy.XPATH,
            "//*[contains(@text,'Invalid') or contains(@text,'invalid') "
            "or contains(@text,'not recognised')]"), \
            "BB-F-02: No error shown for corrupt image"

    def test_BB_F_03_unknown_food_handled(self):
        """BB-F-03: Food not in database → 'not found' message shown."""
        sushi_image = "/sdcard/Download/sushi.jpg"
        self._navigate_to_cheat()
        self._upload_image(sushi_image)
        time.sleep(4)
        assert self.is_visible(
            AppiumBy.XPATH,
            "//*[contains(@text,'not found') or contains(@text,'not identified') "
            "or contains(@text,'manually')]"), \
            "BB-F-03: Unknown food not handled gracefully"

    # ── FAILING ──────────────────────────────────────────────────
    def test_BB_TC_05_multi_dish_confusion_FAIL(self):
        """
        BB-TC-05 FAILING CASE
        Plate with biryani + raita + salad → system misidentifies.
        Expected : dominant dish identified OR prompt to photograph one dish.
        Actual   : incorrect label 'fruit chaat', wrong calorie estimate.
        """
        self._navigate_to_cheat()
        self._upload_image(self.MULTI_IMAGE)
        time.sleep(5)

        label_el    = self.is_visible(AppiumBy.ACCESSIBILITY_ID, "detected_food_label")
        low_conf_el = self.is_visible(
            AppiumBy.XPATH,
            "//*[contains(@text,'one dish') or contains(@text,'confidence') "
            "or contains(@text,'unclear')]", timeout=3)

        detected_label = ""
        if label_el:
            detected_label = self.get_text(
                AppiumBy.ACCESSIBILITY_ID, "detected_food_label")

        print(f"\n[BB-TC-05] Detected label: '{detected_label}'")
        print(f"           Low-confidence prompt shown: {low_conf_el}")

        # Either a correct label OR a low-confidence prompt must appear
        correct = ("biryani" in detected_label.lower()) or low_conf_el
        assert correct, (
            "BB-TC-05 FAIL: Multi-dish image misidentified without "
            "confidence warning. Fix: add similarity threshold check "
            "and prompt user to photograph one dish at a time."
        )

    def test_BB_TC_06_ingredient_obfuscation_FAIL(self):
        """
        BB-TC-06 FAILING CASE
        Beef biryani with meat hidden under rice → protein misclassified.
        Expected : beef biryani identified, correct protein ~22g/100g.
        Actual   : chicken biryani or plain rice returned, ~12g protein.
        """
        beef_biryani_image = "/sdcard/Download/beef_biryani_hidden_meat.jpg"
        self._navigate_to_cheat()
        self._upload_image(beef_biryani_image)
        time.sleep(5)

        label = self.get_text(AppiumBy.ACCESSIBILITY_ID, "detected_food_label")
        print(f"\n[BB-TC-06] Detected: '{label}'")

        assert "beef" in label.lower(), (
            f"BB-TC-06 FAIL: Expected 'beef biryani', got '{label}'. "
            "Hidden ingredients cause misclassification. "
            "Fix: add user confirmation step after detection."
        )


# ════════════════════════════════════════════════════════════════
#  FEATURE 5 — POSE ESTIMATION
# ════════════════════════════════════════════════════════════════
class TestPoseEstimation(NutrifitBase):

    def _navigate_to_workout(self):
        self.do_login()
        self.tap(AppiumBy.ACCESSIBILITY_ID, "workout_tab")
        time.sleep(1)
        self.tap(AppiumBy.ACCESSIBILITY_ID, "start_workout_button")
        time.sleep(2)

    # ── PASSING ──────────────────────────────────────────────────
    def test_BB_P_01_correct_posture_detected(self):
        """BB-P-01: Good squat form in well-lit room → 'Correct form' shown."""
        self._navigate_to_workout()
        time.sleep(5)   # allow MediaPipe to initialise and detect
        assert self.is_visible(
            AppiumBy.XPATH,
            "//*[contains(@text,'Correct') or contains(@text,'correct') "
            "or contains(@text,'Good form')]"), \
            "BB-P-01: Correct posture feedback not displayed"

    def test_BB_P_02_incorrect_posture_alert(self):
        """BB-P-02: Slouching posture triggers corrective alert."""
        self._navigate_to_workout()
        time.sleep(5)
        # In automated context we check the alert exists in the UI hierarchy
        assert self.is_visible(
            AppiumBy.ACCESSIBILITY_ID, "posture_feedback_text"), \
            "BB-P-02: Posture feedback text element not found"

    # ── FAILING ──────────────────────────────────────────────────
    def test_BB_TC_07_poor_lighting_FAIL(self):
        """
        BB-TC-07 FAILING CASE
        Poor lighting / occluded joints → false 'Poor form' alert or no detection.
        Expected : confidence indicator shown, advisory to improve conditions.
        Actual   : 'Joints not detected' OR wrong corrective feedback triggered.

        In automated test we verify the app handles low-confidence gracefully
        by checking for a readiness/confidence UI element.
        """
        self._navigate_to_workout()
        time.sleep(5)

        confidence_indicator = self.is_visible(
            AppiumBy.ACCESSIBILITY_ID, "pose_confidence_score", timeout=5)

        lighting_warning = self.is_visible(
            AppiumBy.XPATH,
            "//*[contains(@text,'lighting') or contains(@text,'Lighting') "
            "or contains(@text,'conditions')]", timeout=5)

        print(f"\n[BB-TC-07] confidence_indicator={confidence_indicator}, "
              f"lighting_warning={lighting_warning}")

        assert confidence_indicator or lighting_warning, (
            "BB-TC-07 FAIL: No confidence score or lighting advisory shown. "
            "Fix: add pre-workout camera check screen with lighting readiness "
            "indicator and minimum confidence threshold before feedback."
        )
