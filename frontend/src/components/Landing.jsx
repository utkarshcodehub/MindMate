/**
 * Landing.jsx
 *
 * The MindMate marketing page. Full-width commercial layout:
 * aurora-gradient hero → feature tiles → how it works → honesty
 * section → crisis strip → final CTA. Doubles as "About" after
 * onboarding (showCta={false}).
 */

export default function Landing({ onStart, showCta = true }) {
  return (
    <div style={{ width: '100%' }}>
      {/* ---- Hero ---- */}
      <section className="hero aurora">
        <div className="hero-inner">
          <h1>
            A companion that
            <br />
            knows your normal
          </h1>
          <p className="hero-sub">
            MindMate is your AI companion for student well-being —
            30-second daily check-ins, trends measured against your own
            baseline, and an agent that actually reads your data before
            it speaks.
          </p>

          {showCta && (
            <div className="hero-cta">
              <button className="btn btn-primary btn-inline" onClick={onStart}>
                Start free — takes 2 minutes
              </button>
              <p className="muted">No email. No feed. Your answers stay yours.</p>
            </div>
          )}

          <div className="hero-stats">
            <div className="hero-stat">
              <b>30s</b>
              <span>a day is enough</span>
            </div>
            <div className="hero-stat">
              <b>1:1</b>
              <span>you vs. your own baseline</span>
            </div>
            <div className="hero-stat">
              <b>24/7</b>
              <span>an agent in your corner</span>
            </div>
          </div>
        </div>
      </section>

      <div className="page-wide">
        {/* ---- Feature tiles ---- */}
        <section className="land-section" id="features">
          <div className="land-section-head">
            <h2>Small check-ins. Big picture.</h2>
            <p>
              Burnout rarely arrives overnight — it drifts in. MindMate is
              built to notice the drift early, kindly, and privately.
            </p>
          </div>

          <div className="tile-grid">
            <div className="tile">
              <div className="tile-art a1" aria-hidden="true">☀️</div>
              <div className="tile-body">
                <h3>A 30-second daily ritual</h3>
                <p>
                  Five sliders — mood, sleep, study, stress. No essays, no
                  streak guilt, no score to win. Just an honest reading,
                  once a day.
                </p>
              </div>
            </div>
            <div className="tile">
              <div className="tile-art a2" aria-hidden="true">📈</div>
              <div className="tile-body">
                <h3>Trends that know your normal</h3>
                <p>
                  A night owl's 6 hours isn't a red flag — a sudden drop
                  from your usual 8 is. MindMate compares you only to you,
                  and gently flags what drifts.
                </p>
              </div>
            </div>
            <div className="tile">
              <div className="tile-art a3" aria-hidden="true">💬</div>
              <div className="tile-body">
                <h3>An agent that reads your data</h3>
                <p>
                  Ask how your week has really been — the agent checks your
                  actual numbers before answering. Once a day, it looks
                  things over on its own and leaves a note if you need one.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ---- How it works ---- */}
        <section className="land-section" id="how">
          <div className="land-section-head">
            <h2>How MindMate works</h2>
          </div>
          <div className="steps">
            <div className="step-row">
              <span className="step-num">01</span>
              <div>
                <h3>Set your starting picture</h3>
                <p>
                  A 2-minute intake with short, clinically validated
                  questionnaires — so day one already understands where
                  you're starting from.
                </p>
              </div>
            </div>
            <div className="step-row">
              <span className="step-num">02</span>
              <div>
                <h3>Check in daily, 30 seconds</h3>
                <p>
                  Move five sliders to where things honestly feel. MindMate
                  quietly learns your personal baseline over the first ten
                  days.
                </p>
              </div>
            </div>
            <div className="step-row">
              <span className="step-num">03</span>
              <div>
                <h3>Get noticed — before it gets heavy</h3>
                <p>
                  When your pattern drifts, you get a kind heads-up and a
                  small suggestion. When things look serious, MindMate
                  points you to real people who can help — instantly, every
                  time.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ---- Honesty ---- */}
        <section className="land-section" id="safety">
          <div className="land-section-head">
            <h2>Being straight with you</h2>
            <p>
              Trust is the whole product. So here's exactly what MindMate
              is — and what it will never pretend to be.
            </p>
          </div>
          <div className="honesty-grid">
            <div className="honesty-card honesty-is">
              <h3>MindMate is</h3>
              <ul>
                <li>A private mirror for your last few weeks</li>
                <li>An early nudge when your patterns drift</li>
                <li>A bridge toward real people who can help</li>
                <li>Yours — your data is never shown to anyone else</li>
              </ul>
            </div>
            <div className="honesty-card honesty-not">
              <h3>MindMate is not</h3>
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
          available for you.
        </div>

        {/* ---- Final CTA ---- */}
        {showCta && (
          <section className="final-cta aurora">
            <h2>Your mind deserves a mate.</h2>
            <p>
              Two minutes to set up. Thirty seconds a day. A companion that
              pays attention so things never have to get heavy in silence.
            </p>
            <button className="btn btn-primary btn-inline" onClick={onStart}>
              Start your first check-in
            </button>
          </section>
        )}

        <footer className="land-footer">
          MindMate · your AI companion for student well-being · built for
          the IBM SkillsBuild AI Automation &amp; Intelligent Solutions
          internship · SDG 3, Good Health and Well-being.
          <br />
          MindMate does not diagnose, treat, or monitor anyone.
        </footer>
      </div>
    </div>
  )
}
