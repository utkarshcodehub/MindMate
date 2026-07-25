/**
 * CrisisModal.jsx
 *
 * Full-screen overlay shown whenever crisis_path_fired is true.
 * Requires the user to check a checkbox before dismissing,
 * ensuring they've seen the resources rather than panic-closing.
 *
 * Never shown because an LLM decided something — only shown because
 * item9_response > 0 (a deterministic rule in safety_check.py).
 */

import { useState } from 'react'

export default function CrisisModal({ data, onDismiss }) {
  const [acknowledged, setAcknowledged] = useState(false)
  const { resources = [], message } = data

  return (
    <div className="crisis-overlay" role="dialog" aria-modal="true" aria-label="Support resources">
      <div className="crisis-modal">
        <h2>You don't have to carry this alone</h2>

        <p>
          {message ||
            'Thank you for being honest. Please know that support is available ' +
            'right now — these services are free, confidential, and available any time.'}
        </p>

        {resources.map((r, i) => (
          <div className="resource-card" key={i}>
            <div className="resource-name">{r.name}</div>
            <div className="resource-phone">{r.phone}</div>
            <div className="resource-hours">{r.hours}</div>
          </div>
        ))}

        <label className="crisis-ack">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={e => setAcknowledged(e.target.checked)}
          />
          I've noted these resources and understand they're here for me.
        </label>

        <button
          className="btn btn-ghost"
          disabled={!acknowledged}
          onClick={onDismiss}
        >
          Continue
        </button>
      </div>
    </div>
  )
}