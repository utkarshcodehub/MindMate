"""
scoring.py

Onboarding score computation: PHQ-2, GAD-2, PSS-4.

All scoring logic lives here in pure Python -- no DB, no HTTP -- so it
can be tested and changed without touching route code. The route just
calls score_onboarding() and passes the result to the DB layer.

PSS-4 scoring note:
Items 4 and 5 are reverse-scored before summing. This means a response
of 0 becomes 4, 1 becomes 3, etc. The raw responses are ALWAYS stored
as the user answered them (in onboarding_raw_responses jsonb); the
reversal happens only at scoring time so we can re-score later if needed.
"""

from dataclasses import dataclass

REVERSE_SCORE = {0: 4, 1: 3, 2: 2, 3: 1, 4: 0}

# Clinical further-evaluation thresholds
PHQ2_FLAG_THRESHOLD = 3   # >= 3 warrants further evaluation per validation studies
GAD2_FLAG_THRESHOLD = 3


@dataclass
class OnboardScores:
    phq2_score: int      # 0-6
    gad2_score: int      # 0-6
    pss4_score: int      # 0-16 (after reversal)
    phq2_flag: bool      # True if >= PHQ2_FLAG_THRESHOLD
    gad2_flag: bool
    overall_risk: str    # 'low' | 'moderate' | 'high' -- coarse, for onboarding only
    raw_responses: dict  # stored as-is in DB for audit / future re-scoring


def score_onboarding(
    phq2_q1: int, phq2_q2: int,
    gad2_q1: int, gad2_q2: int,
    pss4_q2: int, pss4_q4: int, pss4_q5: int, pss4_q10: int,
) -> OnboardScores:
    phq2 = phq2_q1 + phq2_q2
    gad2 = gad2_q1 + gad2_q2

    # PSS-4: items q4 and q5 are reverse-scored before summing
    pss4 = pss4_q2 + REVERSE_SCORE[pss4_q4] + REVERSE_SCORE[pss4_q5] + pss4_q10

    phq2_flag = phq2 >= PHQ2_FLAG_THRESHOLD
    gad2_flag = gad2 >= GAD2_FLAG_THRESHOLD

    # Coarse overall risk from combined signals
    # PSS-4 doesn't have an official validated band so we use proportional
    # thirds of its 0-16 range as a rough proxy
    n_flags = sum([phq2_flag, gad2_flag, pss4 >= 11])
    if n_flags >= 2 or phq2 >= 5 or gad2 >= 5:
        overall_risk = "high"
    elif n_flags == 1 or phq2 >= 3 or gad2 >= 3 or pss4 >= 6:
        overall_risk = "moderate"
    else:
        overall_risk = "low"

    return OnboardScores(
        phq2_score=phq2,
        gad2_score=gad2,
        pss4_score=pss4,
        phq2_flag=phq2_flag,
        gad2_flag=gad2_flag,
        overall_risk=overall_risk,
        raw_responses={
            "phq2_q1": phq2_q1, "phq2_q2": phq2_q2,
            "gad2_q1": gad2_q1, "gad2_q2": gad2_q2,
            "pss4_q2": pss4_q2, "pss4_q4": pss4_q4,
            "pss4_q5": pss4_q5, "pss4_q10": pss4_q10,
        }
    )
