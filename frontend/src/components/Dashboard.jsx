/**
 * Dashboard.jsx  ("Trends")
 *
 * The user's recent patterns:
 *   - Current flag state (steady / heads up / check in)
 *   - 7-day chart (mood + stress), theme-aware colors
 *   - Flagged-days + logged-days stats
 *   - Safety check prompt if the 2-week cadence is due
 *
 * NOTE: no .page wrapper here — App wraps Dashboard + AgentChat
 * together so they share one column.
 */

import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { getUserSummary, checkSafetyDue, submitSafetyCheck } from '../api'

const PHQ_SCALE = [
  { value: 0, label: 'Not at all' },
  { value: 1, label: 'Several days' },
  { value: 2, label: 'More than half the days' },
  { value: 3, label: 'Nearly every day' },
]

/** Read a CSS custom property so charts follow light/dark automatically */
function cssVar(name, fallback) {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name)
  return v?.trim() || fallback
}

function FlagCard({ flagType, nudgeMessage }) {
  if (flagType === 'none' || !flagType) {
    return (
      <div className="card">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <span className="flag-chip flag-steady">steady</span>
          <span className="muted">Nothing out of the ordinary. Keep going.</span>
        </div>
      </div>
    )
  }

  if (flagType === 'soft_nudge') {
    return (
      <div className="card card-tint-apricot">
        <span className="flag-chip flag-soft">heads up</span>
        {nudgeMessage && <p className="nudge-text">{nudgeMessage}</p>}
      </div>
    )
  }

  return (
    <div className="card card-tint-rose">
      <span className="flag-chip flag-hard">check in</span>
      {nudgeMessage && <p className="nudge-text">{nudgeMessage}</p>}
    </div>
  )
}

