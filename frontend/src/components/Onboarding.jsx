/**
 * Onboarding.jsx
 *
 * 4 groups of questions, one group at a time:
 *   1. PHQ-2   (depression screen, 0-3 scale)
 *   2. GAD-2   (anxiety screen, 0-3 scale)
 *   3. PSS-4   (stress assessment, 0-4 scale)
 *   4. Item 9  (safety question, alone, special framing)
 *
 * All answers collected before submitting so the API gets one clean
 * POST with all 9 fields. Logic unchanged from v3 — presentation only.
 */

import { useState } from 'react'
import { onboard } from '../api'

const PHQ_SCALE = [
  { value: 0, label: 'Not at all' },
  { value: 1, label: 'Several days' },
  { value: 2, label: 'More than half the days' },
  { value: 3, label: 'Nearly every day' },
]

const PSS_SCALE = [
  { value: 0, label: 'Never' },
  { value: 1, label: 'Almost never' },
  { value: 2, label: 'Sometimes' },
  { value: 3, label: 'Fairly often' },
  { value: 4, label: 'Very often' },
]

const GROUPS = [
  {
    key: 'phq2',
    title: 'Over the last 2 weeks…',
    subtitle: 'How often have you been bothered by the following?',
    scale: PHQ_SCALE,
    questions: [
      { id: 'phq2_q1', text: 'Little interest or pleasure in doing things' },
      { id: 'phq2_q2', text: 'Feeling down, depressed, or hopeless' },
    ],
  },
  {
    key: 'gad2',
    title: 'Over the last 2 weeks…',
    subtitle: null,
    scale: PHQ_SCALE,
    questions: [
      { id: 'gad2_q1', text: 'Feeling nervous, anxious, or on edge' },
      { id: 'gad2_q2', text: 'Not being able to stop or control worrying' },
    ],
  },
  {
    key: 'pss4',
    title: 'In the last month…',
    subtitle: null,
    scale: PSS_SCALE,
    questions: [
      { id: 'pss4_q2',  text: 'Felt unable to control the important things in your life' },
      { id: 'pss4_q4',  text: 'Felt confident about your ability to handle personal problems' },
      { id: 'pss4_q5',  text: 'Felt that things were going your way' },
      { id: 'pss4_q10', text: 'Felt difficulties piling up so high you could not overcome them' },
    ],
  },
  {
    key: 'safety',
    title: 'One more question',
    subtitle:
      'This one matters a lot to us. Please answer honestly — your response stays completely private and is never shared with anyone.',
    scale: PHQ_SCALE,
    isSpecial: true,
    questions: [
      {
        id: 'item9_response',
        text: 'Thoughts that you would be better off dead, or of hurting yourself in some way',
      },
    ],
  },
]

function QuestionCard({ question, scale, answer, onSelect }) {
  return (
    <div className="card mt16">
      <p style={{ fontSize: 15, lineHeight: 1.6 }}>{question.text}</p>
      <div className="option-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
        {scale.map(opt => (
          <button
            key={opt.value}
            className={`option-card${answer === opt.value ? ' selected' : ''}`}
            onClick={() => onSelect(question.id, opt.value)}
          >
            <span
              className="mono"
              style={{
                display: 'block',
                fontSize: 13,
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
    </div>
  )
}

export default function Onboarding({ onComplete }) {
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const group = GROUPS[step]
  const totalSteps = GROUPS.length

  // All questions in current group must be answered to proceed
  const groupAnswered = group.questions.every(q => answers[q.id] !== undefined)

  function handleSelect(id, value) {
    setAnswers(prev => ({ ...prev, [id]: value }))
  }

  async function handleNext() {
    if (step < totalSteps - 1) {
      setStep(s => s + 1)
      return
    }

    // Last step — submit
    setLoading(true)
    setError(null)
    try {
      const result = await onboard(answers)
      onComplete(result)
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  const progress = (step / totalSteps) * 100

  return (
    <div className="page">
      {/* Header */}
      <div style={{ padding: '28px 0 20px' }}>
        <p className="eyebrow" style={{ marginBottom: 4 }}>
          Setting up MindMate · step {step + 1} of {totalSteps}
        </p>
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <h1>{group.title}</h1>
        {group.subtitle && (
          group.isSpecial ? (
            <p className="notice">{group.subtitle}</p>
          ) : (
            <p className="muted" style={{ marginTop: 8, fontSize: 14, lineHeight: 1.6 }}>
              {group.subtitle}
            </p>
          )
        )}
      </div>

      {/* Questions */}
      {group.questions.map(q => (
        <QuestionCard
          key={q.id}
          question={q}
          scale={group.scale}
          answer={answers[q.id]}
          onSelect={handleSelect}
        />
      ))}

      {/* Error */}
      {error && (
        <p style={{ color: 'var(--rose)', fontSize: 13, marginTop: 12 }}>
          {error}
        </p>
      )}

      {/* Action */}
      <div className="mt24">
        <button
          className="btn btn-primary"
          disabled={!groupAnswered || loading}
          onClick={handleNext}
        >
          {loading
            ? 'Getting things ready…'
            : step < totalSteps - 1
            ? 'Next'
            : 'Finish setup'}
        </button>
      </div>

      {/* Disclaimer */}
      <p
        className="muted text-center"
        style={{ fontSize: 12, marginTop: 20, lineHeight: 1.7 }}
      >
        These short questionnaires set your starting picture. MindMate
        does not diagnose any condition — it helps you notice patterns
        before they become harder to manage.
      </p>
    </div>
  )
}
