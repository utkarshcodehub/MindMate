"""
agent.py

The Wellbeing Agent: an autonomous LLM agent (Groq LLaMA 3.3 70B with
tool use) that students can chat with about their wellbeing patterns.

WHAT MAKES THIS AN "AGENT" (vs a plain chatbot):
  1. PERCEIVES  — has tools to fetch the student's real check-in data
  2. REASONS    — the LLM itself decides WHICH tools to call and WHEN,
                  based on the conversation (we never hardcode the flow)
  3. ACTS       — calls tools, reads results, may call more tools,
                  then composes a grounded, personalised response
  4. LOOPS      — multi-step: up to MAX_TOOL_ROUNDS of tool-call cycles

PRESERVED DESIGN RULE (same as groq_client.py):
  The LLM never makes safety decisions. Before the agent loop runs,
  a deterministic pre-screen checks the user's message for crisis
  language. If it fires, we return crisis resources immediately —
  the LLM is never consulted. Inside the loop, the agent's system
  prompt forbids diagnosis and clinical claims; the get_crisis_resources
  tool lets it surface helplines, but the routing rule is ours, not its.

Fails gracefully:
  - GROQ_API_KEY missing -> static fallback message, no crash
  - API/tool errors      -> static fallback message, no crash
"""

import os
import json
from datetime import date, timedelta
from dotenv import load_dotenv

from api import db
from engine.safety_check import CRISIS_RESOURCES

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
MAX_TOOL_ROUNDS = 4

# ----------------------------------------------------------------------
# Deterministic crisis pre-screen (runs BEFORE any LLM call)
# ----------------------------------------------------------------------
# Same philosophy as safety_check.py: no nuance, no tiers, no LLM.
# If it fires, resources are shown, period.

_CRISIS_PATTERNS = [
    "kill myself", "end my life", "suicide", "suicidal",
    "hurt myself", "harm myself", "self harm", "self-harm",
    "better off dead", "don't want to live", "dont want to live",
    "want to die", "end it all",
]


def crisis_prescreen(message: str) -> bool:
    """Deterministic keyword screen. Any hit -> crisis path, no LLM."""
    lowered = message.lower()
    return any(p in lowered for p in _CRISIS_PATTERNS)


CRISIS_RESPONSE = (
    "It sounds like you're going through something really heavy right now, "
    "and I want you to talk to a real person about it — someone trained to "
    "help. Please reach out to one of these free, confidential services:\n\n"
    + "\n".join(
        f"• {r['name']}: {r['phone']} ({r['hours']})" for r in CRISIS_RESOURCES
    )
    + "\n\nYou don't have to carry this alone."
)

