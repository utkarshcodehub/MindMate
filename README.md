# Student Wellbeing Check-In · with Wellbeing Agent

A private, non-judgmental early-warning system for student burnout — now
with an **autonomous AI agent** students can talk to about their own data.

**SDG 3: Good Health and Well-being** ·

> This tool does **not** diagnose, does **not** replace therapy, and is
> **not** a crisis service. It is a bridge to help-seeking.
> Crisis resources (India): iCall 9152987821 · Vandrevala 1860-2662-345 ·
> NIMHANS 080-46110007

---

## What it does

1. **Onboarding** — short, validated screeners (PHQ-2, GAD-2, PSS-4) set
   a starting picture. PHQ-9 item 9 is asked standalone; any nonzero
   answer routes straight to crisis resources.
2. **Daily check-ins** — mood, sleep, study hours, stress (30 seconds).
3. **Trend engine (deterministic)** — z-scores against each student's
   *own* baseline, consecutive-day persistence rules, cross-metric
   logic (mood+sleep together > either alone). Produces
   `none | soft_nudge | hard_flag`.
4. **Daily automation sweep (no human in the loop)** — an external cron
   (GitHub Actions, included in `.github/workflows/daily_agent_sweep.yml`)
   triggers `POST /api/automation/daily-sweep` each morning. The sweep
   scans every user, runs trend analysis, and deterministically decides:
   concerning trend → personalised wellbeing nudge; 3+ silent days →
   gentle re-engagement; otherwise → no action. The LLM only words the
   message; nudges appear in the student's agent chat at next login,
   marked "sent automatically by the daily agent sweep."
5. **Wellbeing Agent (LLM + tools)** — a Groq LLM agent that
   autonomously decides which tools to call to answer the student:

   | Tool | What it gives the agent |
   |---|---|
   | `get_user_summary` | the student's last 7 days of real check-ins |
   | `get_trend_analysis` | last 7 days vs 3-week personal baseline |
   | `get_crisis_resources` | professional helplines (India) |

   The UI shows each tool call as a chip ("📈 analysed your 4-week
   trend") so the agent's actions are visible, not just claimed.

## Safety architecture (the core design rule)

**The LLM never makes safety decisions.**

- Flags are decided by the deterministic engine; Groq only *words* them.
- Agent chat messages pass a deterministic crisis pre-screen **before**
  any LLM call — a hit returns helplines immediately, LLM never consulted.
- PHQ-9 item 9 handling has no thresholds, tiers, or LLM: any nonzero
  answer shows resources, every time.
- The agent's system prompt forbids diagnosis and clinical claims, and
  it fails gracefully (static supportive copy) if Groq is unreachable.

## Stack

FastAPI · Supabase (Postgres) · Groq (LLaMA 3.3 70B, tool use) ·
React + Vite · Recharts

## Run locally

```bash
# backend (from repo root)
pip install -r requirements.txt
cp .env.example .env        # fill in SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY
uvicorn api.main:app --reload --port 8000

# frontend
cd frontend
npm install
npm run dev                 # http://localhost:5173 (proxies /api to :8000)
```

## Deploy

**Backend → Render:** push this repo to GitHub, create a Blueprint from
`render.yaml`, set `SUPABASE_URL`, `SUPABASE_KEY`, `GROQ_API_KEY`, `AUTOMATION_SECRET`, and
(after the frontend is live) `ALLOWED_ORIGINS=https://<your-app>.vercel.app`.

**Frontend → Vercel:** import the `frontend/` directory, framework =
Vite, and set env var `VITE_API_URL=https://<your-api>.onrender.com`.

**Database migration:** run `migrations/002_agent_nudges.sql` once in the
Supabase SQL Editor (creates the `agent_nudges` table).

**Automation trigger:** in the GitHub repo, add Actions secrets
`SWEEP_URL` and `AUTOMATION_SECRET` — the included workflow then runs the
sweep daily at 9:00 AM IST (also manually runnable from the Actions tab).

## Tests

```bash
python -m pytest tests/
```

Covers the safety check (item 9), the full trend pipeline, and the
agent's deterministic crisis pre-screen and fallbacks.
