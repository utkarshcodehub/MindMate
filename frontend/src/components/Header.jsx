/**
 * Header.jsx
 *
 * Wordmark (lowercase serif italic resting on its line — the brand
 * motif) plus nav. Nav links appear only once the user exists.
 */

export default function Header({ view, onNavigate, hasUser }) {
  return (
    <header className="topbar">
      <button
        className="wordmark"
        onClick={() => onNavigate(hasUser ? 'dashboard' : 'landing')}
        aria-label="Baseline home"
      >
        baseline
      </button>

      {hasUser && (
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
      )}
    </header>
  )
}
