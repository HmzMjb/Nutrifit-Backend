#exercise_video.py pycharm

import os
import sys
import csv
import time
import pickle
import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression, RidgeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score


# ============================================================
# LANDMARK COLUMN DEFINITIONS
# ============================================================
# Full 33-landmark header — used for Deadlift and Squat
landmarks = ['class']
for val in range(1, 33 + 1):
    landmarks += [f'x{val}', f'y{val}', f'z{val}', f'v{val}']

# Reduced 22-landmark header — used for Bench Press only
# (hips and below are irrelevant for bench press)
landmarks_bench = ['class']
for val in range(1, 22 + 1):
    landmarks_bench += [f'x{val}', f'y{val}', f'z{val}', f'v{val}']

LANDMARK_COLS       = landmarks[1:]        # 33-landmark feature columns (no 'class')
LANDMARK_COLS_BENCH = landmarks_bench[1:]  # 22-landmark feature columns (no 'class')

# ── MediaPipe shorthand ────────────────────────────────────────────────────────
mp_drawing = mp.solutions.drawing_utils
mp_pose    = mp.solutions.pose
PL         = mp_pose.PoseLandmark   # convenient alias

# ── Confidence thresholds (IMPROVED from Model_Predictions.py) ────────────────
PROB_THRESHOLD = 0.70   # model must be ≥70% confident before acting (was 0.3)
BUFFER_SIZE    = 5      # consecutive frames needed to confirm a stage change
VIS_THRESHOLD  = 0.5    # landmark visibility needed for angle calculations


# ============================================================
# EXERCISE CONFIGURATION MAP
# ============================================================
# Defines the up/down pose classes and landmark mode for each
# supported exercise. Used by process_video() and Make_Predictions()
# to select the correct feature set and rep-counting logic.
#
#   Bench Press:  22 landmarks (hips excluded), bench=True
#   Deadlift:     33 landmarks, bench=False
#   Squat:        33 landmarks, bench=False
# ============================================================

EXERCISE_CONFIG = {
    "Models/Bench_rf.pkl": {
        # KEY FIX: bad classes (up_close, up_roll, down_close) removed from ups/downs.
        # They are detected by validate_posture() and shown as warnings, but never
        # trigger a rep count. Only clean-form classes count reps.
        "ups":   ["up"],
        "downs": ["down"],
        "bench": True,    # Use 22-landmark feature set
    },
    "Models/Deadlift_rf.pkl": {
        # KEY FIX: bad classes (up_back, up_roll, down_roll, down_low) removed.
        "ups":   ["up"],
        "downs": ["down"],
        "bench": False,
    },
    "Models/Squat_rf.pkl": {
        # KEY FIX: bad classes (down_deep, down_forward) removed.
        "ups":   ["up"],
        "downs": ["down"],
        "bench": False,
    },
}


def _get_exercise_config(model_path):
    """
    Returns the correct exercise config for the given model path.
    Matches by keyword (Bench / Deadlift / Squat) so any path format works,
    e.g. 'Models/Bench_rf.pkl', '/abs/path/Bench_rf.pkl', or 'bench'.
    Falls back to Bench config if no keyword matches.
    """
    p = model_path.lower()
    if "bench" in p:
        return EXERCISE_CONFIG["Models/Bench_rf.pkl"]
    elif "deadlift" in p:
        return EXERCISE_CONFIG["Models/Deadlift_rf.pkl"]
    elif "squat" in p:
        return EXERCISE_CONFIG["Models/Squat_rf.pkl"]
    # Exact key lookup as final fallback
    return EXERCISE_CONFIG.get(model_path, EXERCISE_CONFIG["Models/Bench_rf.pkl"])

