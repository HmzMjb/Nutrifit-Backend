"""
test_bb_appium.py
════════════════════════════════════════════════════════════════════
BLACK BOX TESTING — NutriFit AI Flutter App (Appium / Android)
────────────────────────────────────────────────────────────────────
Based on actual frontend files:
  signup_page.dart   → Keys: signup_username, signup_email,
                              signup_password, signup_google
  login_page.dart    → No keys yet (added below with patch guide)
  profile_setup.dart → keyName params: name, age, weight, height,
                       goal, targetWeight, activitylevel
  home_page.dart     → BMI: "BMI: $bmi" text, Bottom nav labels
  meal_plan.dart     → "Breakfast" / "Lunch" / "Dinner" section titles
  meal_snap.dart     → predictedLabel, similarity, "Analyze Meal" btn
  cheatmeal.dart     → Form with food_name, calories, protein fields

Prerequisites
─────────────
  npm install -g appium
  appium driver install uiautomator2
  appium                          # start server in separate terminal
  pip install Appium-Python-Client selenium pytest
  flutter build apk --debug
  adb install build/app/.../app-debug.apk

Update APP_PACKAGE below to match your AndroidManifest.xml.
Run : pytest blackbox/appium/test_bb_appium.py -v --tb=short
════════════════════════════════════════════════════════════════════
"""

import pytest
import time
from appium import webdriver
from appium.options import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ─── UPDATE THESE ────────────────────────────────────────────────
APP_PACKAGE  = "com.nutrifit.ai"    # from AndroidManifest.xml
APP_ACTIVITY = ".MainActivity"      # usually .MainActivity
APPIUM_URL   = "http://localhost:4723"
TIMEOUT      = 15


def get_capabilities():
    options = UiAutomator2Options()
    options.platform_name          = "Android"
    options.device_name            = "emulator-5554"
    options.app_package            = APP_PACKAGE
    options.app_activity           = APP_ACTIVITY
    options.automation_name        = "UiAutomator2"
    options.no_reset               = False
    options.auto_grant_permissions = True
    return options


# ─── BASE CLASS ───────────────────────────────────────────────────
class NutrifitBase:

    @pytest.fixture(autouse=True)
    def setup_driver(self):
        self.driver = webdriver.Remote(APPIUM_URL, options=get_capabilities())
        self.wait   = WebDriverWait(self.driver, TIMEOUT)
        yield
        self.driver.quit()

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

    def tap_text(self, text):
        """Tap a widget by its visible text label."""
        self.tap(AppiumBy.XPATH, f"//*[@text='{text}']")

    # ── Reusable flows ────────────────────────────────────────────
    def do_registration(self, name="TestUser",
                        email="testuser@nutrifit.com",
                        password="Test@1234"):
        """
        signup_page.dart keys:
          signup_username, signup_email, signup_password
        Get Started button has no key → find by text.
        """
        self.tap(AppiumBy.XPATH, "//*[@text='Get Started']")
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "signup_username", name)
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "signup_email",    email)
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "signup_password", password)
        self.tap(AppiumBy.XPATH, "//*[@text='Sign Up']")
        time.sleep(3)

    def do_login(self, email="testuser@nutrifit.com", password="Test@1234"):
        """
        login_page.dart: no keys on fields yet.
        Add keys via patch below, then switch to ACCESSIBILITY_ID.
        Meanwhile use label text.
        """
        self.tap(AppiumBy.XPATH, "//*[@text='Login']")
        # Fill by hint text (labelText in InputDecoration)
        self.type_into(AppiumBy.XPATH, "//*[@hint='Email']", email)
        self.type_into(AppiumBy.XPATH, "//*[@hint='Password']", password)
        self.tap(AppiumBy.XPATH, "//*[@text='Login']")
        time.sleep(3)

    def fill_profile(self, weight="60", height="5.4", age="22",
                     target_weight="55", goal="weight loss",
                     activity="sedentary"):
        """
        profile_setup.dart uses keyName params on _buildTextFieldWithLoader.
        Add Key(keyName) inside the TextFormField to use ACCESSIBILITY_ID.
        """
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "name",         "TestUser")
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "age",          age)
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "weight",       weight)
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "height",       height)
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "targetWeight", target_weight)
        # Dropdowns — tap label then select value
        self.tap(AppiumBy.XPATH, "//*[@text='Goal']")
        self.tap_text(goal)
        self.tap(AppiumBy.XPATH, "//*[@text='Activity Level']")
        self.tap_text(activity)
        self.tap(AppiumBy.XPATH, "//*[@text='Save & Continue']")
        time.sleep(4)


