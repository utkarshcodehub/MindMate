/**
 * App.jsx
 *
 * Views: landing → onboarding → daily-log ("Today") → dashboard
 * ("Trends"), plus "about" (the landing content, minus the CTA).
 * State lives here; all child components receive props.
 *
 * Crisis overlay (CrisisModal) is rendered on top of any view
 * whenever crisis_path_fired is true from any API response.
 */

import { useState, useEffect } from 'react'
import Header       from './components/Header'
import Landing      from './components/Landing'
import Onboarding   from './components/Onboarding'
import DailyLog     from './components/DailyLog'
import Dashboard    from './components/Dashboard'
import CrisisModal  from './components/CrisisModal'
import AgentChat    from './components/AgentChat'
import { localToday } from './api'

const USER_KEY     = 'wb_user_id'
const LAST_LOG_KEY = 'wb_last_log_date'

export default function App() {
  const [view, setView]           = useState('loading')
  const [userId, setUserId]       = useState(null)
  const [todayLogged, setTodayLogged] = useState(false)
  const [crisis, setCrisis]       = useState(null) // {resources, message}

  // On mount: check if user exists and whether today's log is done
  useEffect(() => {
    const storedId  = localStorage.getItem(USER_KEY)
    const lastDate  = localStorage.getItem(LAST_LOG_KEY)
    const alreadyLoggedToday = lastDate === localToday()

    if (!storedId) {
      setView('landing')
      return
    }

    setUserId(storedId)
    setTodayLogged(alreadyLoggedToday)

    // Go to dashboard if already logged; daily-log otherwise
    setView(alreadyLoggedToday ? 'dashboard' : 'daily-log')
  }, [])

  // Called by Onboarding on successful POST /api/onboard
  function handleOnboardComplete(data) {
    localStorage.setItem(USER_KEY, data.user_id)
    if (data.auth_token) {
      localStorage.setItem('wb_auth_token', data.auth_token)
    }
    setUserId(data.user_id)
    if (data.crisis_path_fired) {
      setCrisis({ resources: data.crisis_resources, message: data.message })
    }
    setView('daily-log')
  }


  // Called by DailyLog on successful POST /api/log
  function handleLogSubmit(result) {
    localStorage.setItem(LAST_LOG_KEY, localToday())
    setTodayLogged(true)
    // Show crisis resources if hard_flag fired
    if (result.flag_type === 'hard_flag' && result.crisis_resources?.length) {
      setCrisis({
        resources: result.crisis_resources,
        message: result.nudge_message || null,
      })
    }
    setView('dashboard')
  }

  if (view === 'loading') {
    return <div className="app" />
  }

  return (
    <div className="app">
      {/* Crisis overlay — rendered above everything */}
      {crisis && (
        <CrisisModal data={crisis} onDismiss={() => setCrisis(null)} />
      )}

      <Header
        view={view}
        hasUser={!!userId}
        onNavigate={setView}
        onStart={() => setView('onboarding')}
      />

      {view === 'landing' && (
        <Landing onStart={() => setView('onboarding')} />
      )}

      {view === 'about' && (
        <Landing showCta={false} />
      )}

      {view === 'onboarding' && (
        <Onboarding onComplete={handleOnboardComplete} />
      )}

      {view === 'daily-log' && (
        <DailyLog
          userId={userId}
          todayLogged={todayLogged}
          onSubmit={handleLogSubmit}
          onViewDashboard={() => setView('dashboard')}
        />
      )}

      {view === 'dashboard' && (
        <div className="page">
          <Dashboard
            userId={userId}
            onLogToday={() => setView('daily-log')}
          />
          <AgentChat
            userId={userId}
            onCrisis={data => setCrisis(data)}
          />
        </div>
      )}
    </div>
  )
}
