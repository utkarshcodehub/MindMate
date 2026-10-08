"""
groq_client.py

Generates warm, contextual nudge messages using Groq LLaMA.

CRITICAL DESIGN RULE: This module writes copy only. It never makes
any risk assessment, safety decision, or flag determination. All of
those are made by the deterministic engine before this is called.
The engine decides IF something gets shown; this module only decides
HOW it is worded.

Fails gracefully in both directions:
  - GROQ_API_KEY not set  -> static fallback, no crash
  - API call fails        -> static fallback, no crash

Static fallbacks are good enough to ship; Groq just makes them warmer.
"""

import os
from dotenv import load_dotenv

load_dotenv()

METRIC_FRIENDLY = {
    "mood":          "mood",
    "sleep_hours":   "sleep",
    "sleep_quality": "sleep quality",
    "study_hours":   "energy for studying",
    "stress":        "stress levels",
}

_SOFT_FALLBACK = (
    "Hey — we noticed things have felt a bit heavier than usual lately. "
    "That's completely okay, and you don't have to figure it out all at once. "
    "Is there one small thing you could do for yourself today?"
)

_HARD_FALLBACK = (
    "It sounds like the last stretch has been genuinely tough. "
    "You don't have to carry this alone — please consider reaching out "
    "to someone you trust, or one of the support services listed below."
)


def generate_nudge_message(
    flag_type: str,
    concerning_metrics: list,
    consecutive_days: int,
) -> str:
    """
    Generate a contextual nudge message for soft_nudge or hard_flag.

    Parameters
    ----------
    flag_type          : 'soft_nudge' or 'hard_flag'
    concerning_metrics : list of metric names that triggered
                         e.g. ['mood', 'sleep_hours']
    consecutive_days   : longest streak among the concerning metrics
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return _fallback(flag_type)

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        friendly = [METRIC_FRIENDLY.get(m, m) for m in concerning_metrics]
        metrics_str = ", ".join(friendly) if friendly else "a few things"

        if flag_type == "soft_nudge":
            user_prompt = (
                f"A student has been having a harder time than usual with "
                f"{metrics_str} for about {consecutive_days} days. "
                "Write a warm, brief check-in message (2-3 sentences max). "
                "Do not mention data, scores, AI, or any diagnosis. "
                "End with one gentle, concrete suggestion they could try today."
            )
        else:
            user_prompt = (
                f"A student has been struggling with {metrics_str} "
                f"for {consecutive_days} days. "
                "Write a warm 2-sentence message acknowledging they've had "
                "a tough stretch and gently encouraging them to reach out "
                "for support. Do not mention data, scores, or AI."
            )

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write brief, warm check-in messages for a student "
                        "wellbeing app. Rules: never diagnose, never mention AI "
                        "or data, never use clinical language, keep to 2-3 "
                        "sentences maximum, be human and gentle, never catastrophize."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=120,
            temperature=0.7,
        )

        message = response.choices[0].message.content.strip()
        return message if message else _fallback(flag_type)

    except Exception:
        # Never let a Groq failure crash the daily log endpoint.
        # The flag decision is already made; only the copy is missing.
        return _fallback(flag_type)


def _fallback(flag_type: str) -> str:
    return _SOFT_FALLBACK if flag_type == "soft_nudge" else _HARD_FALLBACK