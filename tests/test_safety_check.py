import sys
sys.path.insert(0, "/home/claude/student_wellbeing/engine")

import pandas as pd
from engine.safety_check import evaluate_item9

today = pd.Timestamp("2026-06-18")

print("Test 1: response = 0 (no ideation)")
r = evaluate_item9("user_a", today, "scheduled_2wk", 0)
print(f"  crisis_path_fired = {r.crisis_path_fired}, resources shown: {len(r.resources_shown)}")
assert r.crisis_path_fired == False
assert len(r.resources_shown) == 0

print("\nTest 2: response = 1 ('several days') -- should STILL fire crisis path")
r = evaluate_item9("user_b", today, "onboarding", 1)
print(f"  crisis_path_fired = {r.crisis_path_fired}, resources shown: {len(r.resources_shown)}")
assert r.crisis_path_fired == True
assert len(r.resources_shown) == 3

print("\nTest 3: response = 3 ('nearly every day') -- crisis path, same resources as response=1")
r = evaluate_item9("user_c", today, "hard_flag_triggered", 3)
print(f"  crisis_path_fired = {r.crisis_path_fired}, resources shown: {len(r.resources_shown)}")
assert r.crisis_path_fired == True

print("\nTest 4: invalid response (5) -- should raise, NOT silently default to safe")
try:
    evaluate_item9("user_d", today, "onboarding", 5)
    print("  FAILED: should have raised an exception")
except ValueError as e:
    print(f"  Correctly raised: {e}")

print("\nAll safety check tests passed.")