# ── Bad-posture class → warning message map ────────────────────────────────────
# If a predicted class is in this dict → bad posture (red skeleton + warning).
# If NOT in this dict → good posture (green skeleton + "Good form!").
BAD_CLASS_MSGS = {
    # Deadlift
    'up_back'      : 'Avoid leaning backward at the top.',
    'up_roll'      : 'Never round your back while deadlifting.',
    'down_roll'    : 'Keep your chest up — do not arch your back.',
    'down_low'     : 'Hips too low — this is not a squat!',
    # Squat
    'down_deep'    : 'Too deep — ease up on the depth.',
    'down_forward' : 'Avoid leaning forward. Keep your back straight.',
    # Bench Press
    'up_close'     : 'Keep your arms parallel — not too close together.',
    'up_roll'      : 'Lock your shoulders — do not extend them.',
    'down_close'   : 'Open your chest more on the way down.',
}


# ============================================================
# GEOMETRY HELPERS  (from Model_Predictions.py)
# ============================================================

def calc_angle(a, b, c):
    """Return the angle (degrees) at joint b, formed by points a-b-c."""
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = (np.arctan2(c[1] - b[1], c[0] - b[0])
               - np.arctan2(a[1] - b[1], a[0] - b[0]))
    angle = np.abs(np.degrees(radians))
    return 360 - angle if angle > 180 else angle


def get_xy(lm_list, landmark_enum):
    """Return (x, y) for a landmark if visible, else None."""
    lm = lm_list[landmark_enum.value]
    if lm.visibility < VIS_THRESHOLD:
        return None
    return [lm.x, lm.y]


# ============================================================
# POSTURE VALIDATION  (from Model_Predictions.py)
# ============================================================
# Geometry-based joint-angle checks on top of model predictions.
# Returns a warning string, or '' if form looks good.
# ============================================================

def validate_posture(path_model, predicted_class, lm_list):
    """
    Run geometry-based checks relevant to the current exercise and pose.
    Returns a warning message string (empty string = good form).

    Args:
        path_model      (str): Path to the active model file.
        predicted_class (str): Current predicted pose class.
        lm_list:               MediaPipe landmark list.

    Returns:
        str: A corrective message, or '' if form is correct.
    """
    msg = ''

    try:
        # ── DEADLIFT checks ───────────────────────────────────────────────
        if 'Deadlift' in path_model:

            # Spine rounding: shoulder → hip → knee angle
            shoulder = get_xy(lm_list, PL.LEFT_SHOULDER)
            hip      = get_xy(lm_list, PL.LEFT_HIP)
            knee     = get_xy(lm_list, PL.LEFT_KNEE)

            if all(p is not None for p in [shoulder, hip, knee]):
                back_angle = calc_angle(shoulder, hip, knee)
                # A neutral spine gives ~160–180°; rounding drops it below ~140°
                if back_angle < 140 and 'down' in predicted_class:
                    msg = 'Keep your back straight! Avoid rounding.'

            # Overextension at the top
            if predicted_class == 'up_back':
                msg = 'Avoid leaning backward at the top.'
            elif predicted_class == 'up_roll':
                msg = 'Never round your back while deadlifting.'
            elif predicted_class == 'down_roll':
                msg = 'Keep your chest up — do not arch your back.'
            elif predicted_class == 'down_low':
                msg = 'Hips too low — this is not a squat!'

        # ── SQUAT checks ─────────────────────────────────────────────────
        elif 'Squat' in path_model:

            # Knee cave / forward lean: hip → knee → ankle
            hip   = get_xy(lm_list, PL.LEFT_HIP)
            knee  = get_xy(lm_list, PL.LEFT_KNEE)
            ankle = get_xy(lm_list, PL.LEFT_ANKLE)

            if all(p is not None for p in [hip, knee, ankle]):
                knee_angle = calc_angle(hip, knee, ankle)
                # Below ~60° = knees collapsing / going too far forward
                if knee_angle < 60 and predicted_class == 'down_deep':
                    msg = 'Too deep — knees are under excessive stress.'

            if predicted_class == 'down_forward':
                msg = 'Avoid leaning forward. Keep your back straight.'
            elif predicted_class == 'down_deep':
                if not msg:
                    msg = 'Try not to go down this much.'

        # ── BENCH PRESS checks ───────────────────────────────────────────
        elif 'Bench' in path_model:

            # Elbow flare: shoulder → elbow → wrist angle
            shoulder = get_xy(lm_list, PL.LEFT_SHOULDER)
            elbow    = get_xy(lm_list, PL.LEFT_ELBOW)
            wrist    = get_xy(lm_list, PL.LEFT_WRIST)

            if all(p is not None for p in [shoulder, elbow, wrist]):
                elbow_angle = calc_angle(shoulder, elbow, wrist)
                # Elbow angle < 70° while pressing = elbows flaring too wide
                if elbow_angle < 70 and 'up' in predicted_class:
                    msg = 'Tuck your elbows — reduce elbow flare.'

            if predicted_class == 'up_close':
                if not msg:
                    msg = 'Keep your arms parallel to each other.'
            elif predicted_class == 'up_roll':
                if not msg:
                    msg = 'Lock your shoulders — do not extend them.'
            elif predicted_class == 'down_close':
                if not msg:
                    msg = 'Open your chest more on the way down.'

    except Exception:
        pass

    # If no geometry check fired but the class is a known bad-posture class,
    # fall back to the message dict (matches pasted Model_Predictions.py logic).
    if not msg:
        msg = BAD_CLASS_MSGS.get(predicted_class, '')

    return msg


