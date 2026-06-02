# NutriFit AI — Testing Suite
## White Box (pytest + mock) · Black Box (Appium + Flutter Integration Test)

---

## Quick Start

```
51 passed ✅  |  1 intentional fail ❌ (WB-TC-07 — documented bug)
```

```bash
# White box — run immediately (no device needed)
cd nutrifit_tests
pip install pytest pandas numpy
pytest whitebox/ -v
```

---

## Project Structure

```
nutrifit_tests/
│
├── fixtures/
│   └── mock_backend.py              ← mirrors meal_plan.py, exercise_plan.py
│
├── whitebox/
│   ├── test_wb_filter_foods.py      ← V(G)=4 basis paths, loop, control structure
│   └── test_wb_exercise_latency.py  ← exercise plan, BMI labels, backend latency
│
├── blackbox/
│   ├── appium/
│   │   └── test_bb_appium.py        ← Appium Python client (Android)
│   └── flutter_integration/
│       └── nutrifit_blackbox_test.dart  ← Flutter integration_test (Dart)
│
├── conftest.py                      ← pytest markers + known-failure summary
└── README.md
```

---

## STEP 1 — White Box Tests (pytest)

### Install
```bash
pip install pytest pandas numpy
```

### Point to your real backend (optional)
Open `fixtures/mock_backend.py` and replace stub functions with your actual imports:
```python
# Option A — add backend to sys.path
import sys
sys.path.insert(0, "D:/NutriFit Backend")
from meal_plan     import filter_foods, generate_meal_plan
from exercise_plan import generate_exercise_plan, adjust_exercise, map_activity_level
```

### Run all white box tests
```bash
cd nutrifit_tests
pytest whitebox/ -v
```

### Run only the documented failing cases
```bash
pytest whitebox/ -v -k "FAIL"
```

### Run with HTML coverage report
```bash
pip install pytest-cov
pytest whitebox/ -v --cov=fixtures --cov-report=html
# Opens htmlcov/index.html
```

### Expected output
```
PASSED  whitebox/test_wb_filter_foods.py::TestVariableDeclaration::test_allergies_list_initialises_empty
PASSED  whitebox/test_wb_filter_foods.py::TestVariableDeclaration::test_health_list_initialises_empty
...
PASSED  whitebox/test_wb_filter_foods.py::TestBasisPaths::test_path3_allergy_and_diabetes
FAILED  whitebox/test_wb_filter_foods.py::TestBasisPaths::test_path4_all_conditions_FAIL   ← known bug
PASSED  whitebox/test_wb_exercise_latency.py::TestGenerateExercisePlan::test_7_day_plan_returned
...
FAILED  whitebox/test_wb_exercise_latency.py::TestGenerateExercisePlan::test_unrecognised_goal_FAIL  ← WB-TC-07

========================= 51 passed, 1 failed =========================
```

---

## STEP 2 — Black Box Tests via Appium (Android)

### Prerequisites
```bash
# 1. Node.js + Appium
npm install -g appium
appium driver install uiautomator2

# 2. Python packages
pip install Appium-Python-Client selenium pytest

# 3. Start Appium server (keep running in separate terminal)
appium

# 4. Start Android emulator
emulator -avd Pixel_6_API_33

# 5. Build and install Flutter APK
cd your_flutter_project
flutter build apk --debug
adb install build/app/outputs/flutter-apk/app-debug.apk

# 6. Push test images to device
adb push test_images/biryani_clear.jpg              /sdcard/Download/
adb push test_images/mixed_plate.jpg                /sdcard/Download/
adb push test_images/corrupt_file.jpg               /sdcard/Download/
adb push test_images/beef_biryani_hidden_meat.jpg   /sdcard/Download/
```

### Update capabilities in test file
```python
# blackbox/appium/test_bb_appium.py
APP_PACKAGE  = "com.your.nutrifit"   # from AndroidManifest.xml
APP_ACTIVITY = ".MainActivity"
```

### Run Appium tests
```bash
pytest blackbox/appium/test_bb_appium.py -v --tb=short
```

---

