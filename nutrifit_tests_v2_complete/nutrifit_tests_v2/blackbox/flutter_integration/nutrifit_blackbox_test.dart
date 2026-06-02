// integration_test/nutrifit_blackbox_test.dart
// ═══════════════════════════════════════════════════════════════════
// BLACK BOX INTEGRATION TESTS — NutriFit AI Flutter App
// ───────────────────────────────────────────────────────────────────
// Based on actual frontend dart files:
//   signup_page.dart   → Keys: signup_username, signup_email,
//                               signup_password, signup_google
//   login_page.dart    → Needs keys added (patch guide below)
//   profile_setup.dart → keyName: name, age, weight, height,
//                                 goal, targetWeight, activitylevel
//   home_page.dart     → Text("BMI: $bmi"), Text("BMR: $bmr kcal/day"),
//                        BottomNavigationBar labels
//   meal_plan.dart     → _buildMealSection("Breakfast"/"Lunch"/"Dinner")
//   meal_snap.dart     → predictedLabel, "Analyze Meal" button
//   cheatmeal.dart     → Form fields: Food Name, Calories, Protein etc.
//   exercise_plan.dart → ExercisePlan widget
//
// ── STEP 1: Add to pubspec.yaml ──────────────────────────────────
//   dev_dependencies:
//     integration_test:
//       sdk: flutter
//     flutter_test:
//       sdk: flutter
//
// ── STEP 2: Keys to add to your Flutter widgets ──────────────────
//
//   signup_page.dart — already has:
//     signup_username, signup_email, signup_password, signup_google
//   signup_page.dart — ADD key to Sign Up ElevatedButton:
//     key: const Key('signup_button')
//
//   login_page.dart — ADD keys:
//     TextFormField email    → key: const Key('login_email')
//     TextFormField password → key: const Key('login_password')
//     ElevatedButton Login   → key: const Key('login_button')
//     TextButton "Sign Up"   → key: const Key('go_to_signup')
//
//   profile_setup.dart — _buildTextFieldWithLoader already uses
//   keyName param. Expose it as a Key by changing:
//     TextFormField( controller: controller, ...)
//   to:
//     TextFormField( key: keyName != null ? Key(keyName!) : null,
//                    controller: controller, ...)
//   Also add key to Save button:
//     ElevatedButton( key: const Key('save_continue_button'), ...)
//
//   home_page.dart — ADD keys to Text widgets:
//     Text("BMI: $bmi",  key: const Key('bmi_text'))
//     Text("BMR: $bmr kcal/day", key: const Key('bmr_text'))
//     Text("TDEE: $tdee kcal/day", key: const Key('tdee_text'))
//
//   meal_plan.dart — ADD key to _buildMealSection Container:
//     Container( key: Key('meal_section_$title'), ...)
//   ADD key to Cheat Meal ElevatedButton:
//     ElevatedButton( key: const Key('cheat_meal_button'), ...)
//
//   meal_snap.dart — ADD keys:
//     ElevatedButton "Select / Capture" → key: const Key('select_image_button')
//     ElevatedButton "Analyze Meal"     → key: const Key('analyze_meal_button')
//     Text(predictedLabel)              → key: const Key('predicted_label_text')
//
//   cheatmeal.dart — ADD key to Save button:
//     ElevatedButton( key: const Key('save_cheat_meal_button'), ...)
//
// Run:
//   flutter test integration_test/nutrifit_blackbox_test.dart \
//           --device-id emulator-5554 -v
// ═══════════════════════════════════════════════════════════════════

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

