import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import hashlib
import time

class exercise_plan:
    def __init__(self, csv_path='excercise.csv'):
        # Load exercise data
        self.exercise_df = pd.read_csv(csv_path)

        # Define feature types
        self.categorical_features = ['muscle_group', 'type', 'intensity']
        self.numerical_features = ['sets', 'repetitions', 'duration']

        # Encode categorical features
        self.encoder = OneHotEncoder()
        self.X_cat = self.encoder.fit_transform(self.exercise_df[self.categorical_features])

        # Scale numerical features
        self.scaler = StandardScaler()
        self.X_num = self.scaler.fit_transform(self.exercise_df[self.numerical_features])

        # Combine final feature matrix
        self.X_final = np.hstack([self.X_cat.toarray(), self.X_num])

    @staticmethod
    def map_activity_level(activity_level):
        activity_level = activity_level.lower()
        if activity_level in ['sedentary', 'lightly active']:
            return 'beginner'
        elif activity_level in ['moderately active', 'very active', 'extra active']:
            return 'advanced'
        return 'beginner'

    def adjust_exercise(self, row, activity, target_goal, timeline_weeks):
        sets, reps, duration = row['sets'], row['repetitions'], row['duration']
        activity = self.map_activity_level(activity)

        # Adjust based on activity level
        if activity == 'beginner':
            sets *= 0.8
            reps *= 0.8
            duration *= 0.8
        elif activity == 'advanced':
            sets *= 1.2
            reps *= 1.2
            duration *= 1.2

        # Adjust based on target goal
        target_goal = target_goal.lower()
        if target_goal in ['weight loss', 'lose weight', 'fat loss', 'weight lose']:
            duration *= 1.2
        elif target_goal in ['weight gain', 'gain weight', 'muscle gain']:
            reps *= 1.2

        # Adjust based on timeline
        if timeline_weeks <= 4:
            sets *= 1.1
            reps *= 1.1
            duration *= 1.1
        elif 5 <= timeline_weeks <= 8:
            sets *= 1.05
            reps *= 1.05
            duration *= 1.05

        return pd.Series([round(sets), round(reps), round(duration)])

    def generate_exercise_plan(self, user_profile, days=7):
        goal = user_profile['target_goal'].lower()
        activity = user_profile['activity_level'].lower()
        timeline = user_profile['timeline_weeks']

        # Filter exercises
        filtered_ex = self.exercise_df[self.exercise_df['target_goal'].str.lower() == goal].copy()
        if filtered_ex.empty:
            return {"error": f"No exercises found for goal '{goal}'. Please update your goal or try a different one."}

        # Adjust exercises
        filtered_ex[['sets', 'repetitions', 'duration']] = filtered_ex.apply(
            lambda row: self.adjust_exercise(row, activity, goal, timeline), axis=1
        )

        # Deterministic shuffle
        user_hash = int(hashlib.md5((str(user_profile) + str(time.time())).encode()).hexdigest(), 16) % (2**32)
        filtered_ex = filtered_ex.sample(frac=1, random_state=user_hash).reset_index(drop=True)

        # Mandatory exercises har din
        mandatory_names = ['Bench Press', 'Squats', 'Deadlift']
        mandatory_df = self.exercise_df[
            self.exercise_df['exercise_name'].isin(mandatory_names)
        ].copy()

        mandatory_df[['sets', 'repetitions', 'duration']] = mandatory_df.apply(
            lambda row: self.adjust_exercise(row, activity, goal, timeline), axis=1
        )

        mandatory_records = mandatory_df[['exercise_name', 'sets', 'repetitions', 'duration']].to_dict(orient='records')

        # Filtered list se mandatory exercises hata do
        filtered_ex = filtered_ex[~filtered_ex['exercise_name'].isin(mandatory_names)].reset_index(drop=True)

        # Har din 2 normal exercises (1 mandatory + 2 normal = 3 total)
        exercises_per_day = 2
        daily_plan = {}
        for day in range(1, days + 1):
            start_idx = (day - 1) * exercises_per_day
            end_idx = start_idx + exercises_per_day
            day_ex = filtered_ex.iloc[start_idx:end_idx]

            # Agar exercises khatam ho jayein to wapas start se lo
            if len(day_ex) < exercises_per_day:
                day_ex = filtered_ex.iloc[:exercises_per_day]
            one_mandatory = mandatory_records[(day - 1) % len(mandatory_records)]

            day_records = [one_mandatory] + day_ex[['exercise_name', 'sets', 'repetitions', 'duration']].to_dict(
                orient='records')

            daily_plan[f'Day {day}'] = day_records
        return daily_plan


# Create a single instance to reuse
planner = exercise_plan()


# Route-style function similar to profile_setup_route
def exercise_plan_route(user_data):

    try:
        if not user_data:
            return {"status": "error", "message": "No user profile sent"}

        user_profile = {
            'target_goal': user_data.get("goal", "").lower(),
            'activity_level': user_data.get("activitylevel", "").lower(),
            'timeline_weeks': int(user_data.get("timeline_weeks", 4))
        }

        # Map activity level
        user_profile['activity_level'] = planner.map_activity_level(user_profile['activity_level'])

        # Generate exercise plan
        plan = planner.generate_exercise_plan(user_profile)

        if not plan or 'error' in plan:
            return {"status": "error", "message": plan.get('error', 'Failed to generate exercise plan')}

        return {"status": "success", "message": "Exercise plan generated successfully", "plan": plan}

    except Exception as e:
        return {"status": "error", "message": str(e)}
