/**
 * Header.jsx
 *
 * Sticky marketing-style navbar: MindMate wordmark left, nav center-
 * right, dark pill CTA. Nav adapts: marketing links before onboarding,
 * app links (Today / Trends / About) after.
 */

export default function Header({ view, onNavigate, hasUser, onStart }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <button
          className="wordmark"
          onClick={() => onNavigate(hasUser ? 'dashboard' : 'landing')}
          aria-label="MindMate home"
        >
          MindMate<span className="dot">.</span>
        </button>

        {hasUser ? (
          <nav className="nav" aria-label="Main">
            <button
              className={`nav-link${view === 'daily-log' ? ' active' : ''}`}
              onClick={() => onNavigate('daily-log')}
            >
              Today
            </button>
            <button
              className={`nav-link${view === 'dashboard' ? ' active' : ''}`}
              onClick={() => onNavigate('dashboard')}
            >
              Trends
            </button>
            <button
              className={`nav-link${view === 'about' ? ' active' : ''}`}
              onClick={() => onNavigate('about')}
            >
              About
            </button>
          </nav>
        ) : (
          view === 'landing' && (
            <nav className="nav" aria-label="Main">
              <button className="nav-cta" onClick={onStart}>
                Start free
              </button>
            </nav>
          )
        )}
      </div>
    </header>
  )
}
