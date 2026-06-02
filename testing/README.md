# NutriFit AI — Testing Suite
## White Box (pytest) + Black Box (Appium + Flutter Integration)

---

## Project Structure

```
nutrifit_tests/
│
├── fixtures/
│   └── mock_backend.py          ← mirrors meal_plan.py, exercise_plan.py
│
├── whitebox/
│   ├── test_wb_filter_foods.py  ← V(G)=4, basis paths, loop, control structure
│   └── test_wb_exercise_latency.py ← exercise plan, BMI, backend latency
│
├── blackbox/
│   ├── appium/
│   │   └── test_bb_appium.py    ← Appium Python client (Android)
│   └── flutter_integration/
│       └── nutrifit_blackbox_test.dart ← Flutter integration_test
│
├── conftest.py                  ← pytest markers + summary
└── README.md
```

---

## STEP 1 — White Box Tests (pytest)

### Install
```bash
pip install pytest pandas numpy
```

### Point to your real backend
Open `fixtures/mock_backend.py` and replace the stub functions with
imports from your actual backend:
```python
# Option A — add your backend to path:
sys.path.insert(0, "D:/Nutrifit Backend")
from meal_plan     import filter_foods, generate_meal_plan
from exercise_plan import generate_exercise_plan, adjust_exercise
```

### Run all white box tests
```bash
cd nutrifit_tests
pytest whitebox/ -v
```

### Run only failing cases
```bash
pytest whitebox/ -v -k "FAIL"
```

### Run with coverage report
```bash
pip install pytest-cov
pytest whitebox/ -v --cov=fixtures --cov-report=html
```

### Expected output
```
PASSED  whitebox/test_wb_filter_foods.py::TestBasisPaths::test_path1_no_conditions
PASSED  whitebox/test_wb_filter_foods.py::TestBasisPaths::test_path2_allergy_only
PASSED  whitebox/test_wb_filter_foods.py::TestBasisPaths::test_path3_allergy_and_diabetes
FAILED  whitebox/test_wb_filter_foods.py::TestBasisPaths::test_path4_all_conditions_FAIL
PASSED  whitebox/test_wb_exercise_latency.py::TestGenerateExercisePlan::test_7_day_plan_returned
FAILED  whitebox/test_wb_exercise_latency.py::TestGenerateExercisePlan::test_unrecognised_goal_FAIL
FAILED  whitebox/test_wb_exercise_latency.py::TestBackendLatency::test_sequential_backend_SLA_FAIL
```

---

## STEP 2 — Black Box Tests via Appium (Android)

### Prerequisites
```bash
# 1. Install Node.js then Appium
npm install -g appium
appium driver install uiautomator2

# 2. Python packages
pip install Appium-Python-Client selenium pytest

# 3. Start Appium server
appium

# 4. Start Android emulator
emulator -avd Pixel_6_API_33

# 5. Build and install Flutter APK
cd your_flutter_project
flutter build apk --debug
adb install build/app/outputs/flutter-apk/app-debug.apk

# 6. Push test images to device
adb push test_images/biryani_clear.jpg       /sdcard/Download/
adb push test_images/mixed_plate.jpg         /sdcard/Download/
adb push test_images/corrupt_file.jpg        /sdcard/Download/
adb push test_images/beef_biryani_hidden.jpg /sdcard/Download/beef_biryani_hidden_meat.jpg
```

### Update capabilities
In `blackbox/appium/test_bb_appium.py`, update:
```python
APP_PACKAGE  = "com.your.nutrifit"     # from AndroidManifest.xml
APP_ACTIVITY = ".MainActivity"
```

### Run Appium tests
```bash
pytest blackbox/appium/test_bb_appium.py -v --tb=short
```

---

## STEP 3 — Black Box Tests via Flutter Integration Test

### pubspec.yaml — add dependencies
```yaml
dev_dependencies:
  integration_test:
    sdk: flutter
  flutter_test:
    sdk: flutter
```

### Add semantic keys to your Flutter widgets
Every testable widget needs a `Key`. Example:
```dart
// Registration screen
ElevatedButton(
  key: const Key('signup_button'),
  onPressed: _handleSignup,
  child: const Text('Sign Up'),
)

TextFormField(
  key: const Key('email_field'),
  // ...
)

// Error text
if (_emailError != null)
  Text(_emailError!, key: const Key('email_error_text'))
```

### Run Flutter integration tests
```bash
cd your_flutter_project

# Copy test file
cp path/to/nutrifit_blackbox_test.dart integration_test/

# Run on connected device or emulator
flutter test integration_test/nutrifit_blackbox_test.dart \
        --device-id emulator-5554 \
        -v
```