## STEP 3 — Black Box Tests via Flutter Integration Test

### 1. Add dependencies to pubspec.yaml
```yaml
dev_dependencies:
  integration_test:
    sdk: flutter
  flutter_test:
    sdk: flutter
```

### 2. Add semantic Keys to your Flutter widgets
Every testable widget needs a `Key`. Example:
```dart
ElevatedButton(
  key: const Key('signup_button'),
  onPressed: _handleSignup,
  child: const Text('Sign Up'),
)

TextFormField(
  key: const Key('email_field'),
  // ...
)

// Error text widget
if (_emailError != null)
  Text(_emailError!, key: const Key('email_error_text'))
```

See **Widget Key Reference** table below for the full list.

### 3. Run Flutter integration tests
```bash
cd your_flutter_project

# Copy test file into integration_test/
cp path/to/nutrifit_blackbox_test.dart integration_test/

# Run on emulator
flutter test integration_test/nutrifit_blackbox_test.dart \
        --device-id emulator-5554 -v

# Run specific feature group only
flutter test integration_test/nutrifit_blackbox_test.dart \
        --name "Feature 1"
```

---

## Widget Key Reference

Add these `Key` values to the corresponding Flutter widgets:

| Key | Widget / Location |
|-----|-------------------|
| `get_started_button` | Home screen CTA button |
| `signup_button` | Registration form submit |
| `login_button` | Login form submit |
| `login_link` | "Already have account? Login" text |
| `username_field` | Registration username TextFormField |
| `email_field` | Email TextFormField |
| `password_field` | Password TextFormField |
| `name_error_text` | Name validation error Text |
| `email_error_text` | Email validation error Text |
| `password_error_text` | Password validation error Text |
| `profile_setup_screen` | Profile setup page root widget |
| `home_dashboard` | Dashboard root widget |
| `full_name_field` | Profile setup name field |
| `age_field` | Age input |
| `weight_field` | Weight input |
| `height_field` | Height input |
| `target_weight_field` | Target weight input |
| `activity_dropdown` | Activity level dropdown |
| `activity_sedentary` | "Sedentary" dropdown item |
| `goal_dropdown` | Fitness goal dropdown |
| `goal_weight_gain` | "Weight Gain" dropdown item |
| `save_continue_button` | Profile save button |
| `bmi_value_text` | BMI number display Text |
| `bmi_label_text` | BMI category label (Normal / Obese …) |
| `meal_tab` | Bottom nav Meal tab |
| `breakfast_section` | Breakfast card / section |
| `lunch_section` | Lunch card / section |
| `dinner_section` | Dinner card / section |
| `breakfast_food_item` | Individual breakfast food ListTile |
| `lunch_food_item` | Individual lunch food ListTile |
| `cheat_meal_button` | Cheat meal upload button |
| `upload_image_button` | Image picker button |
| `mock_corrupt_image` | Test-only button to inject corrupt image |
| `mock_unknown_food_image` | Test-only button to inject unknown food |
| `mock_multi_dish_image` | Test-only button to inject multi-dish image |
| `mock_beef_biryani_occluded` | Test-only button to inject occluded meat image |
| `detected_food_label` | Detected food name Text |
| `calories_estimate_text` | Estimated calories Text |
| `confidence_score_text` | Similarity confidence score Text |
| `food_confirm_button` | "Is this correct?" confirm button |
| `workout_tab` | Bottom nav Workout tab |
| `start_workout_button` | Start workout button |
| `camera_preview_widget` | Camera live view widget |
| `posture_feedback_text` | Posture feedback label Text |
| `pose_confidence_score` | Landmark confidence score Text |
| `camera_setup_guide` | Pre-workout setup guide widget |

---

## Test Case Coverage

