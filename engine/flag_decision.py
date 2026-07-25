"""
flag_decision.py

This is the orchestration layer that ties everything together:
- Calls evaluate_metric() for every tracked metric, every day
- Tracks CONSECUTIVE days of concern per metric (single-day concern isn't
  enough on its own except for extreme crashes -- see PERSISTENCE rules)
- Applies cross-metric combination logic (mood+sleep together matters more
  than either alone; stress alone, explained by workload, gets suppressed)
- Produces the final decision: 'none' | 'soft_nudge' | 'hard_flag'

State is intentionally explicit (UserTrendState), not hidden in globals,
since this needs to persist across days in a real system (one row per user
in your DB, updated daily) -- this module just defines the pure logic that
operates on that state.
"""

import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

from .trend_engine import evaluate_metric, MetricSignal
from .baseline import compute_baseline, METRICS

# Persistence thresholds (consecutive days of concern required)
SOFT_NUDGE_MOOD_ALONE_DAYS = 3       # mood concern alone, sustained
SOFT_NUDGE_GENERAL_DAYS = 3          # 1-2 metrics concerning, sustained
HARD_FLAG_MULTI_METRIC_DAYS = 3      # 3+ metrics concerning together, sustained
HARD_FLAG_MOOD_SLEEP_DAYS = 5        # mood+sleep together, sustained (depression/burnout shape)
EXTREME_Z_BYPASS = True              # a single extreme-Z day can hard-flag immediately, no persistence needed


@dataclass
class UserTrendState:
    """
    Tracks consecutive-day streaks of concern per metric for one user.
    In production this gets loaded from / saved to the DB once per
    evaluation; here it's just an in-memory object for clarity.
    """
    user_id: str
    consecutive_concern_days: dict = field(default_factory=lambda: {m: 0 for m in METRICS})
    consecutive_extreme_days: dict = field(default_factory=lambda: {m: 0 for m in METRICS})
    flagged_dates: set = field(default_factory=set)

    def update(self, metric: str, concerning_today: bool, extreme_today: bool):
        if concerning_today:
            self.consecutive_concern_days[metric] += 1
        else:
            self.consecutive_concern_days[metric] = 0

        if extreme_today:
            self.consecutive_extreme_days[metric] += 1
        else:
            self.consecutive_extreme_days[metric] = 0


@dataclass
class DailyFlagResult:
    date: pd.Timestamp
    flag_type: str  # 'none' | 'soft_nudge' | 'hard_flag'
    triggering_metrics: dict  # metric -> MetricSignal, for auditability
    reason: str  # human-readable explanation of WHY this fired


def evaluate_day(
    daily_logs: pd.DataFrame,
    state: UserTrendState,
    as_of_date: pd.Timestamp,
) -> DailyFlagResult:
    """
    Run the full pipeline for one user, one day:
    1. Evaluate each metric independently (Z-score + slope)
    2. Update consecutive-day counters
    3. Apply combination + suppression rules
    4. Return the final flag decision
    """
    user_id = state.user_id
    today_row = daily_logs[
        (daily_logs["user_id"] == user_id) & (pd.to_datetime(daily_logs["log_date"]) == as_of_date)
    ]

    if today_row.empty:
        # No log for today -- can't evaluate. In production this might itself
        # be worth tracking (missed check-ins are their own signal), but
        # that's a separate feature, not part of this engine's job.
        return DailyFlagResult(as_of_date, "none", {}, "No log entry for this date.")

    today_row = today_row.iloc[0]
    signals = {}

    for metric in METRICS:
        baseline = compute_baseline(
            daily_logs, user_id, metric, as_of_date,
            flagged_dates=state.flagged_dates
        )
        signal = evaluate_metric(
            daily_logs, user_id, metric, today_row[metric], as_of_date, baseline
        )
        signals[metric] = signal
        state.update(metric, signal.concern, signal.z_severity == "extreme")

    result = _decide(signals, state, as_of_date)

    # Any day that contributed to a non-'none' decision is excluded from
    # future baseline calculations, so sustained concern can't quietly drag
    # the baseline down with it (see baseline.py docstring for why this
    # matters).
    if result.flag_type != "none":
        state.flagged_dates.add(as_of_date)

    return result