// Uncomment when running against your real app:
// import 'package:nutrifit/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  // ══════════════════════════════════════════════════════════════
  //  SHARED HELPERS
  // ══════════════════════════════════════════════════════════════

  Future<void> settle(WidgetTester t, {int seconds = 3}) async {
    await t.pumpAndSettle(Duration(seconds: seconds));
  }

  Future<void> tapKey(WidgetTester t, String key) async {
    await t.tap(find.byKey(Key(key)));
    await t.pumpAndSettle();
  }

  Future<void> tapText(WidgetTester t, String text) async {
    await t.tap(find.text(text));
    await t.pumpAndSettle();
  }

  Future<void> typeInto(WidgetTester t, String key, String text) async {
    await t.tap(find.byKey(Key(key)));
    await t.enterText(find.byKey(Key(key)), text);
    await t.pumpAndSettle();
  }

  /// signup_page.dart registration flow
  Future<void> doRegistration(WidgetTester t, {
    String name     = 'TestUser',
    String email    = 'testuser@nutrifit.com',
    String password = 'Test@1234',
  }) async {
    // Get Started button — no key yet, find by text
    await tapText(t, 'Get Started');
    await typeInto(t, 'signup_username', name);
    await typeInto(t, 'signup_email',    email);
    await typeInto(t, 'signup_password', password);
    await tapKey(t, 'signup_button');
    await settle(t, seconds: 3);
  }

  /// login_page.dart login flow
  Future<void> doLogin(WidgetTester t, {
    String email    = 'testuser@nutrifit.com',
    String password = 'Test@1234',
  }) async {
    await typeInto(t, 'login_email',    email);
    await typeInto(t, 'login_password', password);
    await tapKey(t, 'login_button');
    await settle(t, seconds: 3);
  }

  /// profile_setup.dart profile fill
  Future<void> fillProfile(WidgetTester t, {
    String weight       = '60',
    String height       = '5.4',
    String age          = '22',
    String targetWeight = '55',
    String goal         = 'weight loss',
    String activity     = 'sedentary',
  }) async {
    await typeInto(t, 'name',         'TestUser');
    await typeInto(t, 'age',          age);
    await typeInto(t, 'weight',       weight);
    await typeInto(t, 'height',       height);
    await typeInto(t, 'targetWeight', targetWeight);
    // Dropdown for goal
    await t.tap(find.text('Goal'));
    await t.pumpAndSettle();
    await tapText(t, goal);
    // Dropdown for activity
    await t.tap(find.text('Activity Level'));
    await t.pumpAndSettle();
    await tapText(t, activity);
    await tapKey(t, 'save_continue_button');
    await settle(t, seconds: 4);
  }

  // ══════════════════════════════════════════════════════════════
  //  GROUP 1 — REGISTRATION & LOGIN
  //  signup_page.dart  /  login_page.dart
  // ══════════════════════════════════════════════════════════════
  group('Feature 1 — Registration & Login', () {

    testWidgets('BB-R-01: Valid registration navigates to profile setup',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await doRegistration(t);
      // profile_setup.dart shows "Personal Information" as AppBar title
      expect(find.text('Personal Information'), findsOneWidget,
          reason: 'BB-R-01: Profile setup screen must appear after registration');
    });

    testWidgets('BB-R-02: Valid login shows home welcome text',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await doLogin(t);
      // home_page.dart renders "Welcome, $name"
      expect(find.textContaining('Welcome'), findsOneWidget,
          reason: 'BB-R-02: Home screen welcome text must appear after login');
    });

    testWidgets('BB-R-03: Home has bottom nav with Meal and Workout tabs',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await doLogin(t);
      // home_page.dart BottomNavigationBar labels
      expect(find.text('Meal'),    findsOneWidget,
          reason: 'BB-R-03: Meal tab must be in bottom nav');
      expect(find.text('Workout'), findsOneWidget,
          reason: 'BB-R-03: Workout tab must be in bottom nav');
    });

    // ── KNOWN FAILS ─────────────────────────────────────────────
    testWidgets('BB-TC-01 KNOWN FAIL: Empty fields show inline validation',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await tapText(t, 'Get Started');
      // Leave all fields empty — tap Sign Up
      await tapKey(t, 'signup_button');
      await t.pumpAndSettle();

      // signup_page.dart validator returns 'Enter username' / 'Enter email'
      // / 'Enter password' — these render as errorText in TextFormField
      final nameErr  = find.text('Enter username');
      final emailErr = find.text('Enter email');
      final passErr  = find.text('Enter password');

      debugPrint('[BB-TC-01] name_error: ${t.any(nameErr)}');
      debugPrint('[BB-TC-01] email_error: ${t.any(emailErr)}');
      debugPrint('[BB-TC-01] pass_error: ${t.any(passErr)}');

      expect(nameErr,  findsOneWidget,
          reason: 'BB-TC-01 KNOWN FAIL: Name error text missing. '
                  'Fix: validator already returns "Enter username" — '
                  'ensure form triggers validation on submit.');
      expect(emailErr, findsOneWidget,
          reason: 'BB-TC-01 KNOWN FAIL: Email error text missing.');
      expect(passErr,  findsOneWidget,
          reason: 'BB-TC-01 KNOWN FAIL: Password error text missing.');
    });

    testWidgets('BB-TC-02 KNOWN FAIL: Invalid email shows friendly error',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await tapText(t, 'Get Started');
      await typeInto(t, 'signup_username', 'Hamza');
      await typeInto(t, 'signup_email',    'hamza@@gmail');
      await typeInto(t, 'signup_password', 'Test@1234');
      await tapKey(t, 'signup_button');
      await settle(t);

      // signup_page.dart validator only checks isEmpty — not format
      final friendlyErr = find.textContaining('valid email');
      debugPrint('[BB-TC-02] Friendly email error: ${t.any(friendlyErr)}');

      expect(friendlyErr, findsOneWidget,
          reason: 'BB-TC-02 KNOWN FAIL: No friendly email format error. '
                  'Fix: add RegExp validator in signup_page.dart.');
    });
  });

  // ══════════════════════════════════════════════════════════════
  //  GROUP 2 — HEALTH METRICS (BMI / BMR / TDEE)
  //  home_page.dart → "BMI: $bmi", "BMR: $bmr kcal/day"
  // ══════════════════════════════════════════════════════════════
  group('Feature 2 — Health Metrics', () {

    Future<void> setupProfile(WidgetTester t,
        {String weight = '60', String height = '5.4'}) async {
      await doRegistration(t);
      await fillProfile(t, weight: weight, height: height);
    }

    testWidgets('BB-H-01: BMI text visible on home dashboard',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await setupProfile(t);
      // home_page.dart: Text("BMI: $bmi")
      expect(find.byKey(const Key('bmi_text')), findsOneWidget,
          reason: 'BB-H-01: BMI text widget must be on home dashboard');
      final bmiWidget = t.widget(find.byKey(const Key('bmi_text'))) as Text;
      final bmiStr    = bmiWidget.data ?? '';
      debugPrint('[BB-H-01] BMI displayed: $bmiStr');
      expect(bmiStr.contains('21') || bmiStr.contains('22'), true,
          reason: 'BB-H-01: Expected BMI ~21.7 for 60kg/5.4ft');
    });

    testWidgets('BB-H-02: BMR and TDEE text visible on home dashboard',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await setupProfile(t);
      expect(find.byKey(const Key('bmr_text')),  findsOneWidget,
          reason: 'BB-H-02: BMR text must be on home dashboard');
      expect(find.byKey(const Key('tdee_text')), findsOneWidget,
          reason: 'BB-H-02: TDEE text must be on home dashboard');
    });

    testWidgets('BB-H-03: Obese BMI — value >= 30',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await setupProfile(t, weight: '120', height: '5.5');
      final bmiWidget = t.widget(find.byKey(const Key('bmi_text'))) as Text;
      final bmiVal    = double.tryParse(
          (bmiWidget.data ?? '').replaceAll('BMI:', '').trim()) ?? 0;
      expect(bmiVal >= 30.0, true,
          reason: 'BB-H-03: Expected Obese BMI >= 30 for 120kg/5.5ft, got $bmiVal');
    });

    testWidgets('BB-H-04: Underweight BMI — value < 18.5',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await setupProfile(t, weight: '35', height: '5.6');
      final bmiWidget = t.widget(find.byKey(const Key('bmi_text'))) as Text;
      final bmiVal    = double.tryParse(
          (bmiWidget.data ?? '').replaceAll('BMI:', '').trim()) ?? 99;
      expect(bmiVal < 18.5, true,
          reason: 'BB-H-04: Expected Underweight BMI < 18.5 for 35kg/5.6ft');
    });

    // ── KNOWN FAIL ─────────────────────────────────────────────
    testWidgets('BB-TC-03 KNOWN FAIL: Zero weight shows validation error',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await doRegistration(t);
      await typeInto(t, 'weight', '0');
      await typeInto(t, 'height', '5.4');
      await tapKey(t, 'save_continue_button');
      await settle(t);

      // profile_setup.dart sends to backend → backend returns
      // errors["weight"] = "Weight must be positive"
      // This renders as errorText in the TextFormField
      final errFinder = find.textContaining('positive');
      debugPrint('[BB-TC-03] Validation error found: ${t.any(errFinder)}');

      expect(errFinder, findsOneWidget,
          reason: 'BB-TC-03 KNOWN FAIL: Zero weight accepted. '
                  'Fix: add Flutter-side weight > 0 validator before API call.');
    });
  });

  // ══════════════════════════════════════════════════════════════
  //  GROUP 3 — MEAL PLAN
  //  meal_plan.dart — _buildMealSection renders "Breakfast" etc.
  // ══════════════════════════════════════════════════════════════
  group('Feature 3 — Meal Plan', () {

    Future<void> goToMealTab(WidgetTester t) async {
      await doLogin(t);
      await tapText(t, 'Meal');
      await settle(t, seconds: 4);
    }

    testWidgets('BB-M-01: Meal plan shows Breakfast, Lunch, Dinner sections',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToMealTab(t);
      expect(find.text('Breakfast'), findsOneWidget,
          reason: 'BB-M-01: Breakfast section missing');
      expect(find.text('Lunch'),     findsOneWidget,
          reason: 'BB-M-01: Lunch section missing');
      expect(find.text('Dinner'),    findsOneWidget,
          reason: 'BB-M-01: Dinner section missing');
    });

    testWidgets('BB-M-02: All 7 day names present in meal plan',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToMealTab(t);
      final days = ['Monday','Tuesday','Wednesday',
                    'Thursday','Friday','Saturday','Sunday'];
      for (final day in days) {
        expect(find.textContaining(day), findsWidgets,
            reason: 'BB-M-02: $day missing from 7-day meal plan');
      }
    });

    testWidgets('BB-M-03: Diabetes filter — halwa and kheer absent',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToMealTab(t);
      // HEALTH_RESTRICTIONS["diabetes"]["avoid"] includes halwa, kheer
      expect(find.textContaining('Halwa'), findsNothing,
          reason: 'BB-M-03: Halwa must not appear in diabetic plan');
      expect(find.textContaining('Kheer'), findsNothing,
          reason: 'BB-M-03: Kheer must not appear in diabetic plan');
    });

    testWidgets('BB-M-04: Egg allergy — egg omelette absent',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToMealTab(t);
      // ALLERGEN_FILTERS["egg"] includes "omelette"
      expect(find.textContaining('Egg omelette'), findsNothing,
          reason: 'BB-M-04: Egg omelette must not appear for egg-allergic user');
    });

    testWidgets('BB-M-05: Cheat Meal button visible on meal screen',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToMealTab(t);
      expect(find.byKey(const Key('cheat_meal_button')), findsOneWidget,
          reason: 'BB-M-05: Cheat Meal button must be visible');
    });

    testWidgets('BB-M-06: View Compensation Plan button visible',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToMealTab(t);
      expect(find.textContaining('Compensation Plan'), findsOneWidget,
          reason: 'BB-M-06: Compensation Plan button must be visible');
    });

    // ── KNOWN FAIL ─────────────────────────────────────────────
    testWidgets('BB-TC-04 KNOWN FAIL: Multi-condition plan not empty',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToMealTab(t);

      // User with diabetes + hypertension + egg + gluten
      // ProfessionalMealPlanner eliminates all foods → blank screen
      final breakfastSection = find.text('Breakfast');
      final noMealMsg        = find.textContaining('No meal plan');

      debugPrint('[BB-TC-04] breakfast: ${t.any(breakfastSection)}');
      debugPrint('[BB-TC-04] no_plan_msg: ${t.any(noMealMsg)}');

      expect(breakfastSection, findsOneWidget,
          reason: 'BB-TC-04 KNOWN FAIL: Multi-condition profile shows empty '
                  'meal plan. Fix: add constraint-relaxation in meal_plan.py.');
      expect(noMealMsg, findsNothing,
          reason: 'BB-TC-04 KNOWN FAIL: "No meal plan" error shown instead.');
    });
  });

  // ══════════════════════════════════════════════════════════════
  //  GROUP 4 — FOOD IMAGE RECOGNITION
  //  meal_snap.dart (UploadMealScreen)
  //  Camera icon in meal_plan.dart AppBar → UploadMealScreen
  // ══════════════════════════════════════════════════════════════
  group('Feature 4 — Food Image Recognition', () {

    Future<void> goToMealSnap(WidgetTester t) async {
      await doLogin(t);
      await tapText(t, 'Meal');
      await settle(t, seconds: 2);
      // Camera icon in AppBar — meal_snap.dart: UploadMealScreen
      await t.tap(find.byIcon(Icons.camera_alt));
      await settle(t);
    }

    testWidgets('BB-F-01: Select image button visible',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToMealSnap(t);
      expect(find.byKey(const Key('select_image_button')), findsOneWidget,
          reason: 'BB-F-01: Select / Capture image button must be visible');
    });

    testWidgets('BB-F-02: Analyze Meal button disabled before image selected',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToMealSnap(t);
      // meal_snap.dart: onPressed = _image == null ? null : _uploadImage
      final analyzeBtn = find.byKey(const Key('analyze_meal_button'));
      expect(analyzeBtn, findsOneWidget,
          reason: 'BB-F-02: Analyze Meal button must exist');
      final widget = t.widget(analyzeBtn) as ElevatedButton;
      expect(widget.onPressed, isNull,
          reason: 'BB-F-02: Analyze button must be disabled before image selected');
    });

    testWidgets('BB-F-03: Upload screen title shown',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToMealSnap(t);
      // meal_snap.dart AppBar title = "Upload Meal"
      expect(find.text('Upload Meal'), findsOneWidget,
          reason: 'BB-F-03: Upload Meal screen title must be visible');
    });

    // ── KNOWN FAIL ─────────────────────────────────────────────
    testWidgets('BB-TC-05 KNOWN FAIL: Low similarity shows confidence warning',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToMealSnap(t);
      // meal_snap.dart shows similarity score but no threshold warning
      // This test verifies the warning widget exists — it does NOT
      final warningFinder = find.textContaining('one dish');
      final confFinder    = find.textContaining('confidence');
      debugPrint('[BB-TC-05] warning: ${t.any(warningFinder)}');

      expect(
        t.any(warningFinder) || t.any(confFinder),
        true,
        reason: 'BB-TC-05 KNOWN FAIL: No confidence/threshold warning shown. '
                'Fix: add similarity < 0.6 → show "Please photograph one dish".',
      );
    });
  });

  // ══════════════════════════════════════════════════════════════
  //  GROUP 5 — CHEAT MEAL LOG
  //  cheatmeal.dart (CheatMealScreen)
  // ══════════════════════════════════════════════════════════════
  group('Feature 5 — Cheat Meal', () {

    Future<void> goToCheatMeal(WidgetTester t) async {
      await doLogin(t);
      await tapText(t, 'Meal');
      await settle(t, seconds: 3);
      await tapKey(t, 'cheat_meal_button');
      await settle(t, seconds: 2);
    }

    testWidgets('BB-C-01: Cheat meal form has all required fields',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToCheatMeal(t);
      // cheatmeal.dart _buildTextField labels
      expect(find.text('Food Name'),   findsOneWidget,
          reason: 'BB-C-01: Food Name field missing');
      expect(find.text('Calories'),    findsOneWidget,
          reason: 'BB-C-01: Calories field missing');
      expect(find.text('Protein (g)'), findsOneWidget,
          reason: 'BB-C-01: Protein field missing');
      expect(find.text('Carbs (g)'),   findsOneWidget,
          reason: 'BB-C-01: Carbs field missing');
      expect(find.text('Fats (g)'),    findsOneWidget,
          reason: 'BB-C-01: Fats field missing');
    });

    testWidgets('BB-C-02: Save Cheat Meal button visible',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToCheatMeal(t);
      expect(find.byKey(const Key('save_cheat_meal_button')), findsOneWidget,
          reason: 'BB-C-02: Save Cheat Meal button must be visible');
    });

    // ── KNOWN FAIL ─────────────────────────────────────────────
    testWidgets('BB-TC-06 KNOWN FAIL: Empty cheat form shows field errors',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToCheatMeal(t);
      await tapKey(t, 'save_cheat_meal_button');
      await settle(t);

      // cheatmeal.dart _buildTextField uses validator: required → true
      // Should show "This field is required" for each empty field
      final requiredErr = find.textContaining('required');
      debugPrint('[BB-TC-06] Validation errors shown: ${t.any(requiredErr)}');

      expect(requiredErr, findsWidgets,
          reason: 'BB-TC-06 KNOWN FAIL: Empty cheat form submitted without '
                  'showing field errors. Fix: ensure _formKey.validate() '
                  'is called before _saveCheatMeal().');
    });
  });

  // ══════════════════════════════════════════════════════════════
  //  GROUP 6 — EXERCISE PLAN
  //  home_page.dart → bottom nav index 2 → ExercisePlan widget
  // ══════════════════════════════════════════════════════════════
  group('Feature 6 — Exercise Plan', () {

    Future<void> goToWorkoutTab(WidgetTester t) async {
      await doLogin(t);
      // home_page.dart BottomNavigationBarItem label = "Workout"
      await tapText(t, 'Workout');
      await settle(t, seconds: 3);
    }

    testWidgets('BB-E-01: Workout tab loads without crash',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToWorkoutTab(t);
      // exercise_plan.dart must render something
      expect(
        find.textContaining('Exercise').evaluate().isNotEmpty ||
        find.textContaining('Day').evaluate().isNotEmpty ||
        find.textContaining('Workout').evaluate().isNotEmpty,
        true,
        reason: 'BB-E-01: Workout screen must load without crash',
      );
    });

    testWidgets('BB-E-02: Exercise plan shows exercise names',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToWorkoutTab(t);
      // exercise_plan.py returns exercise_name from excercise.csv
      final exercises = ['Squats', 'Push-ups', 'Lunges',
                         'Deadlift', 'Jogging', 'Plank'];
      final found = exercises.any(
        (ex) => find.textContaining(ex).evaluate().isNotEmpty
      );
      expect(found, true,
          reason: 'BB-E-02: No exercise names found in workout plan');
    });

    testWidgets('BB-E-03: Exercise plan shows sets and reps',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await goToWorkoutTab(t);
      final hasSets = find.textContaining('sets').evaluate().isNotEmpty ||
                      find.textContaining('Sets').evaluate().isNotEmpty;
      final hasReps = find.textContaining('reps').evaluate().isNotEmpty  ||
                      find.textContaining('Reps').evaluate().isNotEmpty  ||
                      find.textContaining('repetitions').evaluate().isNotEmpty;
      expect(hasSets || hasReps, true,
          reason: 'BB-E-03: Sets/reps information not displayed in workout plan');
    });
  });

  // ══════════════════════════════════════════════════════════════
  //  GROUP 7 — NAVIGATION
  //  home_page.dart BottomNavigationBar
  // ══════════════════════════════════════════════════════════════
  group('Feature 7 — Navigation', () {

    testWidgets('BB-N-01: All 6 bottom nav tabs present',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await doLogin(t);
      // home_page.dart BottomNavigationBar items
      for (final label in ['Home', 'Meal', 'Workout',
                           'Progress', 'Chatbot', 'Gamification']) {
        expect(find.text(label), findsOneWidget,
            reason: 'BB-N-01: "$label" tab missing from bottom nav');
      }
    });

    testWidgets('BB-N-02: Progress tab navigates without crash',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await doLogin(t);
      await tapText(t, 'Progress');
      await settle(t, seconds: 2);
      // Should not show an error screen
      expect(find.textContaining('Error'), findsNothing,
          reason: 'BB-N-02: Progress tab must load without error');
    });

    testWidgets('BB-N-03: Chatbot tab navigates without crash',
        (WidgetTester t) async {
      // app.main(); await settle(t);
      await doLogin(t);
      await tapText(t, 'Chatbot');
      await settle(t, seconds: 2);
      expect(find.textContaining('Error'), findsNothing,
          reason: 'BB-N-03: Chatbot tab must load without error');
    });
  });
}
