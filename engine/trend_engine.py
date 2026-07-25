"""
trend_engine.py

Takes a user's daily log + their baseline stats, and answers:
"is this metric, today, meaningfully different from this person's normal?"

Two independent detection mechanisms, because they catch different shapes
of decline:

1. Z-SCORE (deviation): "is today's value unusually far from baseline?"
   Catches sharp drops / sudden crashes.

2. SLOPE (trend): "has this metric been steadily moving in the concerning
   direction over the last N days, even if no single day looks extreme?"
   Catches slow bleeds that never cross a Z-score threshold on any one day.

Either one firing is enough to register concern for a metric on a given day.
Neither of these decides the final flag by itself -- that's combination_rules.py.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional
from scipy import stats as scipy_stats

from .baseline import BaselineStats

# Which direction is "concerning" for each metric.
# 'low' = a drop below baseline is concerning
# 'high' = a rise above baseline is concerning
CONCERNING_DIRECTION = {
    "mood": "low",
    "sleep_hours": "low",
    "sleep_quality": "low",
    "stress": "high",
    "study_hours": None,  # handled contextually in combination_rules.py, not here
}

Z_THRESHOLD_NOTABLE = -1.5
Z_THRESHOLD_SIGNIFICANT = -2.0
Z_THRESHOLD_EXTREME = -3.0

SLOPE_WINDOW_DAYS = 10
SLOPE_MIN_POINTS = 6  # need at least this many points in the window to trust a slope

# Minimum standard deviation to use when computing Z-scores, per metric.
# Without this floor, a person who happened to have unusually flat/stable
# baseline weeks (e.g. sleep_hours std of 0.05) would get wildly inflated
# Z-scores for completely ordinary day-to-day variation -- a single normal
# night of slightly worse sleep would read as a multi-sigma "extreme" event
# purely because their recent history was abnormally steady. These floors
# are rough domain judgment calls (tunable in Phase 7), representing "the
# smallest change in this metric that should ever count as one full unit
# of deviation," regardless of how flat someone's recent baseline was.
MIN_STD_FLOOR = {
    "mood": 0.4,          # on a 1-5 scale
    "sleep_hours": 0.5,   # half an hour
    "sleep_quality": 0.4, # on a 1-5 scale
    "study_hours": 0.5,
    "stress": 0.6,        # on a 1-10 scale
}


@dataclass
class MetricSignal:
    metric: str
    value: float
    z_score: Optional[float]
    z_severity: str  # 'none' | 'notable' | 'significant' | 'extreme'
    slope: Optional[float]
    slope_concerning: bool
    concern: bool  # the combined verdict for THIS metric alone


def compute_z_score(value: float, baseline: BaselineStats, metric: str) -> float:
    """
    Standard Z-score: how many standard deviations is this value from
    this person's own baseline mean?

    Applies MIN_STD_FLOOR for the metric to avoid division by a near-zero
    standard deviation inflating ordinary variation into a false "extreme"
    reading (see module docstring / MIN_STD_FLOOR comment for why).
    """
    floor = MIN_STD_FLOOR.get(metric, 0.3)
    std = max(baseline.std, floor)
    return (value - baseline.mean) / std


def classify_z_severity(z: float, direction: str) -> str:
    """
    Map a raw Z-score to a severity label, taking into account which
    direction is concerning for this metric.

    For 'low' direction metrics (mood, sleep), concerning Z is negative.
    For 'high' direction metrics (stress), concerning Z is positive --
    so we flip the sign before comparing against the same thresholds,
    to avoid duplicating the threshold logic for both directions.
    """
    effective_z = z if direction == "low" else -z

    if effective_z <= Z_THRESHOLD_EXTREME:
        return "extreme"
    elif effective_z <= Z_THRESHOLD_SIGNIFICANT:
        return "significant"
    elif effective_z <= Z_THRESHOLD_NOTABLE:
        return "notable"
    return "none"


def compute_slope(daily_logs: pd.DataFrame, user_id: str, metric: str,
                   as_of_date: pd.Timestamp, window_days: int = SLOPE_WINDOW_DAYS) -> Optional[float]:
    """
    Fit a simple linear regression (value vs. day-index) over the trailing
    window and return the slope -- units are "metric change per day."

    A negative slope means the metric is declining day over day; positive
    means rising. Direction of "concern" depends on the metric (handled by
    caller), this function just returns the raw number.

    Returns None if there aren't enough points in the window to trust a
    slope estimate (avoids fitting a line through 2-3 noisy points and
    over-interpreting it).
    """
    user_logs = daily_logs[daily_logs["user_id"] == user_id].copy()
    user_logs["log_date"] = pd.to_datetime(user_logs["log_date"])

    window_start = as_of_date - pd.Timedelta(days=window_days)
    mask = (user_logs["log_date"] >= window_start) & (user_logs["log_date"] <= as_of_date)
    window_data = user_logs.loc[mask].sort_values("log_date")
    window_data = window_data.dropna(subset=[metric])

    if len(window_data) < SLOPE_MIN_POINTS:
        return None

    day_indices = np.arange(len(window_data))
    values = window_data[metric].values

    slope, _intercept, _r, _p, _se = scipy_stats.linregress(day_indices, values)
    return float(slope)


def evaluate_metric(
    daily_logs: pd.DataFrame,
    user_id: str,
    metric: str,
    today_value: float,
    as_of_date: pd.Timestamp,
    baseline: Optional[BaselineStats],
) -> MetricSignal:
    """
    Full single-metric evaluation: compute Z-score severity AND slope,
    decide if either independently signals concern for this metric today.
    """
    direction = CONCERNING_DIRECTION.get(metric)

    z = None
    z_severity = "none"
    if baseline is not None and direction is not None:
        z = compute_z_score(today_value, baseline, metric)
        z_severity = classify_z_severity(z, direction)

    slope = compute_slope(daily_logs, user_id, metric, as_of_date)
    slope_concerning = False
    if slope is not None and direction is not None:
        # A "meaningful" slope threshold depends on the metric's natural
        # scale -- a slope of -0.1/day on a 1-5 mood scale over 10 days is
        # a full point of decline, which is substantial. This threshold is
        # a heuristic to be tuned in Phase 7, not a derived constant.
        slope_threshold = 0.08
        if direction == "low" and slope <= -slope_threshold:
            slope_concerning = True
        elif direction == "high" and slope >= slope_threshold:
            slope_concerning = True

    concern = (z_severity != "none") or slope_concerning

    return MetricSignal(
        metric=metric,
        value=today_value,
        z_score=z,
        z_severity=z_severity,
        slope=slope,
        slope_concerning=slope_concerning,
        concern=concern,
    )
