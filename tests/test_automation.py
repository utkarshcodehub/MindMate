"""Tests for the automation layer's deterministic decision logic."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SUPABASE_URL", "https://placeholder.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "placeholder")

from api.automation import decide_nudge, _write_message, REENGAGE_AFTER_DAYS


def test_no_logs_means_no_action():
    assert decide_nudge({}, None)["action"] == "none"


def test_quiet_user_gets_reengagement():
    d = decide_nudge({"concerning_metrics": []}, REENGAGE_AFTER_DAYS)
    assert d["action"] == "reengage"


def test_concerning_trend_gets_wellbeing_nudge():
    trend = {"concerning_metrics": ["mood", "sleep_hours"]}
    d = decide_nudge(trend, 0)
    assert d["action"] == "wellbeing"
    assert d["metrics"] == ["mood", "sleep_hours"]


def test_stable_active_user_gets_nothing():
    d = decide_nudge({"concerning_metrics": []}, 1)
    assert d["action"] == "none"


def test_reengagement_wins_over_stale_trend():
    # A user silent for 5 days shouldn't get a trend nudge off old data
    trend = {"concerning_metrics": ["stress"]}
    assert decide_nudge(trend, 5)["action"] == "reengage"


def test_message_fallback_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert len(_write_message("wellbeing", ["mood"])) > 0
    assert len(_write_message("reengage", [])) > 0