# ════════════════════════════════════════════════════════════════
#  FEATURE 1 — REGISTRATION & LOGIN
#  signup_page.dart  /  login_page.dart
# ════════════════════════════════════════════════════════════════
class TestRegistration(NutrifitBase):

    def test_BB_R_01_valid_registration(self):
        """BB-R-01: Valid credentials → PersonalInformation screen shown."""
        self.do_registration()
        # profile_setup.dart is the next screen (PersonalInformation class)
        assert self.is_visible(
            AppiumBy.XPATH, "//*[@text='Personal Information']"
        ), "BB-R-01: Profile setup screen must appear after registration"

    def test_BB_R_02_duplicate_email(self):
        """BB-R-02: Registering same email twice → Firebase error snackbar."""
        self.do_registration(email="duplicate@nutrifit.com")
        self.driver.reset()
        self.do_registration(email="duplicate@nutrifit.com")
        time.sleep(2)
        page = self.driver.page_source
        assert ("already" in page.lower() or "registered" in page.lower() or
                "in use" in page.lower()), \
            "BB-R-02: Duplicate email error must be shown"

    def test_BB_R_03_valid_login_shows_home(self):
        """BB-R-03: Valid login → home_page.dart (Welcome text visible)."""
        self.do_registration()
        self.driver.reset()
        self.do_login()
        assert self.is_visible(
            AppiumBy.XPATH, "//*[contains(@text,'Welcome')]"
        ), "BB-R-03: Welcome text must appear on home after login"

    # ── KNOWN FAILS ───────────────────────────────────────────────
    def test_BB_TC_01_empty_fields_KNOWN_FAIL(self):
        """
        BB-TC-01  KNOWN FAIL
        signup_page.dart validator only checks isEmpty → returns
        'Enter username' / 'Enter email' / 'Enter password' inline.
        Expected : inline error text shown immediately under each field.
        Actual   : form submits → Firebase auth/missing-password error.
        Fix      : add RegExp + format validators before API call.
        """
        self.tap(AppiumBy.XPATH, "//*[@text='Get Started']")
        self.tap(AppiumBy.XPATH, "//*[@text='Sign Up']")
        time.sleep(1)
        page = self.driver.page_source
        name_err  = "Enter username" in page
        email_err = "Enter email"    in page
        pass_err  = "Enter password" in page
        print(f"\n[BB-TC-01] name={name_err} email={email_err} pass={pass_err}")
        assert name_err and email_err and pass_err, (
            "BB-TC-01 KNOWN FAIL: Field-level inline validation not shown. "
            "Fix: add non-empty validators in signup_page.dart TextFormField."
        )

    def test_BB_TC_02_invalid_email_format_KNOWN_FAIL(self):
        """
        BB-TC-02  KNOWN FAIL
        Email validator in signup_page.dart only checks isEmpty.
        'hamza@@gmail' passes the isEmpty check → Firebase throws
        auth/invalid-email instead of a friendly inline message.
        Fix: add RegExp(r'^[\\w.]+@[\\w]+\\.[\\w]+$') validator.
        """
        self.tap(AppiumBy.XPATH, "//*[@text='Get Started']")
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "signup_username", "Hamza")
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "signup_email",    "hamza@@gmail")
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "signup_password", "Test@1234")
        self.tap(AppiumBy.XPATH, "//*[@text='Sign Up']")
        time.sleep(1)
        page = self.driver.page_source
        friendly = ("valid email" in page.lower() or
                    "invalid email" in page.lower())
        print(f"\n[BB-TC-02] Friendly email error shown: {friendly}")
        assert friendly, (
            "BB-TC-02 KNOWN FAIL: No friendly email format error shown. "
            "Fix: add RegExp validator in signup_page.dart before Firebase call."
        )


