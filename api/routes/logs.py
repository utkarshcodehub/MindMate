"""
routes/logs.py

POST /api/log          -- Submit a daily check-in, get back a flag decision
GET  /api/user/{id}/summary -- Recent logs + flag state for the dashboard
"""

import pandas as pd
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException

from api.models import DailyLogRequest, DailyLogResponse, UserSummaryResponse, RecentLog
from api import db
from api.groq_client import generate_nudge_message
from engine.flag_decision import evaluate_day, UserTrendState
from engine.safety_check import CRISIS_RESOURCES

router = APIRouter()

LOG_HISTORY_DAYS = 60


def _logs_to_dataframe(logs: list) -> pd.DataFrame:
    if not logs:
        return pd.DataFrame(columns=[
            "user_id", "log_date", "mood", "sleep_hours",
            "sleep_quality", "study_hours", "stress",
        ])
    df = pd.DataFrame(logs)
    df["log_date"] = pd.to_datetime(df["log_date"])
    return df


@router.post("/log", response_model=DailyLogResponse)
async def submit_log(req: DailyLogRequest):
    # 1. Verify user exists
    user = db.get_user(req.user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found. Complete onboarding first."
        )

    # 2. Insert today's log
    log_record = db.insert_daily_log(
        user_id=req.user_id,
        log_date=req.log_date,
        mood=req.mood,
        sleep_hours=req.sleep_hours,
        sleep_quality=req.sleep_quality,
        study_hours=req.study_hours,
        stress=req.stress,
        free_text=req.free_text,
    )

    # 3. Pull history + flagged dates for the trend engine
    since = req.log_date - timedelta(days=LOG_HISTORY_DAYS)
    raw_logs = db.get_user_logs(req.user_id, since)
    df = _logs_to_dataframe(raw_logs)
    flagged_dates = db.get_flagged_dates(req.user_id, since)

    # 4. Rebuild UserTrendState by replaying the last 15 days of logs
    #    so that consecutive_concern_days streaks are correct for today.
    #    (v1 limitation: in production, persist streak state in DB instead)
    state = UserTrendState(user_id=req.user_id, flagged_dates=flagged_dates)
    today_ts = pd.Timestamp(req.log_date)

    replay_rows = df[df["log_date"] < today_ts].tail(15)
    for _, row in replay_rows.iterrows():
        evaluate_day(df, state, pd.Timestamp(row["log_date"]))

    # 5. Evaluate today
    result = evaluate_day(df, state, today_ts)

    # 6. Persist the flag if non-trivial
    if result.flag_type != "none":
        triggering_for_db = {
            metric: {
                "z_score": sig.z_score,
                "z_severity": sig.z_severity,
                "slope": sig.slope,
                "slope_concerning": sig.slope_concerning,
                "concern": sig.concern,
            }
            for metric, sig in result.triggering_metrics.items()
        }
        db.insert_flag(
            user_id=req.user_id,
            flag_date=req.log_date,
            flag_type=result.flag_type,
            triggering_metrics=triggering_for_db,
            reason=result.reason,
        )

    # 7. Build nudge message and crisis resources
    nudge_message = None
    crisis_resources = []
    safety_check_required = result.flag_type == "hard_flag"

    if result.flag_type in ("soft_nudge", "hard_flag"):
        # Extract which metrics actually triggered and the longest streak
        concerning = [
            m for m, s in result.triggering_metrics.items() if s.concern
        ]
        max_streak = max(
            (state.consecutive_concern_days.get(m, 1) for m in concerning),
            default=1,
        )
        # Groq writes the copy; the engine already decided the flag
        nudge_message = generate_nudge_message(
            flag_type=result.flag_type,
            concerning_metrics=concerning,
            consecutive_days=max_streak,
        )

    if result.flag_type == "hard_flag":
        crisis_resources = CRISIS_RESOURCES

    return DailyLogResponse(
        log_id=log_record["id"],
        flag_type=result.flag_type,
        flag_reason=result.reason,
        nudge_message=nudge_message,
        safety_check_required=safety_check_required,
        crisis_resources=crisis_resources,
    )


@router.get("/user/{user_id}/summary", response_model=UserSummaryResponse)
async def get_user_summary(user_id: str):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Recent logs (last 7 days)
    raw_logs = db.get_recent_logs(user_id, days=7)
    flags_7 = db.get_recent_flags(user_id, days=7)
    flag_map = {row["flag_date"]: row["flag_type"] for row in flags_7}

    recent_logs = [
        RecentLog(
            log_date=row["log_date"],
            mood=row["mood"],
            sleep_hours=row["sleep_hours"],
            sleep_quality=row["sleep_quality"],
            study_hours=row["study_hours"],
            stress=row["stress"],
            flag_type=flag_map.get(row["log_date"]),
        )
        for row in raw_logs
    ]

    # Flag state
    flags_14 = db.get_recent_flags(user_id, days=14)
    current_flag_state = flags_14[0]["flag_type"] if flags_14 else "none"
    days_flagged = sum(1 for f in flags_14 if f["flag_type"] != "none")

    # Baseline availability
    all_logs = db.get_user_logs(
        user_id,
        since_date=date.today() - timedelta(days=90)
    )
    baseline_available = len(all_logs) >= 10

    return UserSummaryResponse(
        user_id=user_id,
        recent_logs=recent_logs,
        current_flag_state=current_flag_state,
        days_flagged_last_14=days_flagged,
        baseline_available=baseline_available,
    )