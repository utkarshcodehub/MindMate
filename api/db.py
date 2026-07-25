"""
db.py

Supabase client setup + all database query helpers.

Routes should call ONLY these functions -- no raw Supabase calls in
route files. This keeps all SQL/query logic in one place so schema
changes only need to be fixed here.

Environment variables required (put these in a .env file locally,
set as environment variables in production):
    SUPABASE_URL=https://your-project.supabase.co
    SUPABASE_KEY=your-anon-or-service-role-key

Use the service role key for backend-only server (never expose it
in client-side code). The anon key is only for client-side usage
where row-level security policies are set up.
"""

import os
import json
from datetime import date, timedelta
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

_client: Optional[Client] = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set. "
                "Copy .env.example to .env and fill in your project credentials."
            )
        _client = create_client(url, key)
    return _client


# -----------------------------------------------------------------------
# USERS
# -----------------------------------------------------------------------

def create_user(
    user_id: str,
    phq2_score: int,
    gad2_score: int,
    pss4_score: int,
    overall_risk: str,
    raw_responses: dict,
) -> dict:
    client = get_client()
    data = {
        "id": user_id,
        "phq2_score": phq2_score,
        "gad2_score": gad2_score,
        "pss4_score": pss4_score,
        "overall_risk": overall_risk,
        "onboarding_raw_responses": raw_responses,
    }
    result = client.table("users").insert(data).execute()
    return result.data[0]


def get_user(user_id: str) -> Optional[dict]:
    client = get_client()
    result = client.table("users").select("*").eq("id", user_id).execute()
    return result.data[0] if result.data else None


# -----------------------------------------------------------------------
# DAILY LOGS
# -----------------------------------------------------------------------

def insert_daily_log(
    user_id: str,
    log_date: date,
    mood: int,
    sleep_hours: float,
    sleep_quality: int,
    study_hours: float,
    stress: int,
    free_text: Optional[str],
) -> dict:
    client = get_client()
    data = {
        "user_id": user_id,
        "log_date": str(log_date),
        "mood": mood,
        "sleep_hours": sleep_hours,
        "sleep_quality": sleep_quality,
        "study_hours": study_hours,
        "stress": stress,
        "free_text": free_text,
    }
    result = client.table("daily_logs").insert(data).execute()
    return result.data[0]


def get_user_logs(user_id: str, since_date: date) -> list:
    """
    Fetch all daily logs for a user from since_date onwards, ordered by date.
    Used by the trend engine which needs a full history window.
    """
    client = get_client()
    result = (
        client.table("daily_logs")
        .select("*")
        .eq("user_id", user_id)
        .gte("log_date", str(since_date))
        .order("log_date")
        .execute()
    )
    return result.data


def get_recent_logs(user_id: str, days: int = 7) -> list:
    since = date.today() - timedelta(days=days)
    return get_user_logs(user_id, since)


# -----------------------------------------------------------------------
# FLAGS
# -----------------------------------------------------------------------

def insert_flag(
    user_id: str,
    flag_date: date,
    flag_type: str,
    triggering_metrics: dict,
    reason: str,
) -> dict:
    client = get_client()
    data = {
        "user_id": user_id,
        "flag_date": str(flag_date),
        "flag_type": flag_type,
        "triggering_metrics": triggering_metrics,
        "reason": reason,
        "resolved": False,
    }
    result = client.table("flags").insert(data).execute()
    return result.data[0]


def get_flagged_dates(user_id: str, since_date: date) -> set:
    """
    Returns the set of dates that had a non-'none' flag for a user.
    Passed to the trend engine's baseline computation to exclude
    flagged days from contaminating the baseline.
    """
    client = get_client()
    result = (
        client.table("flags")
        .select("flag_date")
        .eq("user_id", user_id)
        .neq("flag_type", "none")
        .gte("flag_date", str(since_date))
        .execute()
    )
    import pandas as pd
    return {pd.Timestamp(row["flag_date"]) for row in result.data}


def get_recent_flags(user_id: str, days: int = 14) -> list:
    since = date.today() - timedelta(days=days)
    client = get_client()
    result = (
        client.table("flags")
        .select("*")
        .eq("user_id", user_id)
        .gte("flag_date", str(since))
        .order("flag_date", desc=True)
        .execute()
    )
    return result.data


# -----------------------------------------------------------------------
# SAFETY CHECKS (ITEM 9)
# -----------------------------------------------------------------------

def insert_safety_check(
    user_id: str,
    check_date: date,
    trigger_source: str,
    item9_response: int,
    crisis_path_fired: bool,
    resources_shown: list,
) -> dict:
    client = get_client()
    data = {
        "user_id": user_id,
        "check_date": str(check_date),
        "trigger_source": trigger_source,
        "item9_response": item9_response,
        "crisis_path_fired": crisis_path_fired,
        "resources_shown": resources_shown,
    }
    result = client.table("safety_checks").insert(data).execute()
    return result.data[0]


def get_last_safety_check(user_id: str) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("safety_checks")
        .select("*")
        .eq("user_id", user_id)
        .order("check_date", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# -----------------------------------------------------------------------
# AUTOMATION (agent nudges)
# -----------------------------------------------------------------------

def get_all_user_ids() -> list:
    """All user ids — used by the daily automation sweep."""
    client = get_client()
    result = client.table("users").select("id").execute()
    return [row["id"] for row in result.data]


def insert_agent_nudge(
    user_id: str,
    nudge_type: str,
    message: str,
    concerning_metrics: list,
    run_id: str,
) -> dict:
    client = get_client()
    data = {
        "user_id": user_id,
        "nudge_type": nudge_type,
        "message": message,
        "concerning_metrics": json.dumps(concerning_metrics),
        "run_id": run_id,
    }
    result = client.table("agent_nudges").insert(data).execute()
    return result.data[0]


def get_latest_agent_nudge(user_id: str, within_hours: int = 48) -> Optional[dict]:
    """Most recent automated nudge for a user, if fresh enough."""
    from datetime import datetime, timedelta as td, timezone
    client = get_client()
    cutoff = (datetime.now(timezone.utc) - td(hours=within_hours)).isoformat()
    result = (
        client.table("agent_nudges")
        .select("*")
        .eq("user_id", user_id)
        .gte("created_at", cutoff)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None