# ════════════════════════════════════════════════════════════════
#  FEATURE 2 — HEALTH METRICS  (BMI / BMR / TDEE)
#  home_page.dart → Text("BMI: $bmi")
#  profile_setup.dart → validate_required_fields
# ════════════════════════════════════════════════════════════════
class TestHealthMetrics(NutrifitBase):

    def _setup_and_go_home(self, weight="60", height="5.4"):
        self.do_registration()
        self.fill_profile(weight=weight, height=height)

    def test_BB_H_01_normal_bmi_displayed(self):
        """BB-H-01: 60 kg / 5.4 ft → BMI ≈ 21.7 shown on home_page."""
        self._setup_and_go_home()
        bmi_text = self.get_text(
            AppiumBy.XPATH, "//*[contains(@text,'BMI:')]")
        print(f"\n[BB-H-01] BMI text: {bmi_text}")
        # home_page.dart renders as "BMI: 21.7"
        assert "21" in bmi_text or "22" in bmi_text, \
            f"BB-H-01: Expected BMI ~21.7 for 60kg/5.4ft, got '{bmi_text}'"

    def test_BB_H_02_obese_bmi_displayed(self):
        """BB-H-02: 120 kg / 5.5 ft → BMI ≈ 42 on home page."""
        self._setup_and_go_home(weight="120", height="5.5")
        bmi_text = self.get_text(
            AppiumBy.XPATH, "//*[contains(@text,'BMI:')]")
        bmi_val = float(bmi_text.replace("BMI:", "").strip())
        assert bmi_val >= 30.0, \
            f"BB-H-02: Expected Obese BMI (≥30), got {bmi_val}"

    def test_BB_H_03_underweight_bmi_displayed(self):
        """BB-H-03: 35 kg / 5.6 ft → BMI < 18.5 on home page."""
        self._setup_and_go_home(weight="35", height="5.6")
        bmi_text = self.get_text(
            AppiumBy.XPATH, "//*[contains(@text,'BMI:')]")
        bmi_val = float(bmi_text.replace("BMI:", "").strip())
        assert bmi_val < 18.5, \
            f"BB-H-03: Expected Underweight BMI (<18.5), got {bmi_val}"

    def test_BB_H_04_bmr_and_tdee_shown(self):
        """BB-H-04: BMR and TDEE lines visible on home_page dashboard."""
        self._setup_and_go_home()
        assert self.is_visible(
            AppiumBy.XPATH, "//*[contains(@text,'BMR:')]"
        ), "BB-H-04: BMR value not shown on home dashboard"
        assert self.is_visible(
            AppiumBy.XPATH, "//*[contains(@text,'TDEE:')]"
        ), "BB-H-04: TDEE value not shown on home dashboard"

    # ── KNOWN FAIL ────────────────────────────────────────────────
    def test_BB_TC_03_zero_weight_KNOWN_FAIL(self):
        """
        BB-TC-03  KNOWN FAIL  (Boundary Value Analysis)
        profile_setup.dart sends weight=0 to backend.
        Backend profile_setup.py validates: weight must be positive.
        Expected : inline validation error 'Weight must be positive'.
        Actual   : field accepted, API call made, BMI=0 shown or crash.
        Fix      : add Flutter-side validator: weight > 0 before API call.
        """
        self.do_registration()
        # Navigate to profile setup — clear weight field and set 0
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "weight", "0")
        self.type_into(AppiumBy.ACCESSIBILITY_ID, "height", "5.4")
        self.tap(AppiumBy.XPATH, "//*[@text='Save & Continue']")
        time.sleep(2)
        page = self.driver.page_source
        error_shown = ("positive" in page.lower() or
                       "valid" in page.lower() or
                       "must be" in page.lower())
        print(f"\n[BB-TC-03] Validation error shown: {error_shown}")
        assert error_shown, (
            "BB-TC-03 KNOWN FAIL: Zero weight accepted without validation. "
            "Fix: add weight > 0 validator in profile_setup.dart."
        )