### Run specific group
```bash
flutter test integration_test/nutrifit_blackbox_test.dart \
        --name "Feature 1"
```

---

## Widget Key Reference

Add these Keys to the corresponding Flutter widgets:

| Key                        | Widget / Location                     |
|----------------------------|---------------------------------------|
| `get_started_button`       | Home screen CTA button                |
| `signup_button`            | Registration form submit              |
| `login_button`             | Login form submit                     |
| `login_link`               | "Already have account? Login" text    |
| `username_field`           | Registration username TextFormField   |
| `email_field`              | Email TextFormField                   |
| `password_field`           | Password TextFormField                |
| `name_error_text`          | Name validation error Text            |
| `email_error_text`         | Email validation error Text           |
| `password_error_text`      | Password validation error Text        |
| `profile_setup_screen`     | Profile setup page root widget        |
| `home_dashboard`           | Dashboard root widget                 |
| `full_name_field`          | Profile setup name field              |
| `age_field`                | Age input                             |
| `weight_field`             | Weight input                          |
| `height_field`             | Height input                          |
| `target_weight_field`      | Target weight input                   |
| `activity_dropdown`        | Activity level dropdown               |
| `goal_dropdown`            | Fitness goal dropdown                 |
| `save_continue_button`     | Profile save button                   |
| `bmi_value_text`           | BMI number display Text               |
| `bmi_label_text`           | BMI category label (Normal/Obese...) |
| `meal_tab`                 | Bottom nav Meal tab                   |
| `breakfast_section`        | Breakfast card/section                |
| `lunch_section`            | Lunch card/section                    |
| `dinner_section`           | Dinner card/section                   |
| `breakfast_food_item`      | Individual breakfast food ListTile    |
| `lunch_food_item`          | Individual lunch food ListTile        |
| `cheat_meal_button`        | Cheat meal upload button              |
| `upload_image_button`      | Image picker button                   |
| `detected_food_label`      | Detected food name Text               |
| `calories_estimate_text`   | Estimated calories Text               |
| `confidence_score_text`    | Similarity confidence score Text      |
| `food_confirm_button`      | "Is this correct?" confirm button     |
| `workout_tab`              | Bottom nav Workout tab                |
| `start_workout_button`     | Start workout button                  |
| `camera_preview_widget`    | Camera live view widget               |
| `posture_feedback_text`    | Posture feedback label Text           |
| `pose_confidence_score`    | Landmark confidence score Text        |
| `camera_setup_guide`       | Pre-workout setup guide widget        |

---

## Test Case to File Mapping

| Test ID    | File                              | Type       |
|------------|-----------------------------------|------------|
| WB-TC-01   | test_wb_filter_foods.py           | White Box  |
| WB-TC-02   | test_wb_filter_foods.py           | White Box  |
| WB-TC-03   | test_wb_filter_foods.py           | White Box  |
| WB-TC-04 ❌ | test_wb_filter_foods.py          | White Box  |
| WB-TC-05   | test_wb_exercise_latency.py       | White Box  |
| WB-TC-06   | test_wb_exercise_latency.py       | White Box  |
| WB-TC-07 ❌ | test_wb_exercise_latency.py      | White Box  |
| WB-TC-08 ❌ | test_wb_exercise_latency.py      | White Box  |
| BB-R-01    | test_bb_appium.py + .dart         | Black Box  |
| BB-R-02    | test_bb_appium.py + .dart         | Black Box  |
| BB-R-03    | test_bb_appium.py                 | Black Box  |
| BB-TC-01 ❌ | test_bb_appium.py + .dart        | Black Box  |
| BB-TC-02 ❌ | test_bb_appium.py + .dart        | Black Box  |
| BB-H-01    | test_bb_appium.py + .dart         | Black Box  |
| BB-TC-03 ❌ | test_bb_appium.py + .dart        | Black Box  |
| BB-M-01    | test_bb_appium.py + .dart         | Black Box  |
| BB-TC-04 ❌ | test_bb_appium.py + .dart        | Black Box  |
| BB-F-01    | test_bb_appium.py + .dart         | Black Box  |
| BB-TC-05 ❌ | test_bb_appium.py + .dart        | Black Box  |
| BB-TC-06 ❌ | test_bb_appium.py + .dart        | Black Box  |
| BB-P-01    | test_bb_appium.py + .dart         | Black Box  |
| BB-TC-07 ❌ | test_bb_appium.py + .dart        | Black Box  |
