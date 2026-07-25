"""
routes/onboard.py

POST /api/onboard

Entry point for every new user. Scores PHQ-2, GAD-2, PSS-4, handles
item 9 bypass immediately if needed, creates the user record, and returns
a structured response the frontend uses to decide what to show next.

Item 9 evaluated here as 'onboarding' trigger_source -- if nonzero,
crisis resources are returned immediately and a safety_check record is
inserted. User is still created regardless; crisis routing does NOT
block account creation.
"""

import uuid
from datetime import date
from fastapi import APIRouter, HTTPException

from api.models import OnboardRequest, OnboardResponse
from api.scoring import score_onboarding
from api import db
from engine.safety_check import evaluate_item9

router = APIRouter()


@router.post("/onboard", response_model=OnboardResponse)
async def onboard(req: OnboardRequest):
    # 1. Score the abbreviated instruments
    scores = score_onboarding(
        req.phq2_q1, req.phq2_q2,
        req.gad2_q1, req.gad2_q2,
        req.pss4_q2, req.pss4_q4, req.pss4_q5, req.pss4_q10,
    )

    # 2. Evaluate item 9 -- fully independent of scoring
    user_id = str(uuid.uuid4())
    safety_result = evaluate_item9(
        user_id=user_id,
        check_date=date.today(),
        trigger_source="onboarding",
        item9_response=req.item9_response,
    )

    # 3. Create user record in DB
    db.create_user(
        user_id=user_id,
        phq2_score=scores.phq2_score,
        gad2_score=scores.gad2_score,
        pss4_score=scores.pss4_score,
        overall_risk=scores.overall_risk,
        raw_responses=scores.raw_responses,
    )

    # 4. If item 9 fired, log the safety check
    if safety_result.crisis_path_fired:
        db.insert_safety_check(
            user_id=user_id,
            check_date=date.today(),
            trigger_source="onboarding",
            item9_response=req.item9_response,
            crisis_path_fired=True,
            resources_shown=safety_result.resources_shown,
        )

    # 5. Build response message
    if safety_result.crisis_path_fired:
        message = (
            "We noticed your response to the last question. "
            "Please know you don't have to carry this alone — "
            "the resources below are confidential and available right now."
        )
    elif scores.overall_risk == "high":
        message = (
            "Thanks for sharing that. It sounds like things have been "
            "tough lately. Daily check-ins will help us track how you're "
            "doing and let you know when to reach out for support."
        )
    elif scores.overall_risk == "moderate":
        message = (
            "Thanks for completing the check-in. We'll use your daily "
            "logs to spot patterns and give you a heads-up if things "
            "start to feel heavier."
        )
    else:
        message = (
            "Good to have you here. Keep logging daily — even on "
            "normal days the data helps us understand what's typical "
            "for you so we can flag any real changes."
        )

    return OnboardResponse(
        user_id=user_id,
        phq2_score=scores.phq2_score,
        gad2_score=scores.gad2_score,
        pss4_score=scores.pss4_score,
        phq2_flag=scores.phq2_flag,
        gad2_flag=scores.gad2_flag,
        crisis_path_fired=safety_result.crisis_path_fired,
        crisis_resources=safety_result.resources_shown,
        message=message,
    )