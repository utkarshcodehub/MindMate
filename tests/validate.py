"""
validate.py

Runs all 8 synthetic scenarios through the full pipeline and checks
actual flag decisions against expected_flags for each scenario.

Output: per-scenario day-by-day trace + pass/fail summary.

A PASS means the engine produced the expected flag type on every checked
day. A FAIL means a mismatch -- either a false positive (flagged when it
shouldn't have) or a false negative (didn't flag when it should have).
Either one points to a threshold or logic problem to investigate.

This is the Phase 7 validation step from the SOP. Run this every time
you touch threshold constants in trend_engine.py or flag_decision.py to
catch regressions.
"""

import sys
from pathlib import Path

root = Path(__file__).parent.parent  # goes up from tests/ to student_wellbeing/
sys.path.insert(0, str(root))

import pandas as pd
from engine.flag_decision import evaluate_day, UserTrendState
from data.synthetic import all_scenarios

EVAL_START_DAY = 13   # don't evaluate until day 14 -- need baseline history first


def run_scenario(scenario):
    state = UserTrendState(user_id=scenario.user_id)
    results = {}

    for i in range(EVAL_START_DAY, len(scenario.dates)):
        result = evaluate_day(scenario.df, state, scenario.dates[i])
        results[i] = result

    return results


def check_expectations(scenario, results) -> list:
    failures = []
    for day_idx, expected_flag in scenario.expected_flags.items():
        if day_idx not in results:
            failures.append(
                f"  Day {day_idx+1}: expected '{expected_flag}' but day wasn't evaluated "
                f"(index out of range or before evaluation start)"
            )
            continue
        actual = results[day_idx].flag_type
        if actual != expected_flag:
            reason = results[day_idx].reason
            failures.append(
                f"  Day {day_idx+1}: expected '{expected_flag}', got '{actual}' "
                f"-- {reason}"
            )
    return failures


def print_trace(scenario, results, show_all=False):
    """Print day-by-day output for a scenario. show_all=True prints every day;
    False prints only days with non-'none' decisions or expected-check days."""
    checked_days = set(scenario.expected_flags.keys())

    print(f"\n  {'Day':<5} {'Date':<12} {'Flag':<12} Reason")
    print(f"  {'-'*5} {'-'*12} {'-'*12} {'-'*45}")
    for i, result in sorted(results.items()):
        is_checked = i in checked_days
        is_nontrivial = result.flag_type != "none"
        if show_all or is_checked or is_nontrivial:
            marker = " <<" if is_checked else ""
            print(f"  {i+1:<5} {result.date.date()}  {result.flag_type:<12} "
                  f"{result.reason[:60]}{marker}")


def run_all():
    scenarios = all_scenarios()
    passed = 0
    failed = 0
    failures_summary = []

    print("=" * 70)
    print("PHASE 7 VALIDATION — SYNTHETIC SCENARIO SUITE")
    print("=" * 70)

    for scenario in scenarios:
        print(f"\n[{'':─<66}]")
        print(f"  SCENARIO: {scenario.name}")
        print(f"  {scenario.description}")

        results = run_scenario(scenario)
        failures = check_expectations(scenario, results)

        print_trace(scenario, results, show_all=False)

        if failures:
            print(f"\n  ✗ FAILED ({len(failures)} mismatch(es)):")
            for f in failures:
                print(f)
            failed += 1
            failures_summary.append((scenario.name, failures))
        else:
            print(f"\n  ✓ PASSED — all {len(scenario.expected_flags)} expected outcomes matched")
            passed += 1

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(scenarios)} scenarios")
    if failures_summary:
        print("\nFAILED SCENARIOS:")
        for name, failures in failures_summary:
            print(f"  {name}:")
            for f in failures:
                print(f)
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
