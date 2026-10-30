"""
routes/safety.py

POST /api/safety-check              -- Submit item 9 response
GET  /api/user/{id}/due-safety-check -- Check if 2-week cadence check is due
"""

from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Depends

from api.models import SafetyCheckRequest, SafetyCheckResponse, SafetyCheckDueResponse
from api import db
from api.auth import get_current_user_id, verify_user_access
from engine.safety_check import evaluate_item9

router = APIRouter()

SAFETY_CHECK_CADENCE_DAYS = 14


@router.post("/safety-check", response_model=SafetyCheckResponse)
async def submit_safety_check(
    req: SafetyCheckRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    if req.user_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only submit safety checks for your own account.",
        )
    user = db.get_user(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Deterministic safety bypass -- no LLM in this path
    result = evaluate_item9(
        user_id=req.user_id,
        check_date=date.today(),
        trigger_source=req.trigger_source,
        item9_response=req.item9_response,
    )

    # Persist the check regardless of outcome (full audit trail)
    record = db.insert_safety_check(
        user_id=req.user_id,
        check_date=date.today(),
        trigger_source=req.trigger_source,
        item9_response=req.item9_response,
        crisis_path_fired=result.crisis_path_fired,
        resources_shown=result.resources_shown,
    )

    if result.crisis_path_fired:
        message = (
            "Thank you for being honest — that takes courage. "
            "Please reach out to one of these services. They are "
            "confidential, free, and available right now. "
            "You don't have to face this alone."
        )
    else:
        message = "Thank you. We'll check in again in two weeks."

    return SafetyCheckResponse(
        check_id=record["id"],
        crisis_path_fired=result.crisis_path_fired,
        resources_shown=result.resources_shown,
        message=message,
    )


@router.get("/user/{user_id}/due-safety-check", response_model=SafetyCheckDueResponse)
async def check_safety_due(
    user_id: str,
    _: str = Depends(verify_user_access),
):

    """
    Called by the frontend (or a scheduled cron job) to ask:
    is this user due for their 2-week item 9 re-check?
    """
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    last_check = db.get_last_safety_check(user_id)

    if last_check is None:
        return SafetyCheckDueResponse(
            user_id=user_id,
            is_due=True,
            days_since_last_check=None,
            next_check_date=date.today(),
        )

    last_date = date.fromisoformat(str(last_check["check_date"]))
    days_since = (date.today() - last_date).days
    next_date = last_date + timedelta(days=SAFETY_CHECK_CADENCE_DAYS)
    is_due = date.today() >= next_date

    return SafetyCheckDueResponse(
        user_id=user_id,
        is_due=is_due,
        days_since_last_check=days_since,
        next_check_date=next_date,
    )