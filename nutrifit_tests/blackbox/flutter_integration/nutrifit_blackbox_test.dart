// integration_test/nutrifit_blackbox_test.dart
// ═══════════════════════════════════════════════════════════════════
// BLACK BOX INTEGRATION TESTS — NutriFit AI Flutter App
// ───────────────────────────────────────────────────────────────────
// Framework : flutter_test + integration_test
// Run       : flutter test integration_test/nutrifit_blackbox_test.dart
//             --device-id emulator-5554
//
// pubspec.yaml dependencies to add:
//   dev_dependencies:
//     integration_test:
//       sdk: flutter
//     flutter_test:
//       sdk: flutter
// ═══════════════════════════════════════════════════════════════════

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

// Replace with your actual app import
// import 'package:nutrifit_ai/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  // ─── HELPERS ───────────────────────────────────────────────────
  Future<void> pumpAndSettle(WidgetTester t, {int seconds = 3}) async {
    await t.pumpAndSettle(Duration(seconds: seconds));
  }

  Future<void> tapKey(WidgetTester t, String key) async {
    await t.tap(find.byKey(Key(key)));
    await t.pumpAndSettle();
  }

  Future<void> typeIntoKey(WidgetTester t, String key, String text) async {
    await t.tap(find.byKey(Key(key)));
    await t.enterText(find.byKey(Key(key)), text);
    await t.pumpAndSettle();
  }

  Future<void> doRegistration(WidgetTester t, {
    String name     = 'TestUser',
    String email    = 'test@nutrifit.com',
    String password = 'Test@1234',
  }) async {
    await tapKey(t, 'get_started_button');
    await typeIntoKey(t, 'username_field', name);
    await typeIntoKey(t, 'email_field',    email);
    await typeIntoKey(t, 'password_field', password);
    await tapKey(t, 'signup_button');
    await pumpAndSettle(t, seconds: 3);
  }

  // ══════════════════════════════════════════════════════════════
  //  GROUP 1 — USER REGISTRATION & LOGIN
  // ══════════════════════════════════════════════════════════════
  group('Feature 1 — Registration & Login', () {

    // ── PASSING ─────────────────────────────────────────────────
    testWidgets('BB-R-01: Valid registration navigates to profile setup',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await doRegistration(t);
      expect(find.byKey(const Key('profile_setup_screen')), findsOneWidget,
          reason: 'BB-R-01: Profile setup must appear after registration');
    });

    testWidgets('BB-R-02: Valid login shows dashboard', (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await tapKey(t, 'login_link');
      await typeIntoKey(t, 'email_field',    'test@nutrifit.com');
      await typeIntoKey(t, 'password_field', 'Test@1234');
      await tapKey(t, 'login_button');
      await pumpAndSettle(t, seconds: 3);
      expect(find.byKey(const Key('home_dashboard')), findsOneWidget,
          reason: 'BB-R-02: Dashboard must appear after login');
    });

    // ── FAILING ─────────────────────────────────────────────────
    testWidgets('BB-TC-01 FAIL: Empty fields show inline validation errors',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await tapKey(t, 'get_started_button');
      // All fields left empty
      await tapKey(t, 'signup_button');
      await pumpAndSettle(t);

      final nameError  = find.byKey(const Key('name_error_text'));
      final emailError = find.byKey(const Key('email_error_text'));
      final passError  = find.byKey(const Key('password_error_text'));

      debugPrint('[BB-TC-01] name_error visible: ${t.any(nameError)}');
      debugPrint('[BB-TC-01] email_error visible: ${t.any(emailError)}');
      debugPrint('[BB-TC-01] pass_error visible: ${t.any(passError)}');

      expect(nameError,  findsOneWidget,
          reason: 'BB-TC-01 FAIL: Name field must show inline error');
      expect(emailError, findsOneWidget,
          reason: 'BB-TC-01 FAIL: Email field must show inline error');
      expect(passError,  findsOneWidget,
          reason: 'BB-TC-01 FAIL: Password field must show inline error. '
                  'Fix: add validator in TextFormField.');
    });

    testWidgets('BB-TC-02 FAIL: Invalid email format shows friendly error',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await tapKey(t, 'get_started_button');
      await typeIntoKey(t, 'username_field', 'Hamza');
      await typeIntoKey(t, 'email_field',    'hamza@@gmail');
      await typeIntoKey(t, 'password_field', 'Test@1234');
      await tapKey(t, 'signup_button');
      await pumpAndSettle(t);

      final errorText = find.text('Please enter a valid email address');
      debugPrint('[BB-TC-02] Friendly email error found: ${t.any(errorText)}');

      expect(errorText, findsOneWidget,
          reason: 'BB-TC-02 FAIL: Friendly email format error not shown. '
                  'Fix: add RegExp validator before Firebase call.');
    });
  });

  // ══════════════════════════════════════════════════════════════
  //  GROUP 2 — HEALTH METRICS (BMI / BMR / TDEE)
  // ══════════════════════════════════════════════════════════════
  group('Feature 2 — Health Metrics', () {

    Future<void> fillProfile(WidgetTester t, {
      String weight = '60',
      String height = '5.4',
      String age    = '22',
    }) async {
      await doRegistration(t);
      await typeIntoKey(t, 'full_name_field', 'Hamza');
      await typeIntoKey(t, 'age_field',       age);
      await typeIntoKey(t, 'weight_field',    weight);
      await typeIntoKey(t, 'height_field',    height);
      await typeIntoKey(t, 'target_weight_field', '53');
      await tapKey(t, 'activity_dropdown');
      await tapKey(t, 'activity_sedentary');
      await tapKey(t, 'goal_dropdown');
      await tapKey(t, 'goal_weight_gain');
      await tapKey(t, 'save_continue_button');
      await pumpAndSettle(t, seconds: 3);
    }

    // ── PASSING ─────────────────────────────────────────────────
    testWidgets('BB-H-01: Normal BMI displayed correctly',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await fillProfile(t);
      final bmiWidget = find.byKey(const Key('bmi_value_text'));
      expect(bmiWidget, findsOneWidget,
          reason: 'BB-H-01: BMI value must be displayed on dashboard');
      final bmiText = (t.widget(bmiWidget) as Text).data ?? '';
      debugPrint('[BB-H-01] BMI displayed: $bmiText');
      expect(bmiText.contains('18') || bmiText.contains('19'), true,
          reason: 'BB-H-01: Expected BMI ≈ 18.46 for 60kg/5.4ft');
    });

    testWidgets('BB-H-02: Obese BMI label shown', (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await fillProfile(t, weight: '120', height: '5.5');
      final labelWidget = find.byKey(const Key('bmi_label_text'));
      expect(labelWidget, findsOneWidget);
      final label = (t.widget(labelWidget) as Text).data ?? '';
      expect(label.toLowerCase().contains('obese'), true,
          reason: 'BB-H-02: Expected Obese label for 120kg/5.5ft');
    });

    testWidgets('BB-H-03: Underweight BMI label shown', (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await fillProfile(t, weight: '35', height: '5.6');
      final labelWidget = find.byKey(const Key('bmi_label_text'));
      expect(labelWidget, findsOneWidget);
      final label = (t.widget(labelWidget) as Text).data ?? '';
      expect(label.toLowerCase().contains('underweight'), true,
          reason: 'BB-H-03: Expected Underweight label for 35kg/5.6ft');
    });

    // ── FAILING ─────────────────────────────────────────────────
    testWidgets('BB-TC-03 FAIL: Zero weight shows validation error',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await doRegistration(t);
      await typeIntoKey(t, 'weight_field', '0');
      await typeIntoKey(t, 'height_field', '5.4');
      await tapKey(t, 'save_continue_button');
      await pumpAndSettle(t);

      final errorFinder = find.textContaining('valid weight');
      debugPrint('[BB-TC-03] Validation error found: ${t.any(errorFinder)}');

      expect(errorFinder, findsOneWidget,
          reason: 'BB-TC-03 FAIL: Zero weight accepted without error. '
                  'Fix: add min boundary validator (weight > 0, min 20kg).');
    });
  });

  // ══════════════════════════════════════════════════════════════
  //  GROUP 3 — MEAL PLAN GENERATION
  // ══════════════════════════════════════════════════════════════
  group('Feature 3 — Meal Plan', () {

    Future<void> goToMealTab(WidgetTester t) async {
      await tapKey(t, 'login_link');
      await typeIntoKey(t, 'email_field',    'test@nutrifit.com');
      await typeIntoKey(t, 'password_field', 'Test@1234');
      await tapKey(t, 'login_button');
      await pumpAndSettle(t, seconds: 4);
      await tapKey(t, 'meal_tab');
      await pumpAndSettle(t, seconds: 4);
    }

    // ── PASSING ─────────────────────────────────────────────────
    testWidgets('BB-M-01: Meal plan shows 3 meal sections',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await goToMealTab(t);
      expect(find.byKey(const Key('breakfast_section')), findsOneWidget,
          reason: 'BB-M-01: Breakfast section missing');
      expect(find.byKey(const Key('lunch_section')),     findsOneWidget,
          reason: 'BB-M-01: Lunch section missing');
      expect(find.byKey(const Key('dinner_section')),    findsOneWidget,
          reason: 'BB-M-01: Dinner section missing');
    });

    testWidgets('BB-M-02: Diabetic plan excludes sweets',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await goToMealTab(t);
      expect(find.textContaining('halwa'), findsNothing,
          reason: 'BB-M-02: Halwa must not appear in diabetic meal plan');
      expect(find.textContaining('kheer'), findsNothing,
          reason: 'BB-M-02: Kheer must not appear in diabetic meal plan');
    });

    testWidgets('BB-M-03: Egg allergy removes egg dishes',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await goToMealTab(t);
      expect(find.textContaining('egg omelette'), findsNothing,
          reason: 'BB-M-03: Egg omelette must not appear for egg-allergic user');
    });

    // ── FAILING ─────────────────────────────────────────────────
    testWidgets('BB-TC-04 FAIL: Multi-condition plan not empty',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await goToMealTab(t);

      // Should find at least one food item in breakfast
      final breakfast = find.byKey(const Key('breakfast_food_item'));
      final lunch     = find.byKey(const Key('lunch_food_item'));

      debugPrint('[BB-TC-04] breakfast_item found: ${t.any(breakfast)}');
      debugPrint('[BB-TC-04] lunch_item found: ${t.any(lunch)}');

      expect(breakfast, findsWidgets,
          reason: 'BB-TC-04 FAIL: Multi-condition profile shows empty '
                  'breakfast plan. Fix: add constraint-relaxation fallback.');
      expect(lunch, findsWidgets,
          reason: 'BB-TC-04 FAIL: Multi-condition profile shows empty '
                  'lunch plan.');
    });
  });

  // ══════════════════════════════════════════════════════════════
  //  GROUP 4 — FOOD IMAGE RECOGNITION
  // ══════════════════════════════════════════════════════════════
  group('Feature 4 — Food Recognition', () {

    Future<void> goToCheatMeal(WidgetTester t) async {
      await tapKey(t, 'login_link');
      await typeIntoKey(t, 'email_field',    'test@nutrifit.com');
      await typeIntoKey(t, 'password_field', 'Test@1234');
      await tapKey(t, 'login_button');
      await pumpAndSettle(t, seconds: 3);
      await tapKey(t, 'meal_tab');
      await tapKey(t, 'cheat_meal_button');
      await pumpAndSettle(t);
    }

    // ── PASSING ─────────────────────────────────────────────────
    testWidgets('BB-F-02: Corrupt file shows friendly error',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await goToCheatMeal(t);
      // Simulate corrupt file scenario via mock provider if available
      await tapKey(t, 'upload_image_button');
      await tapKey(t, 'mock_corrupt_image'); // mock button for testing
      await pumpAndSettle(t, seconds: 3);
      expect(
        find.textContaining('Invalid').evaluate().isNotEmpty ||
        find.textContaining('invalid').evaluate().isNotEmpty,
        true,
        reason: 'BB-F-02: No error shown for corrupt image',
      );
    });

    testWidgets('BB-F-03: Unknown food shows not-found message',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await goToCheatMeal(t);
      await tapKey(t, 'upload_image_button');
      await tapKey(t, 'mock_unknown_food_image');
      await pumpAndSettle(t, seconds: 4);
      final notFound =
          find.textContaining('not found').evaluate().isNotEmpty ||
          find.textContaining('manually').evaluate().isNotEmpty;
      expect(notFound, true,
          reason: 'BB-F-03: Unknown food not handled gracefully');
    });

    // ── FAILING ─────────────────────────────────────────────────
    testWidgets('BB-TC-05 FAIL: Multi-dish image shows confidence warning',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await goToCheatMeal(t);
      await tapKey(t, 'upload_image_button');
      await tapKey(t, 'mock_multi_dish_image');
      await pumpAndSettle(t, seconds: 5);

      final labelWidget  = find.byKey(const Key('detected_food_label'));
      final warnWidget   = find.textContaining('one dish');
      final confWidget   = find.byKey(const Key('confidence_score_text'));

      String detectedLabel = '';
      if (t.any(labelWidget)) {
        detectedLabel = (t.widget(labelWidget) as Text).data ?? '';
      }
      debugPrint('[BB-TC-05] Detected: $detectedLabel');

      final correctOrWarned =
          detectedLabel.toLowerCase().contains('biryani') ||
          t.any(warnWidget) ||
          t.any(confWidget);

      expect(correctOrWarned, true,
          reason: 'BB-TC-05 FAIL: Multi-dish misidentified with no warning. '
                  'Fix: add similarity threshold check (< 0.6 → prompt user).');
    });

    testWidgets('BB-TC-06 FAIL: Hidden ingredients show confirmation prompt',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await goToCheatMeal(t);
      await tapKey(t, 'upload_image_button');
      await tapKey(t, 'mock_beef_biryani_occluded');
      await pumpAndSettle(t, seconds: 5);

      final labelWidget = find.byKey(const Key('detected_food_label'));
      String label = '';
      if (t.any(labelWidget)) {
        label = (t.widget(labelWidget) as Text).data ?? '';
      }
      debugPrint('[BB-TC-06] Detected label: $label');

      // Either correct OR a confirmation prompt must appear
      final confirmPrompt =
          find.textContaining('Is this correct').evaluate().isNotEmpty ||
          find.byKey(const Key('food_confirm_button')).evaluate().isNotEmpty;

      expect(
        label.toLowerCase().contains('beef') || confirmPrompt,
        true,
        reason: 'BB-TC-06 FAIL: Beef biryani with hidden meat misidentified '
                'with no user confirmation prompt. '
                'Fix: show confirmation dialog after every food detection.',
      );
    });
  });

  // ══════════════════════════════════════════════════════════════
  //  GROUP 5 — POSE ESTIMATION
  // ══════════════════════════════════════════════════════════════
  group('Feature 5 — Pose Estimation', () {

    Future<void> startWorkout(WidgetTester t) async {
      await tapKey(t, 'login_link');
      await typeIntoKey(t, 'email_field',    'test@nutrifit.com');
      await typeIntoKey(t, 'password_field', 'Test@1234');
      await tapKey(t, 'login_button');
      await pumpAndSettle(t, seconds: 3);
      await tapKey(t, 'workout_tab');
      await tapKey(t, 'start_workout_button');
      await pumpAndSettle(t, seconds: 4);
    }

    // ── PASSING ─────────────────────────────────────────────────
    testWidgets('BB-P-01: Workout screen camera view shown',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await startWorkout(t);
      expect(find.byKey(const Key('camera_preview_widget')), findsOneWidget,
          reason: 'BB-P-01: Camera preview must be shown in workout screen');
    });

    testWidgets('BB-P-02: Posture feedback text element present',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await startWorkout(t);
      expect(find.byKey(const Key('posture_feedback_text')), findsOneWidget,
          reason: 'BB-P-02: Posture feedback text must be present in UI');
    });

    // ── FAILING ─────────────────────────────────────────────────
    testWidgets('BB-TC-07 FAIL: Confidence score or lighting warning shown',
        (WidgetTester t) async {
      // app.main();
      await pumpAndSettle(t);
      await startWorkout(t);
      await pumpAndSettle(t, seconds: 5);

      final confidenceEl = find.byKey(const Key('pose_confidence_score'));
      final lightingEl   = find.textContaining('lighting');
      final setupGuide   = find.byKey(const Key('camera_setup_guide'));

      debugPrint('[BB-TC-07] confidence_el: ${t.any(confidenceEl)}');
      debugPrint('[BB-TC-07] lighting_warn: ${t.any(lightingEl)}');
      debugPrint('[BB-TC-07] setup_guide:   ${t.any(setupGuide)}');

      expect(
        t.any(confidenceEl) || t.any(lightingEl) || t.any(setupGuide),
        true,
        reason: 'BB-TC-07 FAIL: No pose confidence score or lighting advisory '
                'shown. Fix: add pre-workout camera readiness check screen.',
      );
    });
  });
}
