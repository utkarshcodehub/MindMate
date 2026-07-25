"""
seed_demo.py

Creates a demo user with 21 days of realistic check-in history so the
dashboard, trend engine, and Wellbeing Agent all have data to work with
IMMEDIATELY — no waiting 10+ days of real logging.

The pattern seeded: two stable weeks, then a gentle decline in mood and
sleep over the last 7 days — the classic early-burnout shape. This gives
the agent something meaningful to find when you ask "how am I doing?"

Usage (from the project root, with your .env in place):
    python data/seed_demo.py

It prints a user_id at the end. To use it in the frontend, open the app,
press F12 → Console, and run (replace <ID>):
    localStorage.setItem('wb_user_id', '<ID>'); location.reload()

Re-runnable: creates a fresh demo user each time.
"""

import sys
import uuid
import random
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from api import db  # noqa: E402

random.seed()  # different demo user each run

DAYS = 21


def seeded_value(base, drift, noise, lo, hi, as_int=True):
    v = base + drift + random.gauss(0, noise)
    v = max(lo, min(hi, v))
    return int(round(v)) if as_int else round(v, 1)


def main():
    user_id = str(uuid.uuid4())
    print(f"Creating demo user {user_id} ...")

    db.create_user(
        user_id=user_id,
        phq2_score=2,
        gad2_score=2,
        pss4_score=6,
        overall_risk="low",
        raw_responses={"demo": True},
    )

    today = date.today()
    for i in range(DAYS, 0, -1):
        d = today - timedelta(days=i)
        # Last 7 days: gentle decline in mood/sleep, stress creeping up
        decline_days = max(0, 7 - i)          # 0 until the final week
        mood_drift = -0.25 * decline_days      # mood slides down
        sleep_drift = -0.35 * decline_days     # sleep shortens
        stress_drift = 0.45 * decline_days     # stress rises

        db.insert_daily_log(
            user_id=user_id,
            log_date=d,
            mood=seeded_value(4.2, mood_drift, 0.4, 1, 5),
            sleep_hours=seeded_value(7.5, sleep_drift, 0.5, 3, 10, as_int=False),
            sleep_quality=seeded_value(4.0, mood_drift, 0.5, 1, 5),
            study_hours=seeded_value(4.5, 0.15 * decline_days, 0.8, 0, 12, as_int=False),
            stress=seeded_value(4.0, stress_drift, 0.7, 1, 10),
            free_text=None,
        )
        print(f"  logged {d}")

    print("\nDone. 21 days of history seeded.")
    print("=" * 60)
    print(f"DEMO USER ID: {user_id}")
    print("=" * 60)
    print(
        "\nTo use it in the app: open the frontend, press F12 -> Console, run:\n"
        f"  localStorage.setItem('wb_user_id', '{user_id}'); location.reload()\n"
        "\nYou'll land on the daily-log page. Submit today's log once, and\n"
        "the dashboard + Wellbeing Agent will have three weeks of data."
    )


if __name__ == "__main__":
    main()
