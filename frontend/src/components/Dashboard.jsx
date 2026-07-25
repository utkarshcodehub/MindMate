/**
 * Dashboard.jsx
 *
 * Shows the user's recent patterns:
 *   - Current flag state (none / soft_nudge / hard_flag)
 *   - 7-day sparkline (mood + stress on one chart)
 *   - Recent log entries summary
 *   - Safety check prompt if 2-week cadence is due
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

function FlagCard({ flagType, nudgeMessage }) {
  if (flagType === 'none' || !flagType) {
    return (
      <div className="card" style={{ borderColor: 'var(--safe)', borderLeftWidth: 3 }}>
        <div className="row">
          <span className="flag-badge flag-none">no flag</span>
          <span className="muted" style={{ fontSize: 13 }}>
            Things look stable. Keep logging.
          </span>
        </div>
      </div>
    )
  }

  if (flagType === 'soft_nudge') {
    return (
      <div className="card" style={{ borderColor: 'var(--warn)', borderLeftWidth: 3 }}>
        <span className="flag-badge flag-soft">heads up</span>
        {nudgeMessage && <div className="nudge-card">{nudgeMessage}</div>}
      </div>
    )
  }

  return (
    <div className="card" style={{ borderColor: 'var(--danger)', borderLeftWidth: 3 }}>
      <span className="flag-badge flag-hard">check in</span>
      {nudgeMessage && <div className="nudge-card" style={{ borderColor: 'var(--danger)' }}>{nudgeMessage}</div>}
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
    <div
      className="card"
      style={{
        borderColor: 'rgba(245,197,66,0.3)',
        background: 'rgba(245,197,66,0.04)',
      }}
    >
      <p
        style={{
          fontSize: 12,
          fontFamily: 'var(--mono)',
          color: 'var(--accent)',
          marginBottom: 10,
          letterSpacing: '0.5px',
        }}
      >
        2-WEEK CHECK-IN
      </p>
      <p style={{ fontSize: 14, lineHeight: 1.6, marginBottom: 14 }}>
        Over the last 2 weeks, have you had any thoughts of being better
        off dead, or of hurting yourself in some way?
      </p>
      <p
        className="muted"
        style={{ fontSize: 12, marginBottom: 12, lineHeight: 1.6 }}
      >
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
              style={{
                display: 'block',
                fontFamily: 'var(--mono)',
                fontSize: 12,
                color: answer === opt.value ? 'var(--accent)' : 'var(--muted)',
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

const METRIC_COLORS = {
  mood:    '#f5c542',
  stress:  '#ef4444',
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--surface2)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '8px 12px',
      fontSize: 13,
    }}>
      <p style={{ color: 'var(--muted)', marginBottom: 4 }}>{label}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color, fontFamily: 'var(--mono)' }}>
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
      <div className="page" style={{ paddingTop: 48 }}>
        <p className="muted text-center" style={{ fontFamily: 'var(--mono)', fontSize: 13 }}>
          Loading…
        </p>
      </div>
    )
  }

  if (!summary) {
    return (
      <div className="page" style={{ paddingTop: 48 }}>
        <div className="card text-center">
          <p className="muted" style={{ fontSize: 14 }}>
            Couldn't load your dashboard. Try again later.
          </p>
        </div>
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

  const flagLabels = {
    none: 'No flag',
    soft_nudge: 'Heads up',
    hard_flag: 'Check in',
  }

  return (
    <div className="page">
      <div style={{ padding: '32px 0 20px' }}>
        <p className="muted" style={{ fontSize: 13, marginBottom: 4 }}>
          {new Date().toLocaleDateString('en-IN', {
            weekday: 'long', day: 'numeric', month: 'long',
          })}
        </p>
        <h1>Your check-in</h1>
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
          <div className="row" style={{ marginBottom: 12, justifyContent: 'space-between' }}>
            <h2>Last 7 days</h2>
            <div className="row" style={{ gap: 14 }}>
              <span style={{ fontSize: 12, color: METRIC_COLORS.mood }}>
                ● mood
              </span>
              <span style={{ fontSize: 12, color: METRIC_COLORS.stress }}>
                ● stress
              </span>
            </div>
          </div>
          <div className="chart-wrap" style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
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
                  stroke={METRIC_COLORS.mood}
                  strokeWidth={2}
                  dot={{ r: 3, fill: METRIC_COLORS.mood }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="stress"
                  stroke={METRIC_COLORS.stress}
                  strokeWidth={2}
                  dot={{ r: 3, fill: METRIC_COLORS.stress }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Stats row */}
      {summary.baseline_available && (
        <div className="card mt16" style={{ display: 'flex', gap: 0 }}>
          <div style={{ flex: 1, textAlign: 'center', padding: '4px 0' }}>
            <p
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 26,
                fontWeight: 600,
                color: summary.days_flagged_last_14 > 5 ? 'var(--danger)' : 'var(--accent)',
              }}
            >
              {summary.days_flagged_last_14}
            </p>
            <p className="muted" style={{ fontSize: 12 }}>flagged days (14d)</p>
          </div>
          <div style={{ width: 1, background: 'var(--border)', margin: '4px 0' }} />
          <div style={{ flex: 1, textAlign: 'center', padding: '4px 0' }}>
            <p style={{ fontFamily: 'var(--mono)', fontSize: 26, fontWeight: 600, color: 'var(--safe)' }}>
              {summary.recent_logs.length}
            </p>
            <p className="muted" style={{ fontSize: 12 }}>days logged (7d)</p>
          </div>
        </div>
      )}

      {!summary.baseline_available && (
        <div className="card mt16">
          <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>
            Keep logging daily — trend detection starts after{' '}
            <span style={{ fontFamily: 'var(--mono)', color: 'var(--accent)' }}>10</span> check-ins.
            You're at{' '}
            <span style={{ fontFamily: 'var(--mono)', color: 'var(--accent)' }}>
              {summary.recent_logs.length}
            </span>
            .
          </p>
        </div>
      )}

      {/* Log today button */}
      <div style={{ marginTop: 24 }}>
        <button className="btn btn-primary" onClick={onLogToday}>
          Log today
        </button>
      </div>

      <p
        className="muted text-center"
        style={{ fontSize: 11, marginTop: 20, lineHeight: 1.6 }}
      >
        This tool does not diagnose any condition. Crisis support:{' '}
        iCall 9152987821 · Vandrevala 1860-2662-345
      </p>
    </div>
  )
}