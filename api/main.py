"""
main.py

FastAPI application entry point.

Run from the student_wellbeing/ root directory with:
    uvicorn api.main:app --reload --port 8000

Interactive docs:
    http://localhost:8000/docs    (Swagger UI)
    http://localhost:8000/redoc   (ReDoc)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import onboard, logs, safety, agent_chat, automation

app = FastAPI(
    title="Student Wellbeing API",
    description=(
        "Private, non-judgmental early-warning system for student burnout. "
        "This API does NOT diagnose, does NOT replace therapy, and is NOT a "
        "crisis service. It is a bridge to help-seeking, not the help itself. "
        "Crisis resources: iCall 9152987821 | Vandrevala 1860-2662-345 | "
        "NIMHANS 080-46110007"
    ),
    version="0.1.0",
)

import os

# In production set ALLOWED_ORIGINS to your Vercel URL, e.g.
#   ALLOWED_ORIGINS=https://student-wellbeing.vercel.app
_default_origins = "http://localhost:3000,http://localhost:5173"
_origins = os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(onboard.router, prefix="/api", tags=["Onboarding"])
app.include_router(logs.router,    prefix="/api", tags=["Daily Logs"])
app.include_router(safety.router,  prefix="/api", tags=["Safety Checks"])
app.include_router(agent_chat.router, prefix="/api", tags=["Wellbeing Agent"])
app.include_router(automation.router, prefix="/api", tags=["Automation"])


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "disclaimer": (
            "This tool does not diagnose mental health conditions. "
            "If you are in crisis, please contact iCall (9152987821) "
            "or Vandrevala Foundation (1860-2662-345)."
        ),
    }