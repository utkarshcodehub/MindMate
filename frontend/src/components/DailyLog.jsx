/**
 * DailyLog.jsx  ("Today")
 *
 * The core daily interaction — 5 sliders, completable in under 30
 * seconds. Values render in JetBrains Mono like instrument readings.
 * Submits to POST /api/log. Logic unchanged from v3.
 */

import { useState } from 'react'
import SliderInput from './SliderInput'
import { submitLog, localToday } from '../api'

const DEFAULTS = {
  mood: 3,
  sleep_hours: 7,
  sleep_quality: 3,
  study_hours: 4,
  stress: 4,
}

function greeting() {
  const h = new Date().getHours()
  if (h < 5) return 'Late night check-in'
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function DailyLog({ userId, todayLogged, onSubmit, onViewDashboard }) {
  const [values, setValues] = useState(DEFAULTS)
  const [freeText, setFreeText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  function set(key) {
    return val => setValues(prev => ({ ...prev, [key]: val }))
  }

  async function handleSubmit() {
    setLoading(true)
    setError(null)
    try {
      const result = await submitLog({
        user_id: userId,
        log_date: localToday(),
        mood: values.mood,
        sleep_hours: values.sleep_hours,
        sleep_quality: values.sleep_quality,
        study_hours: values.study_hours,
        stress: values.stress,
        free_text: freeText.trim() || null,
      })
      onSubmit(result)
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  // Already logged today — a calm holding screen
  if (todayLogged) {
    return (
      <div className="page" style={{ paddingTop: 48 }}>
        <div className="card text-center">
          <p style={{ fontSize: 26, color: 'var(--moss)', marginBottom: 8 }}>✓</p>
          <h2 style={{ fontFamily: 'var(--display)', fontSize: 22, fontWeight: 600 }}>
            Today is already on your line
          </h2>
          <p className="muted mt8" style={{ fontSize: 14 }}>
            One reading a day is all Baseline needs. See you tomorrow.
          </p>
          <button className="btn btn-ghost mt24" onClick={onViewDashboard}>
            See my trends
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      {/* Header */}
      <div style={{ padding: '28px 0 8px' }}>
        <p className="eyebrow" style={{ marginBottom: 6 }}>
          {new Date().toLocaleDateString('en-IN', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
          })}
        </p>
        <h1>{greeting()} — how are you?</h1>
        <p className="muted mt8" style={{ fontSize: 14 }}>
          About 30 seconds. Move the sliders to where things honestly feel.
        </p>
      </div>

      <div className="divider" />

      {/* Sliders */}
      <SliderInput
        label="Mood"
        id="mood"
        min={1} max={5} step={1}
        value={values.mood}
        onChange={set('mood')}
        minLabel="Really struggling"
        maxLabel="Feeling good"
      />

      <SliderInput
        label="Sleep last night"
        id="sleep_hours"
        min={0} max={12} step={0.5}
        value={values.sleep_hours}
        onChange={set('sleep_hours')}
        minLabel="0 hrs"
        maxLabel="12 hrs"
        formatValue={v => `${v}h`}
      />

      <SliderInput
        label="Sleep quality"
        id="sleep_quality"
        min={1} max={5} step={1}
        value={values.sleep_quality}
        onChange={set('sleep_quality')}
        minLabel="Restless"
        maxLabel="Deep & restful"
      />

      <SliderInput
        label="Study / work hours"
        id="study_hours"
        min={0} max={14} step={0.5}
        value={values.study_hours}
        onChange={set('study_hours')}
        minLabel="0 hrs"
        maxLabel="14 hrs"
        formatValue={v => `${v}h`}
      />

      <SliderInput
        label="Stress level"
        id="stress"
        min={1} max={10} step={1}
        value={values.stress}
        onChange={set('stress')}
        minLabel="Very calm"
        maxLabel="Overwhelmed"
      />

      {/* Optional note */}
      <div style={{ margin: '20px 0 24px' }}>
        <p className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
          Anything on your mind?{' '}
          <span style={{ opacity: 0.65 }}>(optional — never scored, just yours)</span>
        </p>
        <textarea
          placeholder="A space to write, if you want to…"
          value={freeText}
          onChange={e => setFreeText(e.target.value)}
          maxLength={500}
        />
      </div>

      {error && (
        <p style={{ color: 'var(--rose)', fontSize: 13, marginBottom: 12 }}>
          {error}
        </p>
      )}

      <button
        className="btn btn-primary"
        disabled={loading}
        onClick={handleSubmit}
      >
        {loading ? 'Saving…' : "Save today's check-in"}
      </button>

      <button
        className="btn btn-ghost"
        style={{ marginTop: 10 }}
        onClick={onViewDashboard}
      >
        View trends instead
      </button>
    </div>
  )
}
