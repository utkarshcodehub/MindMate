/**
 * AgentChat.jsx
 *
 * Chat panel for the Wellbeing Agent.
 *
 * Demo-critical feature: whenever the agent autonomously calls a tool
 * (fetching the user's data, running trend analysis), we render a small
 * "agent action" chip above the reply — making the agentic behaviour
 * VISIBLE, not just claimed.
 *
 * If a reply comes back with crisis=true, we surface the CrisisModal
 * via the onCrisis callback (same pattern as the rest of the app).
 */

import { useState, useRef, useEffect } from 'react'
import { agentChat, getAgentNudge } from '../api'

const TOOL_LABELS = {
  get_user_summary:    '📊 fetched your recent check-ins',
  get_trend_analysis:  '📈 analysed your 4-week trend',
  get_crisis_resources:'📞 looked up support services',
}

const SUGGESTIONS = [
  'How have I been doing this week?',
  'Is my sleep getting better or worse?',
  'Give me one small thing to try today',
]

export default function AgentChat({ userId, onCrisis }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        "Hi — I'm the Wellbeing Agent. I can read your own check-ins " +
        'and help you make sense of them. Ask me anything about how ' +
        "you've been doing lately.",
      tools: [],
    },
  ])
  const [input, setInput]     = useState('')
  const [busy, setBusy]       = useState(false)
  const bottomRef = useRef(null)

  // On mount: surface the latest AUTOMATED nudge (written by the daily
  // sweep with no human in the loop) as a message from the agent.
  useEffect(() => {
    let cancelled = false
    getAgentNudge(userId)
      .then(n => {
        if (cancelled || !n.has_nudge) return
        setMessages(m => [
          ...m,
          {
            role: 'assistant',
            content: n.message,
            tools: [],
            automated: true,
          },
        ])
      })
      .catch(() => {}) // nudge is a bonus, never an error state
    return () => { cancelled = true }
  }, [userId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  async function send(text) {
    const content = (text ?? input).trim()
    if (!content || busy) return
    setInput('')

    const nextMessages = [...messages, { role: 'user', content, tools: [] }]
    setMessages(nextMessages)
    setBusy(true)

    try {
      const res = await agentChat({
        user_id: userId,
        message: content,
        history: nextMessages
          .slice(-9, -1) // prior turns only, capped
          .map(({ role, content }) => ({ role, content })),
      })

      setMessages(m => [
        ...m,
        { role: 'assistant', content: res.reply, tools: res.tools_used || [] },
      ])

      if (res.crisis && onCrisis) {
        onCrisis({ resources: [], message: null })
      }
    } catch (err) {
      setMessages(m => [
        ...m,
        {
          role: 'assistant',
          content: `Sorry — I couldn't respond just now (${err.message}). Please try again.`,
          tools: [],
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card agent-chat">
      <div className="agent-header">
        <span className="agent-title">Your MindMate agent</span>
        <span className="muted agent-sub">
          reads your real data · not a therapist · not a diagnosis
        </span>
      </div>

      <div className="agent-messages">
        {messages.map((m, i) => (
          <div key={i} className={`agent-msg agent-msg-${m.role}`}>
            {m.automated && (
              <div className="agent-tools">
                <span className="agent-tool-chip agent-chip-auto">
                  🤖 sent automatically by the daily agent sweep
                </span>
              </div>
            )}
            {m.tools?.length > 0 && (
              <div className="agent-tools">
                {m.tools.map((t, j) => (
                  <span key={j} className="agent-tool-chip">
                    {TOOL_LABELS[t] || t}
                  </span>
                ))}
              </div>
            )}
            <div className="agent-bubble">{m.content}</div>
          </div>
        ))}
        {busy && (
          <div className="agent-msg agent-msg-assistant">
            <div className="agent-bubble agent-typing">thinking…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {messages.length <= 1 && (
        <div className="agent-suggestions">
          {SUGGESTIONS.map((s, i) => (
            <button key={i} className="agent-suggestion" onClick={() => send(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="agent-input-row">
        <input
          className="agent-input"
          value={input}
          placeholder="Ask about your week…"
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          disabled={busy}
        />
        <button className="agent-send" onClick={() => send()} disabled={busy || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  )
}