| Test ID | Description | File | Type | Status |
|---------|-------------|------|------|--------|
| WB-TC-01 | filter_foods variable declaration | test_wb_filter_foods.py | White Box | ✅ Pass |
| WB-TC-02 | filter_foods control structure (True/False branches) | test_wb_filter_foods.py | White Box | ✅ Pass |
| WB-TC-03 | filter_foods method parameters | test_wb_filter_foods.py | White Box | ✅ Pass |
| WB-TC-04 | Basis path P4 — all conditions (known data gap) | test_wb_filter_foods.py | White Box | ❌ Known |
| WB-TC-05 | Exercise plan + activity level mapping | test_wb_exercise_latency.py | White Box | ✅ Pass |
| WB-TC-06 | BMI label branch coverage | test_wb_exercise_latency.py | White Box | ✅ Pass |
| WB-TC-07 | Unrecognised goal → no fallback | test_wb_exercise_latency.py | White Box | ❌ Known |
| WB-TC-08 | Backend SLA latency (sequential calls) | test_wb_exercise_latency.py | White Box | ❌ Known |
| BB-R-01 | Valid registration → profile setup | appium + dart | Black Box | ✅ Pass |
| BB-R-02 | Valid login → dashboard | appium + dart | Black Box | ✅ Pass |
| BB-R-03 | Duplicate email error | appium | Black Box | ✅ Pass |
| BB-TC-01 | Empty fields — inline validation | appium + dart | Black Box | ❌ Known |
| BB-TC-02 | Invalid email format — friendly error | appium + dart | Black Box | ❌ Known |
| BB-H-01 | Normal BMI displayed | appium + dart | Black Box | ✅ Pass |
| BB-H-02 | Obese BMI label | appium + dart | Black Box | ✅ Pass |
| BB-H-03 | Underweight BMI label | appium + dart | Black Box | ✅ Pass |
| BB-TC-03 | Zero weight boundary validation | appium + dart | Black Box | ❌ Known |
| BB-M-01 | Meal plan 3-section layout | appium + dart | Black Box | ✅ Pass |
| BB-M-02 | Diabetes filter excludes sweets | appium + dart | Black Box | ✅ Pass |
| BB-M-03 | Egg allergy respected | appium + dart | Black Box | ✅ Pass |
| BB-TC-04 | Multi-condition empty meal plan | appium + dart | Black Box | ❌ Known |
| BB-F-01 | Clear image → food label + calories | appium | Black Box | ✅ Pass |
| BB-F-02 | Corrupt image → friendly error | appium + dart | Black Box | ✅ Pass |
| BB-F-03 | Unknown food → not-found message | appium + dart | Black Box | ✅ Pass |
| BB-TC-05 | Multi-dish confusion — no confidence warning | appium + dart | Black Box | ❌ Known |
| BB-TC-06 | Hidden ingredient misclassification | appium + dart | Black Box | ❌ Known |
| BB-P-01 | Workout screen camera preview shown | appium + dart | Black Box | ✅ Pass |
| BB-P-02 | Posture feedback text element present | appium + dart | Black Box | ✅ Pass |
| BB-TC-07 | Poor lighting — no confidence indicator | appium + dart | Black Box | ❌ **Intentional** |

**Intentional failure presented in pytest run: WB-TC-07** (unrecognised goal returns error dict).
All ❌ Known entries are documented bugs requiring backend or Flutter fixes — not test errors.

---

## Known Bugs Summary

| ID | Root Cause | Fix |
|----|-----------|-----|
| WB-TC-04 | Limited food dataset — stacked filters eliminate all items | Constraint-relaxation fallback when pool < 3 |
| WB-TC-07 | No goal-synonym map — 'body recomposition' not in dataset | Normalise synonyms before DataFrame filter |
| WB-TC-08 | Sequential model load + meal + exercise = > 2s SLA | Cache model at startup; parallelise calls with ThreadPoolExecutor |
| BB-TC-01/02 | Missing TextFormField validators — Firebase called on blank/bad input | Add `validator:` callbacks before any API call |
| BB-TC-03 | No boundary check on weight field | Validate weight ≥ 20 kg before profile save |
| BB-TC-04 | Same root as WB-TC-04 (UI-level symptom) | Same constraint-relaxation fix |
| BB-TC-05/06 | Food recognition confidence threshold missing | Add similarity < 0.6 → prompt user |
| BB-TC-07 | No pre-workout lighting / confidence check | Add camera readiness screen before pose estimation |