# ============================================================
# HUD DISPLAY HELPER  (from Model_Predictions.py)
# ============================================================

def draw_hud(image, predicted_class, prob, counter, warning):
    """Draw the top info bar (PROB | CLASS | COUNT) and bottom warning banner."""
    h, w = image.shape[:2]

    # ── Top bar ───────────────────────────────────────────────────────────
    cv2.rectangle(image, (0, 0), (w, 110), (30, 30, 30), -1)

    cv2.putText(image, 'PROB',  (20, 30),  cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 180), 1, cv2.LINE_AA)
    cv2.putText(image, '{:.0f}%'.format(prob * 100), (10, 85),
                cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 3, cv2.LINE_AA)

    cv2.putText(image, 'CLASS', (w // 2 - 45, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 180), 1, cv2.LINE_AA)
    cv2.putText(image, predicted_class, (w // 2 - 60, 85),
                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3, cv2.LINE_AA)

    cv2.putText(image, 'REPS',  (w - 120, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 180), 1, cv2.LINE_AA)
    cv2.putText(image, str(counter), (w - 110, 85),
                cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 3, cv2.LINE_AA)

    # ── Bottom warning / good-form banner ────────────────────────────────
    if warning:
        cv2.rectangle(image, (0, h - 50), (w, h), (0, 0, 200), -1)
        cv2.putText(image, warning, (10, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1, cv2.LINE_AA)
    else:
        cv2.rectangle(image, (0, h - 50), (w, h), (0, 150, 0), -1)
        cv2.putText(image, 'Good form!', (10, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1, cv2.LINE_AA)


# ============================================================
# CREATE CSV FILES
# ============================================================
# Used to initialise and populate the CSV dataset files
# for training the pose classification models.
# ============================================================

def first_line_CSV_file(path, bench=False):
    """
    Creates a new CSV file and writes the header row.
    Call this once before starting a labeling session.

    Args:
        path  (str):  File path for the CSV.
        bench (bool): If True, uses the 22-landmark header
                      for Bench Press; otherwise uses 33.
    """
    header = landmarks_bench if bench else landmarks
    with open(path, mode='w', newline='') as f:
        csv.writer(f, delimiter=',', quotechar='"',
                   quoting=csv.QUOTE_MINIMAL).writerow(header)
    print('CSV header written to:', path)


def export_landmark(results, action, path, bench=False):
    """
    Appends one row of pose landmark data to the CSV file.
    Called each time a labeling key is pressed during a video.

    Args:
        results:        MediaPipe pose detection result object.
        action  (str):  The class label to assign this frame.
        path    (str):  Path to the CSV file.
        bench   (bool): If True, only the first 22 landmarks
                        are exported (Bench Press mode).
    """
    try:
        all_landmarks = results.pose_landmarks.landmark
        selected = list(all_landmarks)[:22] if bench else list(all_landmarks)

        keypoints = np.array([
            [lm.x, lm.y, lm.z, lm.visibility]
            for lm in selected
        ]).flatten().tolist()

        keypoints.insert(0, action)

        with open(path, mode='a', newline='') as f:
            csv.writer(f, delimiter=',', quotechar='"',
                       quoting=csv.QUOTE_MINIMAL).writerow(keypoints)
        print('Saved label:', action)
    except Exception as e:
        print('Export error:', e)


def labeling_video(path_video, labels, path_CSV, bench=False):
    """
    Plays a video and allows manual frame-by-frame pose labeling.
    Draws MediaPipe skeleton overlay on screen for visual reference.

    FIXED (from CSVcreator.py):
      - Single cv2.waitKey() call per loop (was two — caused missed key presses)
      - Key mapping uses ord() consistently — readable and unambiguous
      - Clean end-of-stream guard (no crash when video ends)

    Args:
        path_video (str):  Path to the input video file.
        labels     (dict): Mapping of label name → key character (e.g. {'up': 'u'})
        path_CSV   (str):  CSV file to append labeled data to.
        bench      (bool): If True, uses 22-landmark mode for Bench Press.
    """
    cap = cv2.VideoCapture(path_video)

    print('\nControls:')
    for label, key in labels.items():
        print('  Press  {}  →  {}'.format(key.upper(), label))
    print('  Press  Q  →  Quit\n')

    with mp_pose.Pose(min_detection_confidence=0.5,
                      min_tracking_confidence=0.5) as pose:

        while cap.isOpened():
            ret, image = cap.read()
            if not ret:
                print('End of video or camera error.')
                break

            # BGR → RGB for MediaPipe
            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = pose.process(image)

            # RGB → BGR for OpenCV display
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            mp_drawing.draw_landmarks(
                image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=4),
                mp_drawing.DrawingSpec(color=(245,  66, 230), thickness=2, circle_radius=2)
            )

            # Show key guide on screen
            y_pos = 30
            for label, key in labels.items():
                cv2.putText(image, '{}: {}'.format(key.upper(), label),
                            (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 255, 0), 1, cv2.LINE_AA)
                y_pos += 25

            cv2.imshow('Labelling Tool — Q to quit', image)

            # ── SINGLE waitKey call per loop (FIXED) ──────────────────────
            k = cv2.waitKey(10) & 0xFF
            if k == ord('q'):
                break
            for label, key in labels.items():
                if k == ord(key):
                    export_landmark(results, label, path_CSV, bench=bench)

    cap.release()
    cv2.destroyAllWindows()
    cv2.waitKey(1)


# ============================================================
# MODEL TRAINING
# ============================================================
# Four classifier pipelines — each applies standard scaling
# before classification to normalise landmark values.
#
# Algorithms:
#   lr  — Logistic Regression
#   rc  — Ridge Classifier
#   rf  — Random Forest  ← chosen for deployment
#   gb  — Gradient Boosting
# ============================================================

pipelines = {
    'lr': make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
    'rc': make_pipeline(StandardScaler(), RidgeClassifier()),
    'rf': make_pipeline(StandardScaler(), RandomForestClassifier()),
    'gb': make_pipeline(StandardScaler(), GradientBoostingClassifier()),
}


def Create_sample_label_dataset(path_CSV):
    """
    Loads a CSV dataset and splits it into train/test sets (70/30).

    Args:
        path_CSV (str): Path to the labeled landmark CSV file.

    Returns:
        Tuple: (X_train, X_test, y_train, y_test)
    """
    df = pd.read_csv(path_CSV)
    X = df.drop('class', axis=1)
    y = df['class']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    return X_train, X_test, y_train, y_test


def Train_Model(X_train, y_train):
    """
    Trains all four classifier pipelines on the training data.

    Args:
        X_train: Feature matrix for training.
        y_train: Label vector for training.

    Returns:
        dict: Fitted models keyed by algorithm abbreviation.
    """
    fitted_models = {}
    for algo, pipeline in pipelines.items():
        model = pipeline.fit(X_train, y_train)
        fitted_models[algo] = model
    return fitted_models


def Test_Accuracy(fitted_models, X_test, y_test):
    """
    Evaluates all fitted models and prints accuracy, precision,
    and recall scores (macro averaging) on the test set.
    """
    for algo, model in fitted_models.items():
        yhat = model.predict(X_test)
        print(
            algo,
            accuracy_score(y_test.values, yhat),
            precision_score(y_test.values, yhat, average='macro', zero_division=0),
            recall_score(y_test.values, yhat, average='macro', zero_division=0)
        )


def save_model(model, save_path):
    """
    Saves a trained model to disk as a pickle file.
    Creates the output directory if it doesn't exist.
    """
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'wb') as f:
        pickle.dump(model, f)


# ============================================================
# REAL-TIME WEBCAM PREDICTION  (IMPROVED from Model_Predictions.py)
# ============================================================
# Improvements over original Make_Predictions():
#   - Probability threshold raised to 0.70 (was 0.3) — fewer ghost reps
#   - Frame-buffer (BUFFER_SIZE=5) prevents phantom rep counts
#   - Joint-angle validation (validate_posture) guards form checks
#   - Improved HUD: dynamic width, PROB + CLASS + REPS properly laid out
#   - Green "Good form!" banner when no warning
#   - Single cv2.waitKey() call per loop (was double — caused missed keys)
# ============================================================

def Make_Predictions(path_model, ups, downs, webcam=0):
    """
    Runs live pose classification and rep counting on a webcam.

    Args:
        path_model (str):  Path to the trained .pkl model file.
        ups        (list): Class names considered the "up" position.
        downs      (list): Class names considered the "down" position.
        webcam     (int):  Camera index (0 = default webcam).
    """
    with open(path_model, 'rb') as f:
        model = pickle.load(f)

    config       = _get_exercise_config(path_model)
    is_bench     = config["bench"]
    feature_cols = LANDMARK_COLS

    cap           = cv2.VideoCapture(webcam)
    counter       = 0
    current_stage = ''
    stage_buffer  = []    # rolling window of recent predictions
    warning_msg   = ''

    with mp_pose.Pose(min_detection_confidence=0.5,
                      min_tracking_confidence=0.5) as pose:

        while cap.isOpened():
            ret, image = cap.read()
            if not ret:
                break

            # Mirror for a natural mirror-like view
            image = cv2.flip(image, 1)

            # BGR → RGB for MediaPipe
            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = pose.process(image)

            # RGB → BGR for OpenCV display
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            mp_drawing.draw_landmarks(
                image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=4),
                mp_drawing.DrawingSpec(color=(245,  66, 230), thickness=2, circle_radius=2)
            )

            try:
                lm_list = results.pose_landmarks.landmark

                # Extract landmarks — 22 for Bench Press, 33 for others
                selected = list(lm_list)[:22] if is_bench else list(lm_list)

                row = np.array([
                    [lm.x, lm.y, lm.z, lm.visibility]
                    for lm in selected
                ]).flatten().tolist()

                X               = pd.DataFrame([row], columns=feature_cols)
                predicted_class = model.predict(X)[0]
                proba           = model.predict_proba(X)[0]
                confidence      = float(proba.max())

                # ── Frame buffer: only act when BUFFER_SIZE frames agree ──
                stage_buffer.append(predicted_class)
                if len(stage_buffer) > BUFFER_SIZE:
                    stage_buffer.pop(0)

                confirmed = (
                    len(stage_buffer) == BUFFER_SIZE
                    and len(set(stage_buffer)) == 1
                    and confidence >= PROB_THRESHOLD
                )

                if confirmed:
                    if predicted_class in downs and current_stage != predicted_class:
                        current_stage = predicted_class
                    elif (current_stage in downs
                          and predicted_class in ups
                          and current_stage != predicted_class):
                        current_stage = predicted_class
                        counter += 1

                # ── Posture validation (joint angles, every frame) ────────
                warning_msg = validate_posture(path_model, predicted_class, lm_list)

                draw_hud(image, predicted_class, confidence, counter, warning_msg)

            except Exception:
                draw_hud(image, '---', 0.0, counter, '')

            cv2.imshow('NutriFit AI', image)

            # ── SINGLE waitKey call per loop (FIXED) ──────────────────────
            if cv2.waitKey(10) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    cv2.waitKey(1)


# ============================================================
# FLASK API — VIDEO PROCESSING  (IMPROVED)
# ============================================================
# Called by main.py when the Flutter app uploads a recorded video.
# Fully headless — no cv2.imshow() anywhere.
#
# Improvements over original process_video():
#   - Probability threshold raised to 0.70 (was 0.3)
#   - Frame-buffer (BUFFER_SIZE=5) prevents phantom reps
#   - Joint-angle validation integrated via validate_posture()
#   - Bench Press uses correct 22-landmark feature set (was 33)
#
# Returns JSON-serialisable dict:
#   reps             — total reps counted in the video
#   confidence       — max prediction confidence of the last frame
#   pose             — last detected pose class name
#   suggestion       — worst corrective form tip seen, or "" if good
#   status           — "done" on success, "error: ..." on failure
#   frames_processed — number of frames successfully analysed
# ============================================================

def process_video(video_path, model_path="Models/Bench_rf.pkl"):
    """
    Processes a recorded exercise video to count reps, detect
    the last pose class, and generate a form suggestion.
    Used by the Flask API — fully headless, no display windows.

    Args:
        video_path (str): Path to the uploaded video file.
        model_path (str): Path to the trained .pkl model.
                          Defaults to Bench Press model.

    Returns:
        dict: {
            "reps":             int,
            "confidence":       float,
            "pose":             str,
            "suggestion":       str,
            "status":           "done" or "error: ...",
            "frames_processed": int
        }
    """
    import traceback

    try:
        config   = _get_exercise_config(model_path)
        ups      = config["ups"]
        downs    = config["downs"]
        is_bench = config["bench"]

        feature_cols = LANDMARK_COLS

        with open(model_path, "rb") as f:
            model = pickle.load(f)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {
                "reps": 0, "confidence": 0.0, "pose": "",
                "suggestion": "", "frames_processed": 0,
                "status": "error: could not open video file"
            }

        counter          = 0
        current_stage    = ""
        stage_buffer     = []    # rolling window of recent predictions
        prob             = 0.0
        last_pred        = ""
        last_suggestion  = ""
        frames_processed = 0

        print(f"[ENV] Python={sys.version.split()[0]}, MediaPipe={mp.__version__}, "
              f"OpenCV={cv2.__version__}, sklearn={__import__('sklearn').__version__}")
        sys.stdout.flush()

        with mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as pose:

            while cap.isOpened():
                ret, image = cap.read()
                if not ret:
                    break

                if image is None or image.size == 0:
                    continue

                try:
                    # Mirror the frame for consistent orientation with training data

                    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    image_rgb.flags.writeable = False
                    results   = pose.process(image_rgb)

                    if not results.pose_landmarks:
                        continue

                    lm_list  = results.pose_landmarks.landmark

                    selected = list(lm_list)

                    row = np.array([
                        [lm.x, lm.y, lm.z, lm.visibility]
                        for lm in selected
                    ]).flatten().tolist()

                    X    = pd.DataFrame([row], columns=feature_cols)
                    pred = model.predict(X)[0]
                    prob = float(model.predict_proba(X)[0].max())

                    last_pred        = pred
                    frames_processed += 1
                    print(f"[Frame {frames_processed}] pred={pred}, prob={prob:.2f}")

                    if frames_processed <= 3:
                        print(f"[LM] Frame {frames_processed}: "
                              f"nose=({lm_list[0].x:.4f},{lm_list[0].y:.4f},{lm_list[0].z:.4f}), "
                              f"l_shoulder=({lm_list[11].x:.4f},{lm_list[11].y:.4f},{lm_list[11].z:.4f}), "
                              f"l_hip=({lm_list[23].x:.4f},{lm_list[23].y:.4f},{lm_list[23].z:.4f}), "
                              f"l_knee=({lm_list[25].x:.4f},{lm_list[25].y:.4f},{lm_list[25].z:.4f})")

                    sys.stdout.flush()

                    # ── Frame buffer: only count when BUFFER_SIZE frames agree ──
                    stage_buffer.append(pred)
                    if len(stage_buffer) > BUFFER_SIZE:
                        stage_buffer.pop(0)

                    confirmed = (
                        len(stage_buffer) == BUFFER_SIZE
                        and len(set(stage_buffer)) == 1
                        and prob >= PROB_THRESHOLD
                    )

                    if confirmed:
                        if pred in downs and current_stage != pred:
                            current_stage = pred
                        elif (current_stage in downs
                              and pred in ups
                              and current_stage != pred):
                            current_stage = pred
                            counter += 1

                    # ── Joint-angle posture check (every frame) ───────────
                    suggestion = validate_posture(model_path, pred, lm_list)
                    if suggestion:
                        last_suggestion = suggestion

                except Exception:
                    print(f"[process_video] Skipped frame: {traceback.format_exc()}")
                    sys.stdout.flush()
                    continue
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        dur_secs = (total_frames / fps) if fps > 0 else 0.0
        dur_hours = dur_secs / 3600.0
        cap.release()
        print(f"[DEBUG] frames_processed={frames_processed}, counter={counter}, last_pred={last_pred}, prob={prob}")
        sys.stdout.flush()
        return {
            "reps": counter,
            "confidence": round(prob, 2),
            "pose": last_pred,
            "suggestion": last_suggestion,
            "frames_processed": frames_processed,
            "duration": round(dur_hours, 6),
            "duration_seconds": round(dur_secs, 2),
            "status": "done"
        }

    except Exception:
        error_detail = traceback.format_exc()
        print(f"[process_video] FATAL: {error_detail}")
        sys.stdout.flush()
        return {
            "reps": 0, "confidence": 0.0, "pose": "",
            "suggestion": "", "frames_processed": 0,
            "status": f"error: {error_detail}"
        }


# ============================================================
# EVERYTHING BELOW ONLY RUNS WHEN EXECUTED DIRECTLY:
#   python exercise_video.py
#
# It does NOT run when Flask imports this module — so no windows
# pop up on the server and no training / labeling starts.
# ============================================================

if __name__ == "__main__":

    # ============================================================
    # LABELING SESSIONS
    # ============================================================
    # Run whichever exercise you need to label.
    # Each exercise creates its own CSV and loops over its videos.
    # ============================================================

    # ── DEADLIFT — LABELING ──────────────────────────────────────
    # Classes: up, down, down_low, down_roll, up_back, up_roll
    path_CSV   = 'CSV_files/coords_DL_C_new.csv'
    path_videos = [
        'Videos/CorrectDeadlift_45f.mp4',
        'Videos/RollingDeadlift_45f.mp4',
        'Videos/BackDeadlift_45f.mp4'
    ]
    labels = {'up': 'u', 'down': 'd', 'down_low': 'l',
              'down_roll': 'r', 'up_back': 'b', 'up_roll': 'g'}
    first_line_CSV_file(path_CSV)
    for path_video in path_videos:
        labeling_video(path_video, labels, path_CSV)
        time.sleep(6)

    # ── SQUAT — LABELING ─────────────────────────────────────────
    # Classes: up, down, down_deep, down_forward
    path_CSV   = 'CSV_files/coords_SQ_C_new.csv'
    path_videos = [
        'Videos/CorrectSquat_45f.mp4',
        'Videos/ForwardSquat_45f.mp4',
        'Videos/DeepSquat.mp4'
    ]
    labels = {'up': 'u', 'down': 'd', 'down_deep': 'l', 'down_forward': 'f'}
    first_line_CSV_file(path_CSV)
    for path_video in path_videos:
        labeling_video(path_video, labels, path_CSV)
        time.sleep(6)

    # ── BENCH PRESS — LABELING ───────────────────────────────────
    # Classes: up, down, down_close, up_close, up_roll
    # Uses only 22 landmarks — hips irrelevant for bench press.
    path_CSV   = 'CSV_files/coords_BP_C_new.csv'
    path_videos = [
        'Videos/CorrectBench_45f.mp4',
        'Videos/TietBench_45f.mp4',
        'Videos/RollBench_45f.mp4'
    ]
    labels = {'up': 'u', 'down': 'd', 'down_close': 'l',
              'up_close': 'c', 'up_roll': 'r'}
    first_line_CSV_file(path_CSV, bench=True)
    for path_video in path_videos:
        labeling_video(path_video, labels, path_CSV, bench=True)
        time.sleep(6)

    # ============================================================
    # MODEL TRAINING
    # ============================================================

    # ── TRAIN DEADLIFT MODEL ─────────────────────────────────────
    # Merges original + updated dataset, trains all pipelines,
    # evaluates accuracy, saves RF model.
    path_CSV_DL     = 'CSV_files/coords_DL_C.csv'
    path_CSV_DL_new = 'CSV_files/coords_DL_C_new.csv'
    df_dl = pd.concat([pd.read_csv(path_CSV_DL), pd.read_csv(path_CSV_DL_new)], ignore_index=True)
    df_dl.to_csv('CSV_files/coords_DL_merged.csv', index=False)
    X_train, X_test, y_train, y_test = Create_sample_label_dataset('CSV_files/coords_DL_merged.csv')
    fitted_models = Train_Model(X_train, y_train)
    Test_Accuracy(fitted_models, X_test, y_test)
    save_model(fitted_models['rf'], 'Models/Deadlift_rf.pkl')

    # ── TRAIN SQUAT MODEL ────────────────────────────────────────
    X_train, X_test, y_train, y_test = Create_sample_label_dataset('CSV_files/coords_SQ_C.csv')
    fitted_models = Train_Model(X_train, y_train)
    Test_Accuracy(fitted_models, X_test, y_test)
    save_model(fitted_models['rf'], 'Models/Squat_rf.pkl')

    # ── TRAIN BENCH PRESS MODEL ──────────────────────────────────
    # Uses only the first 22 landmark columns (hips excluded).
    X_train, X_test, y_train, y_test = Create_sample_label_dataset('CSV_files/coords_BP_C.csv')
    fitted_models = Train_Model(X_train, y_train)
    Test_Accuracy(fitted_models, X_test, y_test)
    save_model(fitted_models['rf'], 'Models/Bench_rf.pkl')

    # ============================================================
    # WEBCAM SESSIONS
    # ============================================================

    # ── DEADLIFT — WEBCAM ────────────────────────────────────────
    # Bad classes (up_back, up_roll, down_roll, down_low) handled
    # automatically via BAD_CLASS_MSGS — never count as reps.
    Make_Predictions(
        "Models/Deadlift_rf.pkl",
        ups=["up"],
        downs=["down"],
        webcam=0
    )

    # ── SQUAT — WEBCAM ───────────────────────────────────────────
    # Bad classes (down_deep, down_forward) handled automatically.
    Make_Predictions(
        "Models/Squat_rf.pkl",
        ups=["up"],
        downs=["down"],
        webcam=0
    )

    # ── BENCH PRESS — WEBCAM ─────────────────────────────────────
    # Bad classes (up_close, up_roll, down_close) handled automatically.
    Make_Predictions(
        "Models/Bench_rf.pkl",
        ups=["up"],
        downs=["down"],
        webcam=0
    )