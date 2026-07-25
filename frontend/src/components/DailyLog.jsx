/**
 * DailyLog.jsx
 *
 * The core daily interaction — 5 sliders, completable in under 30 seconds.
 * Each slider shows its value in large JetBrains Mono text (the signature
 * element of this UI). Submits to POST /api/log.
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

  // Already logged today — show a calm holding screen
  if (todayLogged) {
    return (
      <div className="page" style={{ paddingTop: 48 }}>
        <div className="card text-center">
          <p style={{ fontSize: 28, marginBottom: 8 }}>✓</p>
          <h2>Already logged today</h2>
          <p className="muted mt8" style={{ fontSize: 14 }}>
            Come back tomorrow for your next check-in.
          </p>
          <button className="btn btn-ghost mt24" onClick={onViewDashboard}>
            See my dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      {/* Header */}
      <div style={{ padding: '32px 0 8px' }}>
        <p className="muted" style={{ fontSize: 13, marginBottom: 4 }}>
          {new Date().toLocaleDateString('en-IN', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
          })}
        </p>
        <h1>How are you doing?</h1>
        <p className="muted mt8" style={{ fontSize: 14 }}>
          Takes about 30 seconds. Just move the sliders to where things feel right.
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
      <div style={{ marginBottom: 24 }}>
        <p className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
          Anything on your mind? <span style={{ opacity: 0.6 }}>(optional, never scored)</span>
        </p>
        <textarea
          placeholder="Just a space to write if you want to…"
          value={freeText}
          onChange={e => setFreeText(e.target.value)}
          maxLength={500}
        />
      </div>

      {error && (
        <p style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 12 }}>
          {error}
        </p>
      )}

      <button
        className="btn btn-primary"
        disabled={loading}
        onClick={handleSubmit}
      >
        {loading ? 'Saving…' : 'Save today\'s log'}
      </button>

      <button
        className="btn btn-ghost"
        style={{ marginTop: 10 }}
        onClick={onViewDashboard}
      >
        View dashboard
      </button>
    </div>
  )
}