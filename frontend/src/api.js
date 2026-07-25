/**
 * api.js
 * All network calls to the FastAPI backend.
 * Vite proxies /api/* to localhost:8000 in development
 * so no CORS issues and no hardcoded base URL needed.
 */

const BASE = (import.meta.env.VITE_API_URL || '') + '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

/** Submit onboarding answers (9 questions + item 9) */
export function onboard(data) {
  return request('/onboard', { method: 'POST', body: JSON.stringify(data) })
}

/** Submit a daily log entry */
export function submitLog(data) {
  return request('/log', { method: 'POST', body: JSON.stringify(data) })
}

/** Get 7-day summary + current flag state for the dashboard */
export function getUserSummary(userId) {
  return request(`/user/${userId}/summary`)
}

/** Submit item 9 safety check response */
export function submitSafetyCheck(data) {
  return request('/safety-check', { method: 'POST', body: JSON.stringify(data) })
}

/** Check if the 2-week safety check cadence is due */
export function checkSafetyDue(userId) {
  return request(`/user/${userId}/due-safety-check`)
}

/** Get today's date as YYYY-MM-DD in LOCAL time (not UTC).
 *  Important: students in India (IST = UTC+5:30) would get
 *  yesterday's date if we used toISOString().split('T')[0].  */
export function localToday() {
  const d = new Date()
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, '0'),
    String(d.getDate()).padStart(2, '0'),
  ].join('-')
}
/** One turn of chat with the Wellbeing Agent (tool-using LLM agent) */
export function agentChat(data) {
  return request('/agent/chat', { method: 'POST', body: JSON.stringify(data) })
}

/** Latest automated agent nudge (written by the daily sweep), if any */
export function getAgentNudge(userId) {
  return request(`/user/${userId}/agent-nudge`)
}
