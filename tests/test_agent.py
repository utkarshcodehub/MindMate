"""Tests for the Wellbeing Agent's deterministic layers (no network)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SUPABASE_URL", "https://placeholder.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "placeholder")

from api.agent import crisis_prescreen, run_agent, CRISIS_RESPONSE


def test_prescreen_fires_on_crisis_language():
    assert crisis_prescreen("I want to end my life")
    assert crisis_prescreen("thinking about SUICIDE lately")
    assert crisis_prescreen("i keep wanting to hurt myself")


def test_prescreen_ignores_normal_stress_talk():
    assert not crisis_prescreen("exams are killing my sleep schedule")
    assert not crisis_prescreen("how has my mood been this week?")
    assert not crisis_prescreen("i'm so stressed about placements")


def test_crisis_message_bypasses_llm_entirely():
    r = run_agent("u1", "i want to end it all", history=[])
    assert r["crisis"] is True
    assert r["tools_used"] == []
    assert "iCall" in r["reply"]


def test_graceful_fallback_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    r = run_agent("u1", "how am i doing?", history=[])
    assert r["crisis"] is False
    assert len(r["reply"]) > 0