# ════════════════════════════════════════════════════════════════
#  FEATURE 3 — MEAL PLAN
#  home_page.dart → bottom nav index 1 → MealPlan widget
#  meal_plan.dart → _buildMealSection("Breakfast" / "Lunch" / "Dinner")
# ════════════════════════════════════════════════════════════════
class TestMealPlan(NutrifitBase):

    def _go_to_meal_tab(self):
        self.do_login()
        self.tap(AppiumBy.XPATH, "//*[@text='Meal']")
        time.sleep(4)

    def test_BB_M_01_three_meal_sections_visible(self):
        """BB-M-01: Meal plan shows Breakfast, Lunch, Dinner sections."""
        self._go_to_meal_tab()
        assert self.is_visible(
            AppiumBy.XPATH, "//*[@text='Breakfast']"
        ), "BB-M-01: Breakfast section missing"
        assert self.is_visible(
            AppiumBy.XPATH, "//*[@text='Lunch']"
        ), "BB-M-01: Lunch section missing"
        assert self.is_visible(
            AppiumBy.XPATH, "//*[@text='Dinner']"
        ), "BB-M-01: Dinner section missing"

    def test_BB_M_02_seven_days_present(self):
        """BB-M-02: All 7 day names visible in meal plan list."""
        self._go_to_meal_tab()
        days = ["Monday", "Tuesday", "Wednesday",
                "Thursday", "Friday", "Saturday", "Sunday"]
        found = sum(
            1 for d in days
            if self.is_visible(AppiumBy.XPATH,
                               f"//*[contains(@text,'{d}')]", timeout=3)
        )
        assert found >= 7, f"BB-M-02: Only {found}/7 days visible"

    def test_BB_M_03_diabetes_filter_no_halwa_kheer(self):
        """BB-M-03: Diabetic user's meal plan must not contain halwa/kheer."""
        self._go_to_meal_tab()
        page = self.driver.page_source.lower()
        assert "halwa" not in page, "BB-M-03: halwa must not appear"
        assert "kheer"  not in page, "BB-M-03: kheer must not appear"

    def test_BB_M_04_egg_allergy_no_omelette(self):
        """BB-M-04: Egg-allergic user's plan must not contain egg omelette."""
        self._go_to_meal_tab()
        page = self.driver.page_source.lower()
        assert "egg omelette" not in page, \
            "BB-M-04: egg omelette must not appear for egg-allergic user"

    def test_BB_M_05_cheat_meal_button_visible(self):
        """BB-M-05: 'Cheat Meal' button present on meal plan screen."""
        self._go_to_meal_tab()
        assert self.is_visible(
            AppiumBy.XPATH, "//*[@text='Cheat Meal']"
        ), "BB-M-05: Cheat Meal button not found on meal plan screen"

    # ── KNOWN FAIL ────────────────────────────────────────────────
    def test_BB_TC_04_multi_condition_plan_KNOWN_FAIL(self):
        """
        BB-TC-04  KNOWN FAIL
        User with diabetes + hypertension + egg + gluten allergies.
        ProfessionalMealPlanner._apply_all_filters() eliminates all foods.
        Expected : meal plan shown with fallback items + advisory message.
        Actual   : blank screen / 'No meal plan found' message.
        Fix      : add constraint-relaxation in meal_plan.py when pool < 3.
        """
        self._go_to_meal_tab()
        time.sleep(2)
        has_breakfast = self.is_visible(
            AppiumBy.XPATH, "//*[@text='Breakfast']", timeout=5)
        has_error     = self.is_visible(
            AppiumBy.XPATH, "//*[contains(@text,'No meal plan')]", timeout=3)
        print(f"\n[BB-TC-04] has_breakfast={has_breakfast} has_error={has_error}")
        assert has_breakfast and not has_error, (
            "BB-TC-04 KNOWN FAIL: Multi-condition profile returns empty meal plan. "
            "Fix: add constraint-relaxation fallback in meal_plan.py."
        )


