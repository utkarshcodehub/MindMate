"""
demo_seed.py — one-command demo data for the Student Wellbeing Agent.

Creates a demo student whose data follows the classic burnout shape:
  * Days 1-14 : stable baseline (good mood, good sleep, normal stress)
  * Days 15-24: gradual decline — mood and sleep slide together,
                stress climbs — exactly the pattern the engine is
                built to catch.

Every log is submitted through the real API (POST /api/log), so the
trend engine evaluates each day exactly as it would in production and
you can watch the flags appear: none -> soft_nudge -> hard_flag.

Afterwards (if you pass your automation secret) it runs the daily
sweep, which will send this user an automated wellbeing nudge.

USAGE (backend must be running on localhost:8000):

    pip install requests
    python demo_seed.py                         # seed only
    python demo_seed.py --sweep YOUR_SECRET     # seed + run automation

Then follow the printed instructions to open the demo user in the UI.
"""

import argparse
import random
import sys
from datetime import date, timedelta

try:
    import requests
except ImportError:
    sys.exit("Please run:  pip install requests")

BASE = "http://localhost:8000/api"
DAYS_TOTAL = 24
DECLINE_START = 14  # day index where the slide begins

random.seed(42)  # reproducible demo


def n(x, sd):  # small noise so data looks human
    return round(x + random.gauss(0, sd), 1)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", metavar="SECRET", default=None,
                    help="Also trigger the daily automation sweep with this secret")
    ap.add_argument("--base", default=BASE, help="API base (default localhost:8000/api)")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    # ------------------------------------------------------------------
    # 1. Onboard a demo user (healthy answers, item 9 = 0)
    # ------------------------------------------------------------------
    print("1) Onboarding demo user…")
    r = requests.post(f"{base}/onboard", json={
        "phq2_q1": 1, "phq2_q2": 1,
        "gad2_q1": 1, "gad2_q2": 1,
        "pss4_q2": 1, "pss4_q4": 2, "pss4_q5": 2, "pss4_q10": 1,
        "item9_response": 0,
    }, timeout=30)
    r.raise_for_status()
    user_id = r.json()["user_id"]
    print(f"   demo user_id = {user_id}\n")

    # ------------------------------------------------------------------
    # 2. Backfill 24 days of logs through the real engine
    # ------------------------------------------------------------------
    print("2) Submitting 24 days of check-ins (watch the flags appear)…")
    start = date.today() - timedelta(days=DAYS_TOTAL - 1)

    for i in range(DAYS_TOTAL):
        d = start + timedelta(days=i)
        if i < DECLINE_START:
            # Stable baseline
            mood, sleep_h, sleep_q, stress = 4, 7.5, 4, 4
        else:
            # Gradual burnout shape: mood+sleep down together, stress up
            k = (i - DECLINE_START + 1) / (DAYS_TOTAL - DECLINE_START)  # 0..1
            mood    = 4 - 2.2 * k          # 4 -> ~1.8
            sleep_h = 7.5 - 2.8 * k        # 7.5 -> ~4.7
            sleep_q = 4 - 2.0 * k          # 4 -> 2
            stress  = 4 + 4.5 * k          # 4 -> ~8.5

        payload = {
            "user_id": user_id,
            "log_date": str(d),
            "mood": int(clamp(round(n(mood, 0.3)), 1, 5)),
            "sleep_hours": clamp(n(sleep_h, 0.4), 0, 14),
            "sleep_quality": int(clamp(round(n(sleep_q, 0.3)), 1, 5)),
            "study_hours": clamp(n(4, 0.5), 0, 18),   # flat: no workload excuse
            "stress": int(clamp(round(n(stress, 0.5)), 1, 10)),
            "free_text": None,
        }
        r = requests.post(f"{base}/log", json=payload, timeout=60)
        r.raise_for_status()
        res = r.json()
        marker = {"none": " ", "soft_nudge": "⚠", "hard_flag": "🚨"}.get(res["flag_type"], "?")
        print(f"   {d}  {marker}  {res['flag_type']:<10}  {res['flag_reason'][:70]}")

    # ------------------------------------------------------------------
    # 3. Optionally run the automation sweep
    # ------------------------------------------------------------------
    if args.sweep:
        print("\n3) Triggering the daily automation sweep…")
        r = requests.post(
            f"{base}/automation/daily-sweep",
            headers={"X-Automation-Secret": args.sweep},
            timeout=120,
        )
        r.raise_for_status()
        rep = r.json()
        print(f"   run_id        : {rep['run_id']}")
        print(f"   users scanned : {rep['users_scanned']}")
        print(f"   nudges sent   : {rep['nudges_sent']}")
        print(f"   no action     : {rep['no_action']}  (stable users are left alone)")
        print(f"   cooldown skip : {rep['skipped_cooldown']}")
    else:
        print("\n3) Skipped automation sweep (pass --sweep YOUR_SECRET to run it).")

    # ------------------------------------------------------------------
    # 4. How to view it all in the browser
    # ------------------------------------------------------------------
    print(f"""
──────────────────────────────────────────────────────────────────────
DONE. To open the demo user in the frontend:

  1. Open the app in the browser (http://localhost:5173)
  2. Open DevTools console (F12) and run:

       localStorage.setItem('wb_user_id', '{user_id}')
       localStorage.removeItem('wb_last_log_date')

  3. Reload the page.

WHAT TO LOOK AT (and screenshot for the PPT):

  • Dashboard   — flag card shows the current state + the 7-day chart
                  falling. (Slide 12 screenshot.)
  • Agent chat  — automated nudge appears with the amber
                  "🤖 sent automatically by the daily agent sweep" chip
                  (if you ran --sweep). Then ask:
                      "How have I been doing this week?"
                      "Is my sleep getting better or worse?"
                  and watch the tool chips appear. (Slide 13 screenshot.)
  • Safety      — if a hard flag fired, the item-9 check appears;
                  answering 0 continues normally, any nonzero shows
                  crisis resources instantly.
──────────────────────────────────────────────────────────────────────""")


if __name__ == "__main__":
    main()