# ----------------------------------------------------------------------
# Tools the agent can call
# ----------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_user_summary",
            "description": (
                "Fetch the student's recent daily check-in logs (last 7 days): "
                "mood (1-5), sleep hours, sleep quality (1-5), study hours, "
                "stress (1-10), plus any flags raised. Call this whenever the "
                "student asks about how they've been doing, their patterns, "
                "sleep, mood, stress, or anything about their recent data."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trend_analysis",
            "description": (
                "Compare the student's last 7 days against their previous "
                "3 weeks (their personal baseline). Returns per-metric "
                "averages, the direction of change, and which metrics look "
                "concerning. Call this when the student asks whether things "
                "are getting better or worse, or when you want to ground "
                "advice in their actual trajectory rather than guessing."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crisis_resources",
            "description": (
                "Return the list of professional mental-health helplines "
                "(India). Call this if the student asks where to get "
                "professional help, counselling, or someone to talk to."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


# ----------------------------------------------------------------------
# Tool implementations (deterministic, DB-backed)
# ----------------------------------------------------------------------

def _tool_get_user_summary(user_id: str) -> dict:
    logs = db.get_recent_logs(user_id, days=7)
    flags = db.get_recent_flags(user_id, days=14)
    if not logs:
        return {"note": "No check-in logs yet for this student.", "logs": []}
    return {
        "recent_logs": [
            {
                "date": str(l.get("log_date")),
                "mood_1to5": l.get("mood"),
                "sleep_hours": l.get("sleep_hours"),
                "sleep_quality_1to5": l.get("sleep_quality"),
                "study_hours": l.get("study_hours"),
                "stress_1to10": l.get("stress"),
            }
            for l in logs
        ],
        "flags_last_14_days": len([f for f in flags if f.get("flag_type") != "none"]),
    }


def _avg(rows, key):
    vals = [r.get(key) for r in rows if r.get(key) is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def _tool_get_trend_analysis(user_id: str) -> dict:
    since = date.today() - timedelta(days=28)
    logs = db.get_user_logs(user_id, since)
    if len(logs) < 3:
        return {"note": "Not enough data yet for a trend analysis (need 3+ days)."}

    for l in logs:
        l["_d"] = str(l.get("log_date"))
    logs.sort(key=lambda l: l["_d"])
    cutoff = str(date.today() - timedelta(days=7))
    recent = [l for l in logs if l["_d"] >= cutoff]
    baseline = [l for l in logs if l["_d"] < cutoff] or logs

    metrics = ["mood", "sleep_hours", "sleep_quality", "study_hours", "stress"]
    higher_is_worse = {"stress"}
    out = {}
    concerning = []
    for m in metrics:
        r, b = _avg(recent, m), _avg(baseline, m)
        if r is None or b is None:
            continue
        delta = round(r - b, 2)
        worse = (delta > 0.5) if m in higher_is_worse else (delta < -0.5)
        out[m] = {"recent_7d_avg": r, "baseline_avg": b, "change": delta,
                  "direction": "worse" if worse else ("better" if abs(delta) > 0.5 else "stable")}
        if worse:
            concerning.append(m)
    return {"per_metric": out, "concerning_metrics": concerning,
            "days_of_data": len(logs)}


def _tool_get_crisis_resources() -> dict:
    return {"resources": CRISIS_RESOURCES}


def _run_tool(name: str, user_id: str) -> dict:
    try:
        if name == "get_user_summary":
            return _tool_get_user_summary(user_id)
        if name == "get_trend_analysis":
            return _tool_get_trend_analysis(user_id)
        if name == "get_crisis_resources":
            return _tool_get_crisis_resources()
        return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"error": f"Tool failed: {type(e).__name__}"}


# ----------------------------------------------------------------------
# The agent loop
# ----------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are the Wellbeing Agent inside a student wellbeing check-in app. "
    "You help students reflect on their mood, sleep, stress, and study "
    "patterns using their OWN check-in data, which you can fetch with tools.\n\n"
    "Rules you must always follow:\n"
    "1. NEVER diagnose or name any mental-health condition. You are not a "
    "therapist and must say so if asked for therapy.\n"
    "2. Ground your answers in tool data when the question is about the "
    "student's patterns — call a tool rather than guessing.\n"
    "3. Be warm, brief, and concrete. 2-5 sentences for most replies. "
    "Suggest small, doable actions (a walk, a fixed sleep time, a short "
    "break), never sweeping life changes.\n"
    "4. Never mention 'z-scores', 'flags', or internal system mechanics. "
    "Speak like a supportive senior, not a dashboard.\n"
    "5. If the student seems to need real support, gently point them to "
    "the helplines via get_crisis_resources.\n"
    "6. Never claim the app or you can treat, cure, or monitor anyone."
)

_FALLBACK_REPLY = (
    "I'm having trouble reaching my reasoning service right now — but your "
    "check-ins are safe, and the dashboard has your recent patterns. "
    "Please try me again in a moment."
)


def run_agent(user_id: str, message: str, history: list) -> dict:
    """
    Run one agent turn.

    Returns:
      {
        "reply": str,
        "tools_used": [str],       # for the UI to display agent actions
        "crisis": bool,            # True if deterministic pre-screen fired
      }
    """
    # 1. Deterministic safety pre-screen — LLM never sees crisis messages
    if crisis_prescreen(message):
        return {"reply": CRISIS_RESPONSE, "tools_used": [], "crisis": True}

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {"reply": _FALLBACK_REPLY, "tools_used": [], "crisis": False}

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in history[-8:]:  # cap context
            role = turn.get("role")
            if role in ("user", "assistant") and turn.get("content"):
                messages.append({"role": role, "content": turn["content"]})
        messages.append({"role": "user", "content": message})

        tools_used = []

        for _ in range(MAX_TOOL_ROUNDS):
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=400,
                temperature=0.6,
            )
            msg = response.choices[0].message

            if not msg.tool_calls:
                reply = (msg.content or "").strip()
                return {
                    "reply": reply or _FALLBACK_REPLY,
                    "tools_used": tools_used,
                    "crisis": False,
                }

            # The agent chose to act — execute its tool calls
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                tools_used.append(tc.function.name)
                result = _run_tool(tc.function.name, user_id)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        # Ran out of rounds — force a final answer without tools
        final = client.chat.completions.create(
            model=MODEL, messages=messages, max_tokens=300, temperature=0.6,
        )
        reply = (final.choices[0].message.content or "").strip()
        return {"reply": reply or _FALLBACK_REPLY,
                "tools_used": tools_used, "crisis": False}

    except Exception:
        return {"reply": _FALLBACK_REPLY, "tools_used": [], "crisis": False}