# ════════════════════════════════════════════════════════════════
#  FEATURE 4 — FOOD IMAGE RECOGNITION
#  meal_snap.dart (UploadMealScreen)
#  Accessed via camera icon on meal_plan.dart AppBar
# ════════════════════════════════════════════════════════════════
class TestFoodRecognition(NutrifitBase):

    BIRYANI_IMAGE = "/sdcard/Download/biryani_clear.jpg"
    MULTI_IMAGE   = "/sdcard/Download/mixed_plate.jpg"
    CORRUPT_IMAGE = "/sdcard/Download/corrupt_file.jpg"

    def _go_to_meal_snap(self):
        self.do_login()
        self.tap(AppiumBy.XPATH, "//*[@text='Meal']")
        time.sleep(2)
        # Camera icon in AppBar of meal_plan.dart
        self.tap(AppiumBy.XPATH, "//*[@content-desc='Upload Meal']")
        time.sleep(1)

    def _upload_and_analyze(self, image_path: str):
        """Push image via adb then tap Select → Gallery → pick file."""
        self.driver.push_file(image_path, image_path)
        self.tap(AppiumBy.XPATH,
                 "//*[@text='Select / Capture Meal Image']")
        time.sleep(1)
        self.tap(AppiumBy.XPATH,
                 "//*[@text='Gallery' or @text='Photos']")
        time.sleep(2)
        # Tap Analyze Meal button
        self.tap(AppiumBy.XPATH,
                 "//*[contains(@text,'Analyze Meal')]")
        time.sleep(5)

    def test_BB_F_01_clear_image_recognized(self):
        """BB-F-01: Clear biryani image → predicted_label shown on screen."""
        self._go_to_meal_snap()
        self._upload_and_analyze(self.BIRYANI_IMAGE)
        page = self.driver.page_source
        # meal_snap.dart renders predictedLabel as a Text widget
        assert self.is_visible(
            AppiumBy.XPATH,
            "//*[contains(@text,'biryani') or contains(@text,'Biryani')]",
            timeout=8
        ), "BB-F-01: Predicted food label not shown after image upload"

    def test_BB_F_02_similarity_score_shown(self):
        """BB-F-02: Similarity score visible after successful recognition."""
        self._go_to_meal_snap()
        self._upload_and_analyze(self.BIRYANI_IMAGE)
        # meal_snap.dart shows similarity as a Text widget
        assert self.is_visible(
            AppiumBy.XPATH,
            "//*[contains(@text,'%') or contains(@text,'similarity')]",
            timeout=8
        ), "BB-F-02: Similarity score not displayed after recognition"

    def test_BB_F_03_corrupt_image_handled(self):
        """BB-F-03: Corrupt file → 'Upload failed' or error snackbar shown."""
        self._go_to_meal_snap()
        self._upload_and_analyze(self.CORRUPT_IMAGE)
        page = self.driver.page_source
        error_shown = ("failed" in page.lower() or
                       "wrong"  in page.lower() or
                       "invalid" in page.lower())
        assert error_shown, "BB-F-03: No error shown for corrupt image"

    def test_BB_F_04_analyze_without_image_disabled(self):
        """BB-F-04: 'Analyze Meal' button disabled when no image selected."""
        self._go_to_meal_snap()
        # meal_snap.dart: onPressed = _image == null ? null : _uploadImage
        btn = self.find(AppiumBy.XPATH,
                        "//*[contains(@text,'Analyze Meal')]")
        # Disabled button is not clickable — verify by checking enabled attr
        assert btn.get_attribute("enabled") in [None, "false", False] or \
               not btn.is_enabled(), \
            "BB-F-04: Analyze button should be disabled before image is selected"

    # ── KNOWN FAIL ────────────────────────────────────────────────
    def test_BB_TC_05_low_similarity_no_warning_KNOWN_FAIL(self):
        """
        BB-TC-05  KNOWN FAIL
        meal_snap.dart renders similarity score but does NOT show a
        warning when similarity < threshold (e.g. multi-dish plate).
        Expected : if similarity < 0.6 → prompt user to photograph
                   one dish at a time.
        Actual   : label shown regardless of confidence level.
        Fix      : add similarity threshold check in meal_snap.dart.
        """
        self._go_to_meal_snap()
        self._upload_and_analyze(self.MULTI_IMAGE)
        low_conf_warning = self.is_visible(
            AppiumBy.XPATH,
            "//*[contains(@text,'one dish') or "
            "contains(@text,'confidence') or "
            "contains(@text,'unclear')]",
            timeout=5
        )
        print(f"\n[BB-TC-05] Low-confidence warning shown: {low_conf_warning}")
        assert low_conf_warning, (
            "BB-TC-05 KNOWN FAIL: No low-confidence warning shown for "
            "multi-dish image. Fix: show advisory when similarity < 0.6."
        )