def _decide(signals: dict, state: UserTrendState, as_of_date: pd.Timestamp) -> DailyFlagResult:
    """
    Pure decision logic, separated out so evaluate_day() can guarantee the
    flagged_dates bookkeeping happens exactly once, regardless of which
    branch below fires.
    """

    # --- Suppression rule: stress AND sleep loss explained by workload spike ---
    stress_signal = signals["stress"]
    study_signal = signals["study_hours"]
    sleep_signal = signals["sleep_hours"]
    sleep_q_signal = signals["sleep_quality"]

    workload_rising = study_signal.slope is not None and study_signal.slope >= 0.1

    workload_explains_stress = stress_signal.concern and workload_rising
    workload_explains_sleep = (
        (sleep_signal.concern or sleep_q_signal.concern) and workload_rising
    )

    mood_concern = signals["mood"].concern
    sleep_concern_unexplained = (sleep_signal.concern or sleep_q_signal.concern) and not workload_explains_sleep
    stress_concern_unexplained = stress_signal.concern and not workload_explains_stress

    if (
        not mood_concern
        and not sleep_concern_unexplained
        and not stress_concern_unexplained
        and (workload_explains_stress or workload_explains_sleep)
    ):
        # Stress and/or sleep loss are both explained by a rising workload
        # (study hours trending up), and mood is not independently
        # concerning. This is the exam-week shape, not escalating burnout.
        return DailyFlagResult(
            as_of_date, "none", signals,
            "Stress/sleep changes explained by rising study hours (workload spike); "
            "mood remains within normal range. Suppressed as likely exam-period stress."
        )

    # --- Extreme deviation bypass: still requires 2 consecutive extreme days,
    # NOT a single day. A single extreme day, even Z<=-3, could be one bad
    # night -- it's the PERSISTENCE of an extreme deviation that justifies
    # skipping the longer 3-5 day persistence window used for moderate
    # concern. (Caught via testing: an unconditional single-day bypass made
    # the system hard-flag on literally the first abnormal day for any user
    # with low day-to-day variance, defeating the point of persistence.)
    extreme_metrics = [
        m for m, s in signals.items()
        if s.z_severity == "extreme" and state.consecutive_extreme_days[m] >= 2
    ]
    if EXTREME_Z_BYPASS and extreme_metrics:
        return DailyFlagResult(
            as_of_date, "hard_flag", signals,
            f"Extreme deviation sustained 2+ days in: {', '.join(extreme_metrics)}."
        )

    sleep_concern = sleep_signal.concern or sleep_q_signal.concern

    # --- Count how many metrics show sustained concern today ---
    concerning_count = sum(1 for s in signals.values() if s.concern)

    # --- Hard flag: mood + sleep together, sustained ---
    mood_streak = state.consecutive_concern_days["mood"]
    sleep_streak = max(
        state.consecutive_concern_days["sleep_hours"],
        state.consecutive_concern_days["sleep_quality"],
    )
    if mood_concern and sleep_concern and min(mood_streak, sleep_streak) >= HARD_FLAG_MOOD_SLEEP_DAYS:
        return DailyFlagResult(
            as_of_date, "hard_flag", signals,
            f"Mood and sleep both concerning for {HARD_FLAG_MOOD_SLEEP_DAYS}+ consecutive days -- "
            "pattern consistent with sustained burnout/low-mood escalation."
        )

    # --- Hard flag: 3+ metrics concerning simultaneously, sustained ---
    if concerning_count >= 3 and all(
        state.consecutive_concern_days[m] >= HARD_FLAG_MULTI_METRIC_DAYS
        for m, s in signals.items() if s.concern
    ):
        return DailyFlagResult(
            as_of_date, "hard_flag", signals,
            f"{concerning_count} metrics concerning simultaneously for "
            f"{HARD_FLAG_MULTI_METRIC_DAYS}+ consecutive days."
        )

    # --- Soft nudge: mood alone, sustained ---
    if mood_concern and mood_streak >= SOFT_NUDGE_MOOD_ALONE_DAYS:
        return DailyFlagResult(
            as_of_date, "soft_nudge", signals,
            f"Mood concerning for {mood_streak} consecutive days."
        )

    # --- Soft nudge: any 1-2 metrics concerning, sustained ---
    if 1 <= concerning_count <= 2:
        max_streak = max(
            state.consecutive_concern_days[m] for m, s in signals.items() if s.concern
        )
        if max_streak >= SOFT_NUDGE_GENERAL_DAYS:
            concerning_names = [m for m, s in signals.items() if s.concern]
            return DailyFlagResult(
                as_of_date, "soft_nudge", signals,
                f"{', '.join(concerning_names)} concerning for {max_streak}+ consecutive days."
            )

    return DailyFlagResult(as_of_date, "none", signals, "No concerning pattern detected.")
