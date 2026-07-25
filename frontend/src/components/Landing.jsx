/**
 * Landing.jsx
 *
 * The zero page: what Baseline is, how it works, and — just as
 * loudly — what it is not. Doubles as the "About" page after
 * onboarding (pass showCta={false} to hide the start button).
 */

export default function Landing({ onStart, showCta = true }) {
  return (
    <div className="page">
      {/* ---- Hero ---- */}
      <section className="hero">
        <h1>
          Some weeks bend.
          <br />
          <em>Know when yours does.</em>
        </h1>
        <p className="hero-sub">
          Baseline is a private early-warning system for student burnout.
          Thirty seconds a day — measured against your own normal, nobody
          else's.
        </p>

        {/* The signature: your line dips, and returns */}
        <div className="hero-line" aria-hidden="true">
          <svg viewBox="0 0 560 72" preserveAspectRatio="none">
            <line className="ref" x1="0" y1="36" x2="560" y2="36" />
            <path d="M 0 36 C 60 36 90 34 130 38 C 180 43 210 62 260 60 C 310 58 330 40 380 36 C 430 32 470 37 520 36 L 545 36" />
            <circle cx="545" cy="36" r="4.5" />
          </svg>
          <div className="hero-caption">
            <span>a hard stretch</span>
            <span>back to your baseline</span>
          </div>
        </div>
      </section>

      {showCta && (
        <div className="land-cta">
          <button className="btn btn-primary" onClick={onStart}>
            Begin — it takes 2 minutes
          </button>
          <p className="muted">
            No email. No feed. Your answers stay yours.
          </p>
        </div>
      )}

      {/* ---- How it works ---- */}
      <section className="land-section">
        <div className="ruled">
          <h2>How it works</h2>
          <span className="eyebrow">3 layers</span>
        </div>

        <div className="feature-row">
          <span className="feature-num">01</span>
          <div>
            <h3>A 30-second daily check-in</h3>
            <p>
              Five sliders — mood, sleep, study, stress. No essays, no
              streak guilt. Just a small honest reading, once a day.
            </p>
          </div>
        </div>

        <div className="feature-row">
          <span className="feature-num">02</span>
          <div>
            <h3>Your baseline, not an average</h3>
            <p>
              Baseline learns what normal looks like for <em>you</em>. A
              night owl's 6 hours isn't a red flag — a sudden drop from
              your usual 8 is. Slow slides get noticed before they become
              heavy.
            </p>
          </div>
        </div>

        <div className="feature-row">
          <span className="feature-num">03</span>
          <div>
            <h3>An agent that reads your data</h3>
            <p>
              Ask how your week has really been and the Wellbeing Agent
              checks your actual numbers before answering. Once a day it
              also looks over things on its own — and quietly leaves a
              note if you seem to need one.
            </p>
          </div>
        </div>
      </section>

      {/* ---- Honesty ---- */}
      <section className="land-section">
        <div className="ruled">
          <h2>Being straight with you</h2>
        </div>
        <div className="honesty-grid">
          <div className="honesty-card honesty-is">
            <h3>Baseline is</h3>
            <ul>
              <li>A private mirror for your last few weeks</li>
              <li>An early nudge when patterns drift</li>
              <li>A bridge toward real people who can help</li>
              <li>Yours — your data is never shown to anyone else</li>
            </ul>
          </div>
          <div className="honesty-card honesty-not">
            <h3>Baseline is not</h3>
            <ul>
              <li>A diagnosis of any condition</li>
              <li>Therapy, or a replacement for it</li>
              <li>A crisis service</li>
              <li>A judge — there is no score to win</li>
            </ul>
          </div>
        </div>
      </section>

      {/* ---- Crisis strip ---- */}
      <div className="crisis-strip">
        <strong>If things feel urgent right now,</strong> please skip the
        app and talk to a person: iCall{' '}
        <span className="mono">9152987821</span> · Vandrevala{' '}
        <span className="mono">1860-2662-345</span> · NIMHANS{' '}
        <span className="mono">080-46110007</span>. Free, confidential,
        and there for you.
      </div>

      {showCta && (
        <div className="land-cta">
          <button className="btn btn-ghost" onClick={onStart}>
            Start your first check-in
          </button>
        </div>
      )}

      <footer className="land-footer">
        Baseline · a student wellbeing project built for the IBM
        SkillsBuild AI Automation &amp; Intelligent Solutions internship ·
        SDG 3, Good Health and Well-being. It does not diagnose, treat,
        or monitor anyone.
      </footer>
    </div>
  )
}
