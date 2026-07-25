"""
routes/automation.py

POST /api/automation/daily-sweep   -- the cron-triggered automation run
GET  /api/user/{id}/agent-nudge    -- latest automated nudge for the UI

The sweep endpoint requires header:  X-Automation-Secret: <AUTOMATION_SECRET>
Set AUTOMATION_SECRET as an environment variable in production; the cron
service (GitHub Actions / cron-job.org) sends the same header.
"""

import os
from fastapi import APIRouter, Header, HTTPException

from api import db
from api.automation import run_daily_sweep

router = APIRouter()


@router.post("/automation/daily-sweep")
async def daily_sweep(x_automation_secret: str = Header(default="")):
    expected = os.environ.get("AUTOMATION_SECRET")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="AUTOMATION_SECRET is not configured on the server.",
        )
    if x_automation_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid automation secret.")
    return run_daily_sweep()


@router.get("/user/{user_id}/agent-nudge")
async def latest_agent_nudge(user_id: str):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    nudge = db.get_latest_agent_nudge(user_id, within_hours=48)
    if not nudge:
        return {"has_nudge": False}
    return {
        "has_nudge": True,
        "nudge_type": nudge["nudge_type"],
        "message": nudge["message"],
        "created_at": nudge["created_at"],
    }
