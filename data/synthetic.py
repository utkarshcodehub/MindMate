"""
synthetic.py

Generates realistic daily-log sequences for 8 distinct user behavioral
patterns, for use in Phase 7 engine validation.

Every scenario has an expected_outcome -- what the engine SHOULD do over
the course of the scenario. The validator in validate.py runs each scenario
through the full pipeline and checks actual vs expected, flagging any
discrepancy as a threshold/logic problem to investigate.

Why synthetic and not real data: we can't ethically collect labeled data
(real users at genuine risk) in a student project timeframe. Synthetic
data at least lets us confirm the engine behaves correctly on the shapes
of trajectory we designed it for, and catch regressions when we tune
thresholds. It's a substitute for a real validation study, not a claim
of clinical validation -- and we say so explicitly in the README.

Noise model: each metric gets Gaussian noise added (std = NOISE_STD[metric])
to avoid suspiciously perfect data. Real daily logs are always noisy, and
the engine needs to handle that without over-triggering.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional

NOISE_STD = {
    "mood": 0.3,
    "sleep_hours": 0.4,
    "sleep_quality": 0.3,
    "study_hours": 0.5,
    "stress": 0.5,
}

METRIC_BOUNDS = {
    "mood": (1, 5),
    "sleep_hours": (3, 10),
    "sleep_quality": (1, 5),
    "study_hours": (0, 14),
    "stress": (1, 10),
}


@dataclass
class Scenario:
    name: str
    description: str
    user_id: str
    df: pd.DataFrame
    dates: pd.DatetimeIndex
    expected_flags: dict  # {day_index: 'none'|'soft_nudge'|'hard_flag'} for key days


def _clip(values: np.ndarray, metric: str) -> np.ndarray:
    lo, hi = METRIC_BOUNDS[metric]
    return np.clip(np.round(values, 1), lo, hi)


def _add_noise(base: np.ndarray, metric: str, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noisy = base + rng.normal(0, NOISE_STD[metric], size=len(base))
    return _clip(noisy, metric)


def _build_df(user_id: str, metrics: dict, start: str = "2026-01-01") -> tuple:
    n = len(next(iter(metrics.values())))
    dates = pd.date_range(start=start, periods=n, freq="D")
    df = pd.DataFrame({"user_id": user_id, "log_date": dates, **metrics})
    return df, dates


# -----------------------------------------------------------------------
# SCENARIO 1: Stable user — should never flag
# Mood/sleep/stress all within normal range throughout. Engine should stay
# at 'none' the whole time. Tests that low natural variance doesn't produce
# false positives.
# -----------------------------------------------------------------------
def scenario_stable() -> Scenario:
    n = 30
    base_mood = np.full(n, 3.8)
    base_sleep = np.full(n, 7.2)
    base_sleep_q = np.full(n, 3.8)
    base_study = np.full(n, 4.2)
    base_stress = np.full(n, 3.5)

    df, dates = _build_df("user_stable", {
        "mood": _add_noise(base_mood, "mood", seed=1),
        "sleep_hours": _add_noise(base_sleep, "sleep_hours", seed=2),
        "sleep_quality": _add_noise(base_sleep_q, "sleep_quality", seed=3),
        "study_hours": _add_noise(base_study, "study_hours", seed=4),
        "stress": _add_noise(base_stress, "stress", seed=5),
    })

    return Scenario(
        name="Stable user",
        description="All metrics normal throughout. Should never flag.",
        user_id="user_stable",
        df=df,
        dates=dates,
        expected_flags={
            14: "none", 18: "none", 22: "none", 28: "none"
        }
    )


# -----------------------------------------------------------------------
# SCENARIO 2: Gradual decline — slow bleed that slope detection should catch
# No single day looks extreme, but everything trends slowly downward from
# day 15 onward. Z-score alone might miss this; slope detection should catch
# it. Tests the slope mechanism specifically.
# -----------------------------------------------------------------------
def scenario_gradual_decline() -> Scenario:
    n_stable = 17
    n_decline = 16

    # Stable baseline
    mood_s = np.full(n_stable, 3.8)
    sleep_s = np.full(n_stable, 7.2)
    sleep_q_s = np.full(n_stable, 3.8)
    study_s = np.full(n_stable, 4.2)
    stress_s = np.full(n_stable, 3.5)

    # Gradual decline: small daily steps, not a cliff
    mood_d = np.linspace(3.5, 2.0, n_decline)
    sleep_d = np.linspace(7.0, 5.5, n_decline)
    sleep_q_d = np.linspace(3.5, 2.0, n_decline)
    study_d = np.linspace(4.0, 2.5, n_decline)
    stress_d = np.linspace(4.0, 6.5, n_decline)

    df, dates = _build_df("user_gradual", {
        "mood": _add_noise(np.concatenate([mood_s, mood_d]), "mood", seed=10),
        "sleep_hours": _add_noise(np.concatenate([sleep_s, sleep_d]), "sleep_hours", seed=11),
        "sleep_quality": _add_noise(np.concatenate([sleep_q_s, sleep_q_d]), "sleep_quality", seed=12),
        "study_hours": _add_noise(np.concatenate([study_s, study_d]), "study_hours", seed=13),
        "stress": _add_noise(np.concatenate([stress_s, stress_d]), "stress", seed=14),
    })

    return Scenario(
        name="Gradual decline",
        description="Slow multi-metric bleed from day 18. No single day looks extreme. "
                    "Slope detection should catch it before Z-scores do.",
        user_id="user_gradual",
        df=df,
        dates=dates,
        expected_flags={
            16: "none",          # still in stable window
            22: "soft_nudge",    # slope-based concern should start appearing
            28: "hard_flag",     # sustained multi-metric by now
        }
    )


# -----------------------------------------------------------------------
# SCENARIO 3: Sudden crash — sharp single-event drop, Z-score bypass path
# Two consecutive extreme-Z days on multiple metrics, no gradual lead-up.
# Tests the 2-consecutive-extreme-days bypass (the "something happened
# suddenly" case -- not gradual burnout, but an acute crisis event).
# -----------------------------------------------------------------------
def scenario_sudden_crash() -> Scenario:
    n_stable = 16
    n_crash = 6

    mood_s = np.full(n_stable, 3.9)
    sleep_s = np.full(n_stable, 7.5)
    sleep_q_s = np.full(n_stable, 4.0)
    study_s = np.full(n_stable, 4.5)
    stress_s = np.full(n_stable, 3.2)

    # Sharp crash: values immediately plummet, no gradual warning
    mood_c = np.full(n_crash, 1.3)
    sleep_c = np.full(n_crash, 4.5)
    sleep_q_c = np.full(n_crash, 1.5)
    study_c = np.full(n_crash, 1.5)
    stress_c = np.full(n_crash, 8.5)

    df, dates = _build_df("user_crash", {
        "mood": _add_noise(np.concatenate([mood_s, mood_c]), "mood", seed=20),
        "sleep_hours": _add_noise(np.concatenate([sleep_s, sleep_c]), "sleep_hours", seed=21),
        "sleep_quality": _add_noise(np.concatenate([sleep_q_s, sleep_q_c]), "sleep_quality", seed=22),
        "study_hours": _add_noise(np.concatenate([study_s, study_c]), "study_hours", seed=23),
        "stress": _add_noise(np.concatenate([stress_s, stress_c]), "stress", seed=24),
    })

    return Scenario(
        name="Sudden crash",
        description="Sharp multi-metric drop after stable baseline. "
                    "Should hard_flag within 2 days of crash via extreme bypass.",
        user_id="user_crash",
        df=df,
        dates=dates,
        expected_flags={
            15: "none",          # last stable day
            17: "hard_flag",     # 2 extreme days hit, bypass fires
            20: "hard_flag",     # still flagging
        }
    )


# -----------------------------------------------------------------------
# SCENARIO 4: Masking user — logs look "okay" but quietly declining
# This is the hardest case. User is masking: they consistently report
# slightly above their actual state (as you noted in the original write-up,
# people in distress underreport). Represented here as values that hover
# just inside the "concerning" boundary but with a real downward trend.
# The slope detection's job is to catch what Z-scores can't.
# -----------------------------------------------------------------------
def scenario_masking() -> Scenario:
    n_stable = 16
    n_mask = 16

    mood_s = np.full(n_stable, 3.5)
    sleep_s = np.full(n_stable, 7.0)
    sleep_q_s = np.full(n_stable, 3.5)
    study_s = np.full(n_stable, 4.0)
    stress_s = np.full(n_stable, 4.0)

    # Masking: small, consistent decline -- each day only slightly worse,
    # so individual Z-scores stay modest, but the slope is clear over time
    mood_m = np.linspace(3.3, 2.2, n_mask)
    sleep_m = np.linspace(6.8, 5.8, n_mask)
    sleep_q_m = np.linspace(3.3, 2.3, n_mask)
    study_m = np.linspace(4.0, 3.0, n_mask)
    stress_m = np.linspace(4.2, 5.5, n_mask)

    df, dates = _build_df("user_masking", {
        "mood": _add_noise(np.concatenate([mood_s, mood_m]), "mood", seed=30),
        "sleep_hours": _add_noise(np.concatenate([sleep_s, sleep_m]), "sleep_hours", seed=31),
        "sleep_quality": _add_noise(np.concatenate([sleep_q_s, sleep_q_m]), "sleep_quality", seed=32),
        "study_hours": _add_noise(np.concatenate([study_s, study_m]), "study_hours", seed=33),
        "stress": _add_noise(np.concatenate([stress_s, stress_m]), "stress", seed=34),
    })

    return Scenario(
        name="Masking user",
        description="User underreports distress. Small but consistent decline across all metrics. "
                    "No single extreme day. Slope detection should eventually catch it.",
        user_id="user_masking",
        df=df,
        dates=dates,
        expected_flags={
            16: "none",          # baseline period
            23: "soft_nudge",    # slope picks up sleep concern first, soft nudge appears
            25: "hard_flag",     # mood+sleep both concerning 5+ days by day 26 (index 25)
            31: "hard_flag",     # sustained multi-metric decline evident
        }
    )


# -----------------------------------------------------------------------
# SCENARIO 5: Exam week only — stress/sleep/study spike, mood stable
# Should be fully suppressed throughout. Tests that the suppression rule
# doesn't accidentally let a false positive through on a high-workload week.
# -----------------------------------------------------------------------
def scenario_exam_week() -> Scenario:
    n_stable = 16
    n_exam = 10

    mood_s = np.full(n_stable, 3.8)
    sleep_s = np.full(n_stable, 7.2)
    sleep_q_s = np.full(n_stable, 3.8)
    study_s = np.full(n_stable, 4.0)
    stress_s = np.full(n_stable, 3.5)

    # Exam week: study hours spike, stress up, sleep down -- but mood holds
    mood_e = np.full(n_exam, 3.5)     # slightly below normal but not low
    sleep_e = np.full(n_exam, 5.5)    # down due to late studying
    sleep_q_e = np.full(n_exam, 2.8)
    study_e = np.linspace(6.0, 8.0, n_exam)  # clearly rising
    stress_e = np.full(n_exam, 6.5)   # elevated

    df, dates = _build_df("user_exam", {
        "mood": _add_noise(np.concatenate([mood_s, mood_e]), "mood", seed=40),
        "sleep_hours": _add_noise(np.concatenate([sleep_s, sleep_e]), "sleep_hours", seed=41),
        "sleep_quality": _add_noise(np.concatenate([sleep_q_s, sleep_q_e]), "sleep_quality", seed=42),
        "study_hours": _add_noise(np.concatenate([study_s, study_e]), "study_hours", seed=43),
        "stress": _add_noise(np.concatenate([stress_s, stress_e]), "stress", seed=44),
    })

    return Scenario(
        name="Exam week",
        description="Classic high-workload period. Stress/sleep disrupted, "
                    "study hours clearly rising, mood stable. Should be fully suppressed.",
        user_id="user_exam",
        df=df,
        dates=dates,
        expected_flags={
            16: "none",
            20: "none",
            24: "none",
        }
    )


# -----------------------------------------------------------------------
# SCENARIO 6: Post-exam crash — exam ends but decline continues
# The tricky edge case: exam week (suppressed), then exams end, study hours
# drop back to normal -- but mood/sleep don't recover and keep declining.
# Now the workload-explains-stress suppression rule should NO LONGER fire,
# and the engine should start flagging the ongoing real decline.
# -----------------------------------------------------------------------
def scenario_post_exam_crash() -> Scenario:
    n_stable = 14
    n_exam = 8
    n_crash = 10

    # Stable
    mood_s = np.full(n_stable, 3.8)
    sleep_s = np.full(n_stable, 7.2)
    sleep_q_s = np.full(n_stable, 3.8)
    study_s = np.full(n_stable, 4.0)
    stress_s = np.full(n_stable, 3.5)

    # Exam week
    mood_e = np.full(n_exam, 3.4)
    sleep_e = np.full(n_exam, 5.5)
    sleep_q_e = np.full(n_exam, 2.8)
    study_e = np.linspace(6.0, 8.0, n_exam)
    stress_e = np.full(n_exam, 6.5)

    # Post-exam crash: study hours normalize, but mood/sleep/stress don't recover
    mood_c = np.linspace(3.2, 1.8, n_crash)
    sleep_c = np.linspace(5.5, 4.5, n_crash)
    sleep_q_c = np.linspace(2.8, 1.8, n_crash)
    study_c = np.full(n_crash, 3.5)  # back to normal -- no more exam excuse
    stress_c = np.linspace(6.5, 7.5, n_crash)  # stress stays high with no workload reason

    df, dates = _build_df("user_postexam", {
        "mood": _add_noise(np.concatenate([mood_s, mood_e, mood_c]), "mood", seed=50),
        "sleep_hours": _add_noise(np.concatenate([sleep_s, sleep_e, sleep_c]), "sleep_hours", seed=51),
        "sleep_quality": _add_noise(np.concatenate([sleep_q_s, sleep_q_e, sleep_q_c]), "sleep_quality", seed=52),
        "study_hours": _add_noise(np.concatenate([study_s, study_e, study_c]), "study_hours", seed=53),
        "stress": _add_noise(np.concatenate([stress_s, stress_e, stress_c]), "stress", seed=54),
    })

    return Scenario(
        name="Post-exam crash",
        description="Exam week (suppressed correctly), then exams end but decline continues. "
                    "Suppression should lift once study hours normalize and flagging should begin.",
        user_id="user_postexam",
        df=df,
        dates=dates,
        expected_flags={
            18: "none",          # still in exam week, suppressed
            24: "soft_nudge",    # post-exam, suppression lifted, decline visible
            30: "hard_flag",     # multi-metric sustained decline
        }
    )


# -----------------------------------------------------------------------
# SCENARIO 7: Recovery — decline, gets flagged, then genuinely recovers
# Tests that the engine correctly STOPS flagging when a user recovers.
# Flags should fire during the decline window, then drop back to 'none'
# once metrics return to baseline range. Consecutive counters must reset.
# -----------------------------------------------------------------------
def scenario_recovery() -> Scenario:
    n_stable = 14
    n_decline = 8
    n_recovery = 12

    mood_s = np.full(n_stable, 3.8)
    sleep_s = np.full(n_stable, 7.2)
    sleep_q_s = np.full(n_stable, 3.8)
    study_s = np.full(n_stable, 4.0)
    stress_s = np.full(n_stable, 3.5)

    mood_d = np.full(n_decline, 1.8)
    sleep_d = np.full(n_decline, 5.0)
    sleep_q_d = np.full(n_decline, 1.8)
    study_d = np.full(n_decline, 2.0)
    stress_d = np.full(n_decline, 7.5)

    mood_r = np.linspace(2.5, 3.9, n_recovery)
    sleep_r = np.linspace(6.0, 7.5, n_recovery)
    sleep_q_r = np.linspace(2.8, 4.0, n_recovery)
    study_r = np.linspace(3.0, 4.2, n_recovery)
    stress_r = np.linspace(6.0, 3.5, n_recovery)

    df, dates = _build_df("user_recovery", {
        "mood": _add_noise(np.concatenate([mood_s, mood_d, mood_r]), "mood", seed=60),
        "sleep_hours": _add_noise(np.concatenate([sleep_s, sleep_d, sleep_r]), "sleep_hours", seed=61),
        "sleep_quality": _add_noise(np.concatenate([sleep_q_s, sleep_q_d, sleep_q_r]), "sleep_quality", seed=62),
        "study_hours": _add_noise(np.concatenate([study_s, study_d, study_r]), "study_hours", seed=63),
        "stress": _add_noise(np.concatenate([stress_s, stress_d, stress_r]), "stress", seed=64),
    })

    return Scenario(
        name="Recovery",
        description="Genuine decline followed by genuine recovery. Engine should flag "
                    "during decline and correctly stop flagging as metrics return to baseline.",
        user_id="user_recovery",
        df=df,
        dates=dates,
        expected_flags={
            16: "hard_flag",     # deep in decline
            24: "soft_nudge",    # recovering but not back yet
            33: "none",          # fully recovered, no more flags
        }
    )


# -----------------------------------------------------------------------
# SCENARIO 8: Noisy stable user — high natural variance but genuinely fine
# Someone who naturally has high day-to-day mood/stress variance.
# High noise should NOT produce false positive flags -- the MIN_STD_FLOOR
# and baseline adapting to their high-variance normal should keep this clean.
# -----------------------------------------------------------------------
def scenario_noisy_stable() -> Scenario:
    n = 35
    rng = np.random.default_rng(99)

    # High variance but mean stays healthy throughout
    mood = _clip(3.5 + rng.normal(0, 0.8, n), "mood")
    sleep = _clip(7.0 + rng.normal(0, 1.0, n), "sleep_hours")
    sleep_q = _clip(3.5 + rng.normal(0, 0.8, n), "sleep_quality")
    study = _clip(4.0 + rng.normal(0, 1.2, n), "study_hours")
    stress = _clip(4.5 + rng.normal(0, 1.2, n), "stress")

    df, dates = _build_df("user_noisy", {
        "mood": mood,
        "sleep_hours": sleep,
        "sleep_quality": sleep_q,
        "study_hours": study,
        "stress": stress,
    })

    return Scenario(
        name="Noisy stable user",
        description="High natural day-to-day variance, but mean stays healthy. "
                    "Should NOT produce false positive flags -- engine must adapt "
                    "to their high-variance baseline.",
        user_id="user_noisy",
        df=df,
        dates=dates,
        expected_flags={
            16: "none", 22: "none", 30: "none"
        }
    )


def all_scenarios() -> List[Scenario]:
    return [
        scenario_stable(),
        scenario_gradual_decline(),
        scenario_sudden_crash(),
        scenario_masking(),
        scenario_exam_week(),
        scenario_post_exam_crash(),
        scenario_recovery(),
        scenario_noisy_stable(),
    ]
