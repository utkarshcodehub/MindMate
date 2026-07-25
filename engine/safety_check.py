"""
safety_check.py

This module handles ONE thing: the PHQ-9 item 9 question ("thoughts that
you would be better off dead or of hurting yourself in some way").

This is deliberately the simplest file in the entire project. There is no
threshold tuning, no baseline, no persistence requirement, no LLM call, and
no judgment call of any kind. The rule is: ANY nonzero response routes to
crisis resources, immediately, every time, no exceptions.

Per the project's locked design (Option C from planning):
- Asked at onboarding
- Re-asked on a fixed 2-week cadence regardless of trend state (catches
  masking -- a person whose daily logs look stable but who is privately
  struggling)
- Re-asked immediately whenever the trend engine fires a hard_flag

This module does not decide WHEN to ask the question (that's the caller's
job, driven by the cadence/trigger rules above). It only decides what to do
with the answer once given.
"""

from dataclasses import dataclass
import pandas as pd

CRISIS_RESOURCES = [
    {"name": "iCall (Tata Institute of Social Sciences)", "phone": "9152987821", "hours": "Mon-Sat, 8am-10pm"},
    {"name": "Vandrevala Foundation", "phone": "1860-2662-345 / 1800-2333-330", "hours": "24/7"},
    {"name": "NIMHANS", "phone": "080-46110007", "hours": "24/7"},
]


@dataclass
class SafetyCheckResult:
    user_id: str
    check_date: pd.Timestamp
    trigger_source: str  # 'onboarding' | 'scheduled_2wk' | 'hard_flag_triggered'
    item9_response: int  # 0-3
    crisis_path_fired: bool
    resources_shown: list


def evaluate_item9(
    user_id: str,
    check_date: pd.Timestamp,
    trigger_source: str,
    item9_response: int,
) -> SafetyCheckResult:
    """
    The entire safety-critical decision, in one line of logic by design:
    any nonzero response fires the crisis path. No severity tiers, no
    "mild" vs "severe" distinction here -- that nuance belongs to a
    qualified professional, not this system. A response of 1 ("several
    days") gets the exact same resources as a response of 3 ("nearly
    every day"), because this system's job is to route to help, not to
    triage how urgently.
    """
    if item9_response not in (0, 1, 2, 3):
        raise ValueError(
            f"item9_response must be 0-3, got {item9_response}. "
            "Refusing to silently coerce an out-of-range value on a safety-critical check."
        )

    crisis_path_fired = item9_response > 0

    return SafetyCheckResult(
        user_id=user_id,
        check_date=check_date,
        trigger_source=trigger_source,
        item9_response=item9_response,
        crisis_path_fired=crisis_path_fired,
        resources_shown=CRISIS_RESOURCES if crisis_path_fired else [],
    )


def next_scheduled_check_date(last_check_date: pd.Timestamp, cadence_days: int = 14) -> pd.Timestamp:
    """
    Simple helper for the fixed-cadence trigger. In production this would
    be a scheduled job (cron / Supabase Edge Function) that queries for
    users whose last safety_check is >= cadence_days old and surfaces the
    question to them.
    """
    return last_check_date + pd.Timedelta(days=cadence_days)
