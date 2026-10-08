"""
automation.py

The AUTOMATION layer: a scheduled agent sweep that runs with no human
in the loop. This is the n8n-style workflow, expressed in code:

    TRIGGER   — external cron (GitHub Actions / cron-job.org) hits
                POST /api/automation/daily-sweep once a day
    PERCEIVE  — for every registered user, pull their recent logs and
                run the same trend analysis the chat agent uses
    DECIDE    — deterministic rules pick who gets what (see decide_nudge):
                  * concerning trend        -> wellbeing nudge
                  * 3+ days without logging -> gentle re-engagement nudge
                  * everyone else           -> no action (most users, by design)
    ACT       — Groq LLaMA writes a personalised message; it is stored in
                the agent_nudges table and surfaces on the student's
                dashboard/chat at next login.

DESIGN RULE PRESERVED: the LLM never decides WHO gets contacted or WHY —
decide_nudge() is pure deterministic code. The LLM only words the message,
and static fallbacks ship if it is unreachable. The automation never
sends crisis content; crisis handling stays in the log-time hard_flag
path and the chat pre-screen, where it is immediate.

The endpoint is protected by an AUTOMATION_SECRET header so a public
cron service can trigger it while nobody else can.
"""

import os
import uuid
from datetime import date, datetime
from dotenv import load_dotenv

from api import db
from api.agent import _tool_get_trend_analysis

load_dotenv()

REENGAGE_AFTER_DAYS = 3          # no logs for this many days -> re-engagement
NUDGE_COOLDOWN_HOURS = 48        # never nudge the same user twice within this window


# ----------------------------------------------------------------------
# DECIDE — pure, deterministic, unit-testable
# ----------------------------------------------------------------------

def decide_nudge(trend: dict, days_since_last_log: int | None) -> dict:
    """
    Decide what (if any) automated nudge a user should get today.

    Returns {"action": "none" | "wellbeing" | "reengage", "metrics": [...]}
    """
    # Never logged, or no logs found at all -> nothing (onboarding handles them)
    if days_since_last_log is None:
        return {"action": "none", "metrics": []}

    # Silent for a while -> gentle re-engagement
    if days_since_last_log >= REENGAGE_AFTER_DAYS:
        return {"action": "reengage", "metrics": []}

    # Actively logging + concerning trajectory -> wellbeing nudge
    concerning = trend.get("concerning_metrics", []) if trend else []
    if concerning:
        return {"action": "wellbeing", "metrics": concerning}

    return {"action": "none", "metrics": []}


# ----------------------------------------------------------------------
# ACT — LLM words the message; static fallbacks if unreachable
# ----------------------------------------------------------------------

_FALLBACKS = {
    "wellbeing": (
        "Hey — the last few days look like they've been a bit heavier than "
        "your usual. No pressure to fix everything today; maybe just pick "
        "one small kind thing to do for yourself."
    ),
    "reengage": (
        "It's been a few days since your last check-in. No guilt — life "
        "gets busy. Thirty seconds today keeps your picture accurate, "
        "whenever you're ready."
    ),
}

_FRIENDLY = {
    "mood": "mood", "sleep_hours": "sleep", "sleep_quality": "sleep quality",
    "study_hours": "energy for studying", "stress": "stress levels",
}


def _write_message(action: str, metrics: list) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return _FALLBACKS[action]
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        if action == "wellbeing":
            friendly = ", ".join(_FRIENDLY.get(m, m) for m in metrics) or "a few things"
            prompt = (
                f"A student's {friendly} has been trending harder than their "
                "usual over recent days. Write a warm 2-3 sentence proactive "
                "check-in note. No data, scores, AI or diagnosis mentions. "
                "End with one small, concrete suggestion for today."
            )
        else:
            prompt = (
                "A student hasn't done their 30-second wellbeing check-in for "
                "a few days. Write a warm, guilt-free 2-sentence note inviting "
                "them back. No data, scores, AI or diagnosis mentions."
            )
        resp = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": (
                    "You write brief, warm notes for a student wellbeing app. "
                    "Never diagnose, never mention AI or data, never use "
                    "clinical language, never catastrophize. 2-3 sentences max."
                )},
                {"role": "user", "content": prompt},
            ],
            max_tokens=120,
            temperature=0.7,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text or _FALLBACKS[action]
    except Exception:
        return _FALLBACKS[action]


# ----------------------------------------------------------------------
# THE SWEEP
# ----------------------------------------------------------------------

def _days_since_last_log(user_id: str) -> int | None:
    logs = db.get_recent_logs(user_id, days=30)
    if not logs:
        return None
    last = max(str(l.get("log_date")) for l in logs)
    return (date.today() - date.fromisoformat(last[:10])).days


def run_daily_sweep() -> dict:
    """One full automated pass over every user. Returns a run report."""
    run_id = f"sweep-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
    report = {"run_id": run_id, "users_scanned": 0, "nudges_sent": 0,
              "skipped_cooldown": 0, "no_action": 0, "errors": 0, "details": []}

    for user_id in db.get_all_user_ids():
        report["users_scanned"] += 1
        try:
            # Cooldown: don't pile nudges onto the same person
            if db.get_latest_agent_nudge(user_id, within_hours=NUDGE_COOLDOWN_HOURS):
                report["skipped_cooldown"] += 1
                continue

            days_quiet = _days_since_last_log(user_id)
            trend = _tool_get_trend_analysis(user_id) if days_quiet is not None else {}
            decision = decide_nudge(trend, days_quiet)

            if decision["action"] == "none":
                report["no_action"] += 1
                continue

            message = _write_message(decision["action"], decision["metrics"])
            db.insert_agent_nudge(
                user_id=user_id,
                nudge_type=decision["action"],
                message=message,
                concerning_metrics=decision["metrics"],
                run_id=run_id,
            )
            report["nudges_sent"] += 1
            report["details"].append({"user_id": user_id, "action": decision["action"]})
        except Exception as e:
            report["errors"] += 1
            report["details"].append({"user_id": user_id, "error": type(e).__name__})

    return report
