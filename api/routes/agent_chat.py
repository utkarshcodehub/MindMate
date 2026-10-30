"""
routes/agent_chat.py

POST /api/agent/chat -- One turn of conversation with the Wellbeing Agent.

The route is thin on purpose: validate, check the user exists, delegate
to api/agent.py. All agent logic (safety pre-screen, tool loop) lives
there so it can be unit-tested without HTTP.
"""

from fastapi import APIRouter, HTTPException, Depends

from api.models import AgentChatRequest, AgentChatResponse
from api import db
from api.auth import get_current_user_id
from api.agent import run_agent

router = APIRouter()


@router.post("/agent/chat", response_model=AgentChatResponse)
async def agent_chat(
    req: AgentChatRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    if req.user_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only chat with the agent using your own account.",
        )

    user = db.get_user(req.user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found. Complete onboarding first.",
        )

    result = run_agent(
        user_id=req.user_id,
        message=req.message,
        history=[t.model_dump() for t in (req.history or [])],
    )

    return AgentChatResponse(
        reply=result["reply"],
        tools_used=result["tools_used"],
        crisis=result["crisis"],
    )