function SafetyCheckPrompt({ userId, onComplete }) {
  const [answer, setAnswer] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  async function handleSubmit() {
    if (answer === null) return
    setSubmitting(true)
    try {
      const result = await submitSafetyCheck({
        user_id: userId,
        item9_response: answer,
        trigger_source: 'scheduled_2wk',
      })
      setDone(true)
      onComplete(result)
    } catch {
      setSubmitting(false)
    }
  }

  if (done) return null

  return (
    <div className="card">
      <p className="eyebrow" style={{ marginBottom: 10 }}>2-week check-in</p>
      <p style={{ fontSize: 14.5, lineHeight: 1.6, marginBottom: 10 }}>
        Over the last 2 weeks, have you had any thoughts of being better
        off dead, or of hurting yourself in some way?
      </p>
      <p className="muted" style={{ fontSize: 12.5, marginBottom: 4, lineHeight: 1.6 }}>
        Your answer stays completely private and is never shared with anyone.
      </p>
      <div className="option-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
        {PHQ_SCALE.map(opt => (
          <button
            key={opt.value}
            className={`option-card${answer === opt.value ? ' selected' : ''}`}
            onClick={() => setAnswer(opt.value)}
          >
            <span
              className="mono"
              style={{
                display: 'block',
                fontSize: 12,
                color: answer === opt.value ? 'var(--accent-ink)' : 'var(--muted)',
                marginBottom: 2,
              }}
            >
              {opt.value}
            </span>
            {opt.label}
          </button>
        ))}
      </div>
      <button
        className="btn btn-primary"
        style={{ marginTop: 14 }}
        disabled={answer === null || submitting}
        onClick={handleSubmit}
      >
        {submitting ? 'Saving…' : 'Submit'}
      </button>
    </div>
  )
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--line)',
      borderRadius: 8,
      padding: '8px 12px',
      fontSize: 13,
      boxShadow: 'var(--shadow)',
    }}>
      <p style={{ color: 'var(--muted)', marginBottom: 4 }}>{label}</p>
      {payload.map(p => (
        <p key={p.dataKey} className="mono" style={{ color: p.color }}>
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  )
}

export default function Dashboard({ userId, onLogToday }) {
  const [summary, setSummary] = useState(null)
  const [safetyDue, setSafetyDue] = useState(false)
  const [loading, setLoading] = useState(true)
  const [latestResult, setLatestResult] = useState(null)

  const moodColor   = cssVar('--accent', '#5158A5')
  const stressColor = cssVar('--apricot', '#C97F3D')

  useEffect(() => {
    Promise.all([
      getUserSummary(userId),
      checkSafetyDue(userId),
    ])
      .then(([sum, safety]) => {
        setSummary(sum)
        setSafetyDue(safety.is_due)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [userId])

  function handleSafetyComplete(result) {
    setSafetyDue(false)
    if (result.crisis_path_fired) {
      setLatestResult(result)
    }
  }

  if (loading) {
    return (
      <p className="muted text-center mono" style={{ paddingTop: 56, fontSize: 13 }}>
        reading your line…
      </p>
    )
  }

  if (!summary) {
    return (
      <div className="card text-center" style={{ marginTop: 40 }}>
        <p className="muted" style={{ fontSize: 14 }}>
          Couldn't load your trends. Check your connection and try again.
        </p>
      </div>
    )
  }

  // Build chart data from recent_logs (oldest first)
  const chartData = [...summary.recent_logs]
    .reverse()
    .map(log => ({
      date: new Date(log.log_date).toLocaleDateString('en-IN', {
        day: 'numeric', month: 'short',
      }),
      mood: log.mood,
      stress: log.stress,
    }))

  return (
    <>
      <div style={{ padding: '28px 0 18px' }}>
        <p className="eyebrow" style={{ marginBottom: 6 }}>
          {new Date().toLocaleDateString('en-IN', {
            weekday: 'long', day: 'numeric', month: 'long',
          })}
        </p>
        <h1>Your trends</h1>
      </div>

      {/* Flag state */}
      <FlagCard
        flagType={summary.current_flag_state}
        nudgeMessage={latestResult?.nudge_message}
      />

      {/* Safety check if due */}
      {safetyDue && (
        <div className="mt16">
          <SafetyCheckPrompt userId={userId} onComplete={handleSafetyComplete} />
        </div>
      )}

      {/* 7-day chart */}
      {chartData.length >= 2 && (
        <div className="card mt16">
          <div className="ruled">
            <h2>Last 7 days</h2>
            <div className="row" style={{ gap: 14 }}>
              <span style={{ fontSize: 12, color: moodColor }}>● mood</span>
              <span style={{ fontSize: 12, color: stressColor }}>● stress</span>
            </div>
          </div>
          <div className="chart-wrap" style={{ height: 170 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid stroke="var(--line)" strokeDasharray="3 4" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: 'var(--muted)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={[1, 10]}
                  tick={{ fill: 'var(--muted)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="mood"
                  stroke={moodColor}
                  strokeWidth={2.25}
                  dot={{ r: 3, fill: moodColor, strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="stress"
                  stroke={stressColor}
                  strokeWidth={2.25}
                  dot={{ r: 3, fill: stressColor, strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Stats row */}
      {summary.baseline_available && (
        <div className="card mt16 stat-row">
          <div className="stat-cell">
            <p
              className="stat-num"
              style={{
                color: summary.days_flagged_last_14 > 5 ? 'var(--rose)' : 'var(--accent-ink)',
              }}
            >
              {summary.days_flagged_last_14}
            </p>
            <p className="stat-label">flagged days, last 14</p>
          </div>
          <div className="stat-div" />
          <div className="stat-cell">
            <p className="stat-num" style={{ color: 'var(--moss)' }}>
              {summary.recent_logs.length}
            </p>
            <p className="stat-label">days logged, last 7</p>
          </div>
        </div>
      )}

      {!summary.baseline_available && (
        <div className="card mt16 card-tint-accent">
          <p style={{ fontSize: 14, lineHeight: 1.65 }}>
            Baseline is still learning your normal. Trend detection begins
            after <span className="mono" style={{ color: 'var(--accent-ink)' }}>10</span>{' '}
            check-ins — you're at{' '}
            <span className="mono" style={{ color: 'var(--accent-ink)' }}>
              {summary.recent_logs.length}
            </span>{' '}
            this week.
          </p>
        </div>
      )}

      {/* Log today button */}
      <div className="mt24">
        <button className="btn btn-primary" onClick={onLogToday}>
          Log today's check-in
        </button>
      </div>

      <p className="muted text-center" style={{ fontSize: 11.5, marginTop: 20, lineHeight: 1.7 }}>
        Baseline does not diagnose any condition. Crisis support:{' '}
        iCall <span className="mono">9152987821</span> · Vandrevala{' '}
        <span className="mono">1860-2662-345</span>
      </p>
    </>
  )
}
