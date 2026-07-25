"""
baseline.py

Computes each user's personal rolling baseline (mean + standard deviation)
for every tracked metric. This baseline is what every later trend/Z-score
calculation compares against -- the whole system is built on the idea of
"deviation from YOUR normal," not deviation from some population average.

Design decisions worth remembering:
- Window size default is 14 days. Shorter windows react faster but are
  noisier; longer windows are more stable but slower to adapt to a genuinely
  new normal (e.g. a student who permanently shifted their sleep schedule).
- Metrics where "lower is concerning" and "higher is concerning" differ per
  metric -- that direction logic lives in trend_engine.py, not here. This
  module only computes the neutral mean/std, no judgment about direction.
- Cold start: if fewer than MIN_DAYS_FOR_BASELINE rows exist, we return None
  for that user/metric rather than computing an unstable baseline off too
  few points. Callers MUST handle the None case explicitly.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional

DEFAULT_WINDOW_DAYS = 14
MIN_DAYS_FOR_BASELINE = 10  # need at least this many days before trusting a baseline

METRICS = ["mood", "sleep_hours", "sleep_quality", "study_hours", "stress"]


@dataclass
class BaselineStats:
    user_id: str
    metric: str
    mean: float
    std: float
    window_days: int
    n_observations: int


def compute_baseline(
    daily_logs: pd.DataFrame,
    user_id: str,
    metric: str,
    as_of_date: pd.Timestamp,
    window_days: int = DEFAULT_WINDOW_DAYS,
    flagged_dates: Optional[set] = None,
    max_lookback_days: int = 60,
) -> Optional[BaselineStats]:
    """
    Compute rolling mean/std for one user, one metric, looking backward
    from as_of_date (exclusive of as_of_date itself).

    IMPORTANT: flagged_dates should contain every date that was part of an
    active soft_nudge or hard_flag for this user. Those dates are EXCLUDED
    from the baseline window. Without this exclusion, a sustained decline
    contaminates its own baseline -- the rolling mean drifts downward along
    with the decline, masking the very deviation we're trying to detect.
    (Confirmed by testing: a 14-day trailing window starting to overlap
    declining days pulled the mean down ~12%, understating the true Z-score.)

    Because excluding flagged days shrinks the available pool, we search
    backward up to max_lookback_days to find enough clean (non-flagged)
    observations to satisfy MIN_DAYS_FOR_BASELINE, rather than strictly
    using the most recent window_days calendar days.

    Returns None if there isn't enough clean history yet (cold start, or
    everything in range has been flagged).
    """
    flagged_dates = flagged_dates or set()

    user_logs = daily_logs[daily_logs["user_id"] == user_id].copy()
    user_logs["log_date"] = pd.to_datetime(user_logs["log_date"])
    user_logs = user_logs.sort_values("log_date")

    lookback_start = as_of_date - pd.Timedelta(days=max_lookback_days)
    candidate_mask = (user_logs["log_date"] >= lookback_start) & (user_logs["log_date"] < as_of_date)
    candidates = user_logs.loc[candidate_mask].copy()

    # Exclude any day that was part of an active flag
    candidates = candidates[~candidates["log_date"].isin(flagged_dates)]

    # Take the most recent `window_days` worth of CLEAN observations
    clean_data = candidates.sort_values("log_date", ascending=False).head(window_days)
    metric_values = clean_data[metric].dropna()

    if len(metric_values) < MIN_DAYS_FOR_BASELINE:
        return None

    return BaselineStats(
        user_id=user_id,
        metric=metric,
        mean=float(metric_values.mean()),
        std=float(metric_values.std(ddof=1)),  # sample std, not population std
        window_days=window_days,
        n_observations=len(metric_values),
    )


def compute_all_baselines(
    daily_logs: pd.DataFrame,
    user_id: str,
    as_of_date: pd.Timestamp,
    window_days: int = DEFAULT_WINDOW_DAYS,
    flagged_dates: Optional[set] = None,
) -> dict:
    """
    Convenience wrapper: compute baseline for every tracked metric at once.
    Returns a dict of {metric_name: BaselineStats or None}.
    """
    return {
        metric: compute_baseline(daily_logs, user_id, metric, as_of_date, window_days, flagged_dates)
        for metric in METRICS
    }
