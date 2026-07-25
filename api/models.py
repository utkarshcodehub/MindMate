"""
models.py

All Pydantic request and response shapes for the API.
Keeping them in one file makes the contract easy to read
and prevents circular imports between route modules.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date


# -----------------------------------------------------------------------
# ONBOARDING
# -----------------------------------------------------------------------

class OnboardRequest(BaseModel):
    # PHQ-2: items 1 and 2 of PHQ-9 (0-3 each)
    phq2_q1: int = Field(..., ge=0, le=3, description="Little interest or pleasure in doing things")
    phq2_q2: int = Field(..., ge=0, le=3, description="Feeling down, depressed, or hopeless")

    # GAD-2: items 1 and 2 of GAD-7 (0-3 each)
    gad2_q1: int = Field(..., ge=0, le=3, description="Feeling nervous, anxious, or on edge")
    gad2_q2: int = Field(..., ge=0, le=3, description="Not being able to stop or control worrying")

    # PSS-4: items 2, 4, 5, 10 of PSS-10 (0-4 each; items 4 and 5 are reverse-scored)
    pss4_q2:  int = Field(..., ge=0, le=4, description="Felt unable to control important things")
    pss4_q4:  int = Field(..., ge=0, le=4, description="Felt confident handling personal problems (reverse)")
    pss4_q5:  int = Field(..., ge=0, le=4, description="Felt things were going your way (reverse)")
    pss4_q10: int = Field(..., ge=0, le=4, description="Felt difficulties piling up too high")

    # PHQ-9 item 9 — standalone, never folded into totals
    item9_response: int = Field(..., ge=0, le=3,
        description="Thoughts of being better off dead or of hurting yourself")


class OnboardResponse(BaseModel):
    user_id: str
    phq2_score: int                  # 0-6
    gad2_score: int                  # 0-6
    pss4_score: int                  # 0-16 (post-reversal)
    phq2_flag: bool                  # True if >= 3 (clinical further-evaluation threshold)
    gad2_flag: bool
    crisis_path_fired: bool          # True if item9_response > 0
    crisis_resources: list           # populated only if crisis_path_fired
    message: str                     # human-readable summary for the client to display


# -----------------------------------------------------------------------
# DAILY LOG
# -----------------------------------------------------------------------

class DailyLogRequest(BaseModel):
    user_id: str
    log_date: date
    mood: int           = Field(..., ge=1, le=5)
    sleep_hours: float  = Field(..., ge=0, le=14)
    sleep_quality: int  = Field(..., ge=1, le=5)
    study_hours: float  = Field(..., ge=0, le=18)
    stress: int         = Field(..., ge=1, le=10)
    free_text: Optional[str] = None  # never scored, reflection only

    @field_validator("log_date", mode="before")
    @classmethod
    def no_future_dates(cls, v):
        from datetime import date as d
        parsed = d.fromisoformat(str(v)) if not isinstance(v, d) else v
        if parsed > d.today():
            raise ValueError("log_date cannot be in the future")
        return parsed


class DailyLogResponse(BaseModel):
    log_id: str
    flag_type: str                   # 'none' | 'soft_nudge' | 'hard_flag'
    flag_reason: str
    nudge_message: Optional[str]     # Groq-generated copy for soft_nudge
    safety_check_required: bool      # True if hard_flag fired -> trigger item 9
    crisis_resources: list           # populated only if hard_flag fired


# -----------------------------------------------------------------------
# SAFETY CHECK (ITEM 9)
# -----------------------------------------------------------------------

class SafetyCheckRequest(BaseModel):
    user_id: str
    item9_response: int = Field(..., ge=0, le=3)
    trigger_source: str = Field(
        ...,
        pattern="^(onboarding|scheduled_2wk|hard_flag_triggered)$"
    )


class SafetyCheckResponse(BaseModel):
    check_id: str
    crisis_path_fired: bool
    resources_shown: list
    message: str


class SafetyCheckDueResponse(BaseModel):
    user_id: str
    is_due: bool
    days_since_last_check: Optional[int]
    next_check_date: Optional[date]


# -----------------------------------------------------------------------
# USER SUMMARY
# -----------------------------------------------------------------------

class RecentLog(BaseModel):
    log_date: date
    mood: int
    sleep_hours: float
    sleep_quality: int
    study_hours: float
    stress: int
    flag_type: Optional[str]


class UserSummaryResponse(BaseModel):
    user_id: str
    recent_logs: list[RecentLog]     # last 7 days
    current_flag_state: str          # most recent flag_type
    days_flagged_last_14: int        # how many of the last 14 days had a non-'none' flag
    baseline_available: bool         # False during cold-start period


# -----------------------------------------------------------------------
# WELLBEING AGENT CHAT
# -----------------------------------------------------------------------

class AgentTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class AgentChatRequest(BaseModel):
    user_id: str
    message: str = Field(..., min_length=1, max_length=2000)
    history: Optional[list[AgentTurn]] = None   # prior turns, client-managed


class AgentChatResponse(BaseModel):
    reply: str
    tools_used: list[str]    # which tools the agent chose to call this turn
    crisis: bool             # True if the deterministic pre-screen fired