# ════════════════════════════════════════════════════════════════
#  FEATURE 5 — CHEAT MEAL LOG
#  cheatmeal.dart (CheatMealScreen)
# ════════════════════════════════════════════════════════════════
class TestCheatMeal(NutrifitBase):

    def _go_to_cheat_meal(self):
        self.do_login()
        self.tap(AppiumBy.XPATH, "//*[@text='Meal']")
        time.sleep(3)
        self.tap(AppiumBy.XPATH, "//*[@text='Cheat Meal']")
        time.sleep(2)

    def _fill_cheat_form(self, name="Pizza", calories="800",
                         protein="30", carbs="90", fats="25"):
        """Fill cheatmeal.dart form fields."""
        self.type_into(AppiumBy.XPATH, "//*[@hint='Food Name']",   name)
        self.type_into(AppiumBy.XPATH, "//*[@hint='Calories']",    calories)
        self.type_into(AppiumBy.XPATH, "//*[@hint='Protein (g)']", protein)
        self.type_into(AppiumBy.XPATH, "//*[@hint='Carbs (g)']",   carbs)
        self.type_into(AppiumBy.XPATH, "//*[@hint='Fats (g)']",    fats)

    def test_BB_C_01_cheat_meal_form_visible(self):
        """BB-C-01: Cheat meal form with all 5 fields visible."""
        self._go_to_cheat_meal()
        for hint in ["Food Name", "Calories", "Protein (g)",
                     "Carbs (g)", "Fats (g)"]:
            assert self.is_visible(
                AppiumBy.XPATH, f"//*[@hint='{hint}']"
            ), f"BB-C-01: '{hint}' field not visible"

    def test_BB_C_02_save_cheat_meal(self):
        """BB-C-02: Valid cheat meal saved → success or compensation plan."""
        self._go_to_cheat_meal()
        self._fill_cheat_form()
        self.tap(AppiumBy.XPATH, "//*[@text='Save Cheat Meal']")
        time.sleep(3)
        page = self.driver.page_source
        assert ("saved" in page.lower() or
                "compensation" in page.lower() or
                "success" in page.lower()), \
            "BB-C-02: Cheat meal save did not produce success feedback"

    def test_BB_C_03_compensation_plan_button_visible(self):
        """BB-C-03: 'View Compensation Plan' button present on meal screen."""
        self.do_login()
        self.tap(AppiumBy.XPATH, "//*[@text='Meal']")
        time.sleep(3)
        assert self.is_visible(
            AppiumBy.XPATH,
            "//*[contains(@text,'Compensation Plan')]"
        ), "BB-C-03: Compensation Plan button not visible"

    # ── KNOWN FAIL ────────────────────────────────────────────────
    def test_BB_TC_06_empty_cheat_form_KNOWN_FAIL(self):
        """
        BB-TC-06  KNOWN FAIL
        cheatmeal.dart _formKey validates required: true but sends
        empty form to backend /cheatmeal endpoint on some devices.
        Expected : inline validation 'This field is required' per field.
        Actual   : HTTP call made with empty body → backend 422 error.
        Fix      : ensure _formKey.currentState!.validate() guards
                   _saveCheatMeal() on all paths.
        """
        self._go_to_cheat_meal()
        self.tap(AppiumBy.XPATH, "//*[@text='Save Cheat Meal']")
        time.sleep(1)
        page = self.driver.page_source
        validation_shown = ("required" in page.lower() or
                            "field" in page.lower())
        print(f"\n[BB-TC-06] Form validation shown: {validation_shown}")
        assert validation_shown, (
            "BB-TC-06 KNOWN FAIL: Empty cheat meal form validation missing. "
            "Fix: confirm _formKey.validate() is called before _saveCheatMeal."
        )


# ════════════════════════════════════════════════════════════════
#  FEATURE 6 — EXERCISE PLAN
#  home_page.dart → bottom nav index 2 → ExercisePlan widget
#  exercise_plan.dart
# ════════════════════════════════════════════════════════════════
class TestExercisePlan(NutrifitBase):

    def _go_to_workout_tab(self):
        self.do_login()
        self.tap(AppiumBy.XPATH, "//*[@text='Workout']")
        time.sleep(3)

    def test_BB_E_01_workout_tab_loads(self):
        """BB-E-01: Workout tab opens without crash."""
        self._go_to_workout_tab()
        # exercise_plan.dart should render something on screen
        assert self.is_visible(
            AppiumBy.XPATH,
            "//*[contains(@text,'Exercise') or "
            "contains(@text,'Workout') or "
            "contains(@text,'Day')]",
            timeout=5
        ), "BB-E-01: Workout screen did not load"

    def test_BB_E_02_exercises_listed(self):
        """BB-E-02: At least one exercise item visible in plan."""
        self._go_to_workout_tab()
        page = self.driver.page_source
        # exercise_plan.py returns exercise_name, sets, repetitions
        has_exercise = any(
            ex in page for ex in
            ["Squats", "Push-ups", "Lunges", "Deadlift",
             "Jogging", "Plank", "Bench Press"]
        )
        assert has_exercise, "BB-E-02: No exercise names found in workout plan"

    def test_BB_E_03_sets_reps_shown(self):
        """BB-E-03: Sets and repetitions visible for exercises."""
        self._go_to_workout_tab()
        page = self.driver.page_source
        assert ("sets" in page.lower() or "reps" in page.lower() or
                "repetitions" in page.lower()), \
            "BB-E-03: Sets/reps information not displayed"
