# NutriFit AI — Complete Testing Suite
## White Box (pytest + mock) · Black Box (Appium + Flutter Integration)

Built from actual source files:
- `D:\NutriFit Backend\` → meal_plan.py, exercise_plan.py, profile_setup.py
- `C:\NutriFit Frontend\lib\` → signup_page.dart, login_page.dart, profile_setup.dart, home_page.dart, meal_plan.dart, meal_snap.dart, cheatmeal.dart, exercise_plan.dart

---

## Project Structure

```
nutrifit_tests/
├── fixtures/
│   └── mock_backend.py              ← mirrors real backend classes exactly
├── whitebox/
│   ├── test_wb_meal_filter.py       ← filter_by_allergies, filter_by_health_conditions
│   └── test_wb_exercise_profile.py  ← exercise_plan, BMI/BMR/TDEE, validate_profile
├── blackbox/
│   ├── appium/
│   │   └── test_bb_appium.py        ← Appium Python (Android)
│   └── flutter_integration/
│       └── nutrifit_blackbox_test.dart  ← Flutter integration_test
├── conftest.py
└── README.md
```

---

## STEP 1 — White Box (PyCharm)

```bash
pip install pytest pandas numpy
cd D:\NutriFit Backend\nutrifit_tests
pytest whitebox/ -v
```

Expected: **51 passed, 2 known fails** (WB-P4, WB-TC-07)

---

## STEP 2 — Flutter Keys to Add

Before running black box tests, add these `Key(...)` values to your widgets:

### signup_page.dart
```dart
// ElevatedButton "Sign Up"
ElevatedButton(
  key: const Key('signup_button'),
  onPressed: isLoading ? null : signUp,
  ...
)
```

### login_page.dart
```dart
TextFormField(
  key: const Key('login_email'),
  controller: emailController, ...
)
TextFormField(
  key: const Key('login_password'),
  controller: passwordController, ...
)
ElevatedButton(
  key: const Key('login_button'),
  onPressed: isLoading ? null : login, ...
)
```

### profile_setup.dart — _buildTextFieldWithLoader
```dart
// Change this:
TextFormField(controller: controller, ...)
// To this:
TextFormField(
  key: keyName != null ? Key(keyName!) : null,
  controller: controller, ...
)

// Add key to Save button:
ElevatedButton(
  key: const Key('save_continue_button'), ...
)
```

### home_page.dart
```dart
Text("BMI: $bmi",           key: const Key('bmi_text'),  style: infoStyle()),
Text("BMR: $bmr kcal/day",  key: const Key('bmr_text'),  style: infoStyle()),
Text("TDEE: $tdee kcal/day",key: const Key('tdee_text'), style: infoStyle()),
```

### meal_plan.dart
```dart
// Cheat Meal ElevatedButton:
ElevatedButton(
  key: const Key('cheat_meal_button'),
  onPressed: () { Navigator.push(...CheatMealScreen()...); }, ...
)
```

### meal_snap.dart
```dart
ElevatedButton.icon(
  key: const Key('select_image_button'),
  label: const Text("Select / Capture Meal Image"), ...
)
ElevatedButton.icon(
  key: const Key('analyze_meal_button'),
  label: Text(uploading ? "Analyzing..." : "Analyze Meal"), ...
)
// Predicted label Text widget:
if (predictedLabel != null)
  Text(predictedLabel!, key: const Key('predicted_label_text'))
```

### cheatmeal.dart
```dart
ElevatedButton(
  key: const Key('save_cheat_meal_button'),
  onPressed: saving ? null : _saveCheatMeal, ...
)
```

---

## STEP 3 — Appium Black Box

```bash
# Terminal 1
appium

# Terminal 2 — update APP_PACKAGE in test file first
pip install Appium-Python-Client selenium pytest
adb push test_images/biryani_clear.jpg    /sdcard/Download/
adb push test_images/mixed_plate.jpg      /sdcard/Download/
adb push test_images/corrupt_file.jpg     /sdcard/Download/
pytest blackbox/appium/test_bb_appium.py -v --tb=short
```

---

## STEP 4 — Flutter Integration Test (VS Code)

### pubspec.yaml
```yaml
dev_dependencies:
  integration_test:
    sdk: flutter
  flutter_test:
    sdk: flutter
```

```bash
# VS Code terminal
cp blackbox/flutter_integration/nutrifit_blackbox_test.dart \
   C:\NutriFit Frontend\integration_test\

cd C:\NutriFit Frontend
flutter test integration_test/nutrifit_blackbox_test.dart \
        --device-id emulator-5554 -v
```

---

## Known Bugs

| ID | Source | Root Cause | Fix |
|----|--------|-----------|-----|
| WB-P4 | meal_plan.py | Stacked filters eliminate all foods | Constraint-relaxation when pool < 3 |
| WB-TC-07 | exercise_plan.py | Unknown goal returns error dict | Add synonym normalisation map |
| BB-TC-01/02 | signup_page.dart | Validator only checks isEmpty, not format | Add RegExp validator before Firebase |
| BB-TC-03 | profile_setup.dart | Zero weight not caught Flutter-side | Add weight > 0 validator before API call |
| BB-TC-04 | meal_plan.py + Flutter | Empty meal plan shown for multi-condition user | Same constraint-relaxation fix as WB-P4 |
| BB-TC-05 | meal_snap.dart | No confidence threshold warning | Add similarity < 0.6 → show advisory |
| BB-TC-06 | cheatmeal.dart | Empty form may bypass validation | Confirm _formKey.validate() guards save |
