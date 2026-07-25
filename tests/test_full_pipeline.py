import sys
sys.path.insert(0, "/home/claude/student_wellbeing/engine")

import pandas as pd
from engine.flag_decision import evaluate_day, UserTrendState

def build_df(user_id, mood, sleep_hours, sleep_quality, study_hours, stress, start="2026-01-01"):
    n = len(mood)
    dates = pd.date_range(start=start, periods=n, freq="D")
    return pd.DataFrame({
        "user_id": [user_id] * n,
        "log_date": dates,
        "mood": mood,
        "sleep_hours": sleep_hours,
        "sleep_quality": sleep_quality,
        "study_hours": study_hours,
        "stress": stress,
    }), dates


def run_scenario(name, df, dates, start_eval_day=13):
    print(f"\n{'='*70}\nSCENARIO: {name}\n{'='*70}")
    state = UserTrendState(user_id=df['user_id'].iloc[0])
    for i in range(start_eval_day, len(dates)):
        result = evaluate_day(df, state, dates[i])
        print(f"Day {i+1:>2} ({dates[i].date()}): {result.flag_type:<12} -- {result.reason}")


# ---------------------------------------------------------------------
# SCENARIO 1: Genuine mood decline (no workload spike to explain it)
# ---------------------------------------------------------------------
n_stable = 14
n_decline = 8
mood_1 = [4,3,4,4,3,4,4,3,3,4,4,3,4,4] + [3,2,2,2,1,2,1,1]
sleep_1 = [7.5]*n_stable + [7.5,6.5,6,6,5.5,5.5,5,5]
sleep_q_1 = [4]*n_stable + [3,3,2,2,2,2,2,1]
study_1 = [4.0]*n_stable + [4.0,4.0,3.5,3.5,3.0,3.0,3.0,2.5]  # flat/declining, NOT spiking
stress_1 = [4]*n_stable + [4,5,5,5,5,6,6,6]

df1, dates1 = build_df("user_decline", mood_1, sleep_1, sleep_q_1, study_1, stress_1)
run_scenario("Genuine mood+sleep decline (no exam explanation)", df1, dates1)

# ---------------------------------------------------------------------
# SCENARIO 2: Exam week -- stress up, sleep down, study hours UP
# Mood stays roughly stable. This should be suppressed.
# ---------------------------------------------------------------------
mood_2 = [4,3,4,4,3,4,4,3,3,4,4,3,4,4] + [3,4,3,4,3,4,3,4]  # stays normal range
sleep_2 = [7.5]*n_stable + [6.5,6,6,5.5,5.5,5,5,5.5]
sleep_q_2 = [4]*n_stable + [3,3,3,3,3,3,3,3]
study_2 = [4.0]*n_stable + [6.0,6.5,7.0,7.5,7.5,8.0,8.0,7.5]  # clearly spiking -- exam prep
stress_2 = [4]*n_stable + [5,6,6,7,7,7,7,6]

df2, dates2 = build_df("user_examweek", mood_2, sleep_2, sleep_q_2, study_2, stress_2)
run_scenario("Exam week (workload spike explains the stress)", df2, dates2)
