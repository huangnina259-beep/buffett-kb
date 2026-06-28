import { useState, useEffect, useRef, useCallback } from 'react'
import type { Message } from '../types'

// ─── API types ────────────────────────────────────────────────────────────────

interface UserState {
  onboarding_completed: boolean
  onboarding_skipped: boolean
  onboarding_current_module: string
}

interface CompanyItem {
  company_id: string
  company_name: string
  ticker: string
  last_updated: string
  session_count: number
  modules_completed: string[]
}

interface CompanySession {
  session_id: string
  date: string
  status: string
  modules_completed: string[]
  record: Record<string, string>
  conversation: Array<{ role: string; content: string }>
}

interface CompanyHistory {
  company_id: string
  company_name: string
  ticker: string
  first_analysis: string
  last_updated: string
  sessions: CompanySession[]
}

// ─── Constants ────────────────────────────────────────────────────────────────

const ONBOARDING_MODULES = [
  '模块一：商业模式',
  '模块二：护城河',
  '模块三：财务质量',
  '模块四：管理层',
  '模块五：估值与决策',
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getBackendUrl(): string {
  return localStorage.getItem('digest-backend-url') || ''
}

function apiUrl(path: string): string {
  const base = getBackendUrl()
  return base ? `${base.replace(/\/$/, '')}${path}` : path
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const s = {
  sidebar: {
    width: 200, minWidth: 200,
    background: '#080808', borderRight: '1px solid #181818',
    display: 'flex', flexDirection: 'column' as const, overflow: 'hidden',
  },
  sidebarHd: {
    padding: '14px 14px 10px',
    fontFamily: 'monospace', fontSize: 10, letterSpacing: '0.12em',
    textTransform: 'uppercase' as const, color: '#444',
  },
  companyItem: (active: boolean): React.CSSProperties => ({
    padding: '9px 14px', cursor: 'pointer',
    background: active ? '#141414' : 'transparent',
    borderLeft: active ? '2px solid #e0d8c8' : '2px solid transparent',
    transition: 'all 0.15s',
  }),
  companyName: { fontSize: 13, color: '#c0b898', fontWeight: 600 } as React.CSSProperties,
  companyMeta: { fontSize: 10, color: '#444', fontFamily: 'monospace', marginTop: 2 } as React.CSSProperties,
  newBtn: {
    margin: '10px 10px 0', padding: '9px 12px',
    border: '1px dashed #2a2a2a', borderRadius: 4,
    background: 'transparent', color: '#555', cursor: 'pointer',
    fontSize: 12, fontFamily: 'Georgia, serif', textAlign: 'center' as const,
    transition: 'all 0.15s',
  },
  main: { flex: 1, display: 'flex', flexDirection: 'column' as const, overflow: 'hidden', background: '#0a0a0a' },
  header: {
    padding: '14px 24px', background: '#080808',
    borderBottom: '1px solid #181818', flexShrink: 0,
  },
  chatWrap: { flex: 1, display: 'flex', flexDirection: 'column' as const, overflow: 'hidden' },
  messages: { flex: 1, overflowY: 'auto' as const, padding: '24px 24px 0' },
  coachBubble: {
    maxWidth: 560, background: '#141414', border: '1px solid #1e1e1e',
    borderRadius: '0 8px 8px 8px', padding: '12px 16px',
    fontSize: 14, color: '#c0b898', lineHeight: 1.75,
    fontFamily: 'Georgia, serif', whiteSpace: 'pre-wrap' as const,
  },
  userBubble: {
    maxWidth: 480, background: '#0f0f0f', border: '1px solid #2a2a2a',
    borderRadius: '8px 0 8px 8px', padding: '12px 16px',
    fontSize: 14, color: '#888', lineHeight: 1.7,
    fontFamily: 'Georgia, serif', whiteSpace: 'pre-wrap' as const,
    marginLeft: 'auto',
  },
  inputArea: {
    padding: '16px 24px', borderTop: '1px solid #181818',
    background: '#080808', flexShrink: 0, display: 'flex', gap: 10,
  },
  textarea: {
    flex: 1, background: '#0f0f0f', border: '1px solid #2a2a2a',
    borderRadius: 4, color: '#e0d8c8', fontFamily: 'Georgia, serif',
    fontSize: 14, padding: '10px 14px', resize: 'none' as const,
    outline: 'none',
  },
  sendBtn: (disabled: boolean): React.CSSProperties => ({
    padding: '10px 20px', background: disabled ? '#1a1a1a' : '#e0d8c8',
    color: disabled ? '#444' : '#0a0a0a', border: 'none', borderRadius: 4,
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontFamily: 'Georgia, serif', fontSize: 14, fontWeight: 700,
    flexShrink: 0, alignSelf: 'flex-end',
  }),
}

// ─── Chat component ────────────────────────────────────────────────────────────

function ChatArea({
  messages, isStreaming, onSend, headerSlot, footerSlot,
}: {
  messages: Message[]
  isStreaming: boolean
  onSend: (text: string) => void
  headerSlot?: React.ReactNode
  footerSlot?: React.ReactNode
}) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const ta = textareaRef.current
    if (ta) { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 140) + 'px' }
  }, [input])

  function handleSubmit() {
    const text = input.trim()
    if (!text || isStreaming) return
    onSend(text)
    setInput('')
  }

  return (
    <div style={s.chatWrap}>
      {headerSlot}
      <div style={s.messages}>
        {messages.map(msg => (
          <div key={msg.id} style={{ marginBottom: 16, display: 'flex', flexDirection: 'column' }}>
            <div style={{ fontSize: 10, fontFamily: 'monospace', color: '#333', marginBottom: 5,
              textAlign: msg.role === 'student' ? 'right' : 'left' }}>
              {msg.role === 'tutor' ? '教练' : '我'}
            </div>
            <div style={msg.role === 'tutor' ? s.coachBubble : s.userBubble}>
              {msg.content || (isStreaming && msg === messages[messages.length - 1] ? '…' : '')}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      {footerSlot}
      <div style={s.inputArea}>
        <textarea
          ref={textareaRef}
          style={s.textarea}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() } }}
          placeholder="输入你的想法…（Enter 发送）"
          rows={1}
          disabled={isStreaming}
        />
        <button style={s.sendBtn(isStreaming || !input.trim())} onClick={handleSubmit}
          disabled={isStreaming || !input.trim()}>
          发送
        </button>
      </div>
    </div>
  )
}

// ─── History view ─────────────────────────────────────────────────────────────

function HistoryView({ history, onNewSession, onBack }: {
  history: CompanyHistory
  onNewSession: () => void
  onBack: () => void
}) {
  const [openIdx, setOpenIdx] = useState<number | null>(0)

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '24px 28px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <button onClick={onBack} style={{
          background: 'none', border: '1px solid #2a2a2a', color: '#666',
          padding: '6px 12px', borderRadius: 4, cursor: 'pointer', fontSize: 12, fontFamily: 'monospace',
        }}>← 返回</button>
        <div>
          <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#444', letterSpacing: '0.1em' }}>分析历史</div>
          <div style={{ fontSize: 18, color: '#e0d8c8', marginTop: 2 }}>
            {history.company_name}{history.ticker && <span style={{ fontSize: 12, color: '#555', marginLeft: 8 }}>{history.ticker}</span>}
          </div>
        </div>
        <button onClick={onNewSession} style={{
          marginLeft: 'auto', background: '#e0d8c8', color: '#0a0a0a',
          border: 'none', borderRadius: 4, padding: '8px 18px',
          cursor: 'pointer', fontSize: 13, fontFamily: 'Georgia, serif', fontWeight: 700,
        }}>开始新一轮分析</button>
      </div>

      {history.sessions.length === 0 && (
        <div style={{ color: '#444', fontSize: 14, fontFamily: 'Georgia, serif' }}>暂无分析记录。</div>
      )}

      {[...history.sessions].reverse().map((session, idx) => (
        <div key={session.session_id} style={{
          background: '#0f0f0f', border: '1px solid #1e1e1e', borderRadius: 6,
          marginBottom: 14, overflow: 'hidden',
        }}>
          <div
            onClick={() => setOpenIdx(openIdx === idx ? null : idx)}
            style={{ padding: '14px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12 }}
          >
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, color: '#c0b898', fontWeight: 600 }}>
                第 {history.sessions.length - idx} 次分析
                <span style={{ marginLeft: 10, fontSize: 11, fontFamily: 'monospace', color: '#444',
                  fontWeight: 400 }}>
                  {session.date} · {session.modules_completed.length} 个模块 · {session.status === 'completed' ? '已完成' : '进行中'}
                </span>
              </div>
              {session.modules_completed.length > 0 && (
                <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
                  {session.modules_completed.map(m => (
                    <span key={m} style={{
                      fontSize: 10, fontFamily: 'monospace', padding: '2px 8px',
                      background: '#1a2a1a', color: '#4ade80', borderRadius: 3,
                    }}>{m}</span>
                  ))}
                </div>
              )}
            </div>
            <span style={{ color: '#444', fontSize: 12 }}>{openIdx === idx ? '▲' : '▼'}</span>
          </div>

          {openIdx === idx && (
            <div style={{ borderTop: '1px solid #1a1a1a', padding: '14px 18px' }}>
              {/* Records */}
              {Object.keys(session.record).length > 0 && (
                <div style={{ marginBottom: 14 }}>
                  <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#444', marginBottom: 8 }}>模块小结</div>
                  {Object.entries(session.record).map(([mod, summary]) => (
                    <div key={mod} style={{ marginBottom: 8 }}>
                      <div style={{ fontSize: 11, fontFamily: 'monospace', color: '#666', marginBottom: 3 }}>{mod}</div>
                      <div style={{ fontSize: 13, color: '#888', lineHeight: 1.6 }}>{summary}</div>
                    </div>
                  ))}
                </div>
              )}
              {/* Conversation */}
              {session.conversation.length > 0 && (
                <div>
                  <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#444', marginBottom: 8 }}>对话记录</div>
                  <div style={{ maxHeight: 300, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {session.conversation.map((msg, i) => (
                      <div key={i} style={{
                        padding: '8px 12px', borderRadius: 4,
                        background: msg.role === 'assistant' ? '#141414' : '#0f0f0f',
                        border: '1px solid #1e1e1e', fontSize: 13, color: '#777', lineHeight: 1.6,
                      }}>
                        <span style={{ fontSize: 10, fontFamily: 'monospace', color: '#444', marginRight: 8 }}>
                          {msg.role === 'assistant' ? '教练' : '我'}
                        </span>
                        {msg.content}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ─── Main Coach page ──────────────────────────────────────────────────────────

type Screen = 'loading' | 'onboarding-choice' | 'onboarding-chat' | 'main'
type MainView = 'start' | 'chat' | 'history'

export default function Coach() {
  // ── Top-level screen state
  const [screen, setScreen] = useState<Screen>('loading')
  const [loadError, setLoadError] = useState('')

  // ── Onboarding state
  const [onboardingModuleIdx, setOnboardingModuleIdx] = useState(0)
  const [onboardingMessages, setOnboardingMessages] = useState<Message[]>([])
  const [onboardingStreaming, setOnboardingStreaming] = useState(false)
  const onboardingHistoryRef = useRef<Array<{ role: 'user' | 'assistant'; content: string }>>([])

  // ── Main layout state
  const [companies, setCompanies] = useState<CompanyItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [mainView, setMainView] = useState<MainView>('start')
  const [historyData, setHistoryData] = useState<CompanyHistory | null>(null)

  // ── New/active company state
  const [companyName, setCompanyName] = useState('')
  const [ticker, setTicker] = useState('')
  const [activeCompany, setActiveCompany] = useState({ name: '', ticker: '', id: '' })

  // ── Chat state
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const apiHistoryRef = useRef<Array<{ role: 'user' | 'assistant'; content: string }>>([])

  // ── Load initial state ──────────────────────────────────────────────────────
  useEffect(() => {
    async function init() {
      try {
        const [stateRes, companiesRes] = await Promise.all([
          fetch(apiUrl('/api/coach/state')),
          fetch(apiUrl('/api/coach/companies')),
        ])
        const state: UserState = await stateRes.json()
        const comps: CompanyItem[] = await companiesRes.json()
        setCompanies(comps)

        if (!state.onboarding_completed && !state.onboarding_skipped) {
          // Find resume module if partially done
          const savedModule = state.onboarding_current_module
          const idx = ONBOARDING_MODULES.findIndex(m => m === savedModule)
          if (idx > 0) setOnboardingModuleIdx(idx)
          setScreen('onboarding-choice')
        } else {
          setScreen('main')
        }
      } catch (e: any) {
        setLoadError(e.message)
        setScreen('main') // fallback: show main anyway
      }
    }
    init()
  }, [])

  // ── Fetch companies list ────────────────────────────────────────────────────
  const refreshCompanies = useCallback(async () => {
    try {
      const res = await fetch(apiUrl('/api/coach/companies'))
      setCompanies(await res.json())
    } catch { /* silent */ }
  }, [])

  // ── Save record to backend ──────────────────────────────────────────────────
  const saveRecord = useCallback(async (opts: {
    companyId: string; companyName: string; ticker: string
    conversation: Array<{ role: string; content: string }>
    status?: string
    moduleId?: string; moduleSummary?: string; skipped?: boolean
  }) => {
    try {
      await fetch(apiUrl('/api/coach/record'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_id: opts.companyId,
          company_name: opts.companyName,
          ticker: opts.ticker,
          conversation: opts.conversation,
          status: opts.status || 'in_progress',
          module_id: opts.moduleId || '',
          module_summary: opts.moduleSummary || '',
          skipped: opts.skipped || false,
        }),
      })
    } catch { /* silent */ }
  }, [])

  // ── Stream coach API ────────────────────────────────────────────────────────
  const streamCoach = useCallback(async (opts: {
    message: string
    history: Array<{ role: string; content: string }>
    company?: string
    mode?: string
    onboardingModule?: string
    onToken: (text: string) => void
    onDone: (finalText: string, record: string | null) => void
    onError: (msg: string) => void
  }) => {
    try {
      const res = await fetch(apiUrl('/api/coach/stream'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: opts.message,
          history: opts.history,
          company: opts.company || '',
          mode: opts.mode || 'normal',
          onboarding_module: opts.onboardingModule || ONBOARDING_MODULES[0],
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const evt = JSON.parse(line.slice(6))
            if (evt.type === 'token') {
              fullContent += evt.text
              opts.onToken(fullContent)
            } else if (evt.type === 'done') {
              opts.onDone(evt.final_answer || fullContent, evt.record || null)
            } else if (evt.type === 'error') {
              opts.onError(evt.message)
            }
          } catch { /* skip malformed */ }
        }
      }
    } catch (e: any) {
      opts.onError(e.message)
    }
  }, [])

  // ─────────────────────────────────────────────────────────────────────────────
  // ONBOARDING CHAT LOGIC
  // ─────────────────────────────────────────────────────────────────────────────

  async function startOnboarding() {
    setScreen('onboarding-chat')
    setOnboardingStreaming(true)
    const msgId = `coach-${Date.now()}`
    setOnboardingMessages([{ id: msgId, role: 'tutor', content: '', timestamp: Date.now() }])

    await streamCoach({
      message: '你好，我准备好开始学习了。',
      history: [],
      mode: 'onboarding',
      onboardingModule: ONBOARDING_MODULES[onboardingModuleIdx],
      onToken: (text) => setOnboardingMessages(prev =>
        prev.map(m => m.id === msgId ? { ...m, content: text } : m)
      ),
      onDone: (finalText) => {
        setOnboardingMessages(prev =>
          prev.map(m => m.id === msgId ? { ...m, content: finalText } : m)
        )
        onboardingHistoryRef.current.push({ role: 'assistant', content: finalText })
        setOnboardingStreaming(false)
      },
      onError: (msg) => {
        setOnboardingMessages(prev =>
          prev.map(m => m.id === msgId ? { ...m, content: `[错误: ${msg}]` } : m)
        )
        setOnboardingStreaming(false)
      },
    })
  }

  async function sendOnboardingMessage(text: string) {
    const userMsgId = `u-${Date.now()}`
    const coachMsgId = `coach-${Date.now() + 1}`
    onboardingHistoryRef.current.push({ role: 'user', content: text })
    setOnboardingMessages(prev => [
      ...prev,
      { id: userMsgId, role: 'student', content: text, timestamp: Date.now() },
      { id: coachMsgId, role: 'tutor', content: '', timestamp: Date.now() + 1 },
    ])
    setOnboardingStreaming(true)

    await streamCoach({
      message: text,
      history: onboardingHistoryRef.current.slice(0, -1), // exclude the user msg we just pushed
      mode: 'onboarding',
      onboardingModule: ONBOARDING_MODULES[onboardingModuleIdx],
      onToken: (content) => setOnboardingMessages(prev =>
        prev.map(m => m.id === coachMsgId ? { ...m, content } : m)
      ),
      onDone: (finalText) => {
        setOnboardingMessages(prev =>
          prev.map(m => m.id === coachMsgId ? { ...m, content: finalText } : m)
        )
        onboardingHistoryRef.current.push({ role: 'assistant', content: finalText })
        setOnboardingStreaming(false)
      },
      onError: (msg) => {
        setOnboardingMessages(prev =>
          prev.map(m => m.id === coachMsgId ? { ...m, content: `[错误: ${msg}]` } : m)
        )
        setOnboardingStreaming(false)
      },
    })
  }

  async function advanceOnboardingModule() {
    const nextIdx = onboardingModuleIdx + 1
    if (nextIdx >= ONBOARDING_MODULES.length) {
      // Mark completed
      await fetch(apiUrl('/api/coach/state'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ onboarding_completed: true }),
      })
      setScreen('main')
      return
    }
    setOnboardingModuleIdx(nextIdx)
    // Save progress
    await fetch(apiUrl('/api/coach/state'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ onboarding_current_module: ONBOARDING_MODULES[nextIdx] }),
    })
    // Start next module with fresh context
    onboardingHistoryRef.current = []
    setOnboardingStreaming(true)
    const msgId = `coach-${Date.now()}`
    setOnboardingMessages(prev => [
      ...prev,
      {
        id: `sep-${Date.now()}`, role: 'tutor',
        content: `▸ ${ONBOARDING_MODULES[nextIdx]}`,
        timestamp: Date.now(),
      },
      { id: msgId, role: 'tutor', content: '', timestamp: Date.now() + 1 },
    ])

    await streamCoach({
      message: '进入下一个模块。',
      history: [],
      mode: 'onboarding',
      onboardingModule: ONBOARDING_MODULES[nextIdx],
      onToken: (text) => setOnboardingMessages(prev =>
        prev.map(m => m.id === msgId ? { ...m, content: text } : m)
      ),
      onDone: (finalText) => {
        setOnboardingMessages(prev =>
          prev.map(m => m.id === msgId ? { ...m, content: finalText } : m)
        )
        onboardingHistoryRef.current.push({ role: 'assistant', content: finalText })
        setOnboardingStreaming(false)
      },
      onError: (msg) => {
        setOnboardingMessages(prev =>
          prev.map(m => m.id === msgId ? { ...m, content: `[错误: ${msg}]` } : m)
        )
        setOnboardingStreaming(false)
      },
    })
  }

  async function skipOnboarding() {
    await fetch(apiUrl('/api/coach/state'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ onboarding_skipped: true }),
    })
    setScreen('main')
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // MAIN CHAT LOGIC
  // ─────────────────────────────────────────────────────────────────────────────

  async function startAnalysis() {
    if (!companyName.trim()) return
    const name = companyName.trim()
    const tick = ticker.trim()
    const id = name.toLowerCase().replace(/\s+/g, '_')
    setActiveCompany({ name, ticker: tick, id })
    setMessages([])
    apiHistoryRef.current = []
    setMainView('chat')
    setSelectedId(id)

    // Initial coach message
    setIsStreaming(true)
    const msgId = `coach-${Date.now()}`
    setMessages([{ id: msgId, role: 'tutor', content: '', timestamp: Date.now() }])

    await streamCoach({
      message: `我想分析${name}${tick ? `（${tick}）` : ''}这家公司。`,
      history: [],
      company: name,
      mode: 'normal',
      onToken: (text) => setMessages(prev =>
        prev.map(m => m.id === msgId ? { ...m, content: text } : m)
      ),
      onDone: async (finalText) => {
        setMessages(prev =>
          prev.map(m => m.id === msgId ? { ...m, content: finalText } : m)
        )
        apiHistoryRef.current.push({ role: 'assistant', content: finalText })
        setIsStreaming(false)
        // Save initial record
        await saveRecord({
          companyId: id, companyName: name, ticker: tick,
          conversation: [{ role: 'assistant', content: finalText }],
        })
        refreshCompanies()
      },
      onError: (err) => {
        setMessages(prev =>
          prev.map(m => m.id === msgId ? { ...m, content: `[错误: ${err}]` } : m)
        )
        setIsStreaming(false)
      },
    })
  }

  async function sendMessage(text: string) {
    const userMsgId = `u-${Date.now()}`
    const coachMsgId = `coach-${Date.now() + 1}`
    apiHistoryRef.current.push({ role: 'user', content: text })
    setMessages(prev => [
      ...prev,
      { id: userMsgId, role: 'student', content: text, timestamp: Date.now() },
      { id: coachMsgId, role: 'tutor', content: '', timestamp: Date.now() + 1 },
    ])
    setIsStreaming(true)

    await streamCoach({
      message: text,
      history: apiHistoryRef.current.slice(0, -1),
      company: activeCompany.name,
      mode: 'normal',
      onToken: (content) => setMessages(prev =>
        prev.map(m => m.id === coachMsgId ? { ...m, content } : m)
      ),
      onDone: async (finalText) => {
        setMessages(prev =>
          prev.map(m => m.id === coachMsgId ? { ...m, content: finalText } : m)
        )
        apiHistoryRef.current.push({ role: 'assistant', content: finalText })
        setIsStreaming(false)

        // Save full conversation
        const conv = apiHistoryRef.current.map(h => ({ role: h.role, content: h.content }))
        await saveRecord({
          companyId: activeCompany.id,
          companyName: activeCompany.name,
          ticker: activeCompany.ticker,
          conversation: conv,
        })
        refreshCompanies()
      },
      onError: (err) => {
        setMessages(prev =>
          prev.map(m => m.id === coachMsgId ? { ...m, content: `[错误: ${err}]` } : m)
        )
        setIsStreaming(false)
      },
    })
  }

  async function selectCompany(item: CompanyItem) {
    setSelectedId(item.company_id)
    setMainView('history')
    try {
      const res = await fetch(apiUrl(`/api/coach/company/${item.company_id}`))
      setHistoryData(await res.json())
    } catch { /* silent */ }
  }

  function startNewSessionForCompany() {
    if (!historyData) return
    setCompanyName(historyData.company_name)
    setTicker(historyData.ticker || '')
    const name = historyData.company_name
    const tick = historyData.ticker || ''
    const id = historyData.company_id
    setActiveCompany({ name, ticker: tick, id })
    setMessages([])
    apiHistoryRef.current = []
    setMainView('chat')

    setIsStreaming(true)
    const msgId = `coach-${Date.now()}`
    setMessages([{ id: msgId, role: 'tutor', content: '', timestamp: Date.now() }])

    streamCoach({
      message: `我想继续分析${name}${tick ? `（${tick}）` : ''}，进行新一轮深入研究。`,
      history: [],
      company: name,
      mode: 'normal',
      onToken: (text) => setMessages(prev =>
        prev.map(m => m.id === msgId ? { ...m, content: text } : m)
      ),
      onDone: async (finalText) => {
        setMessages(prev =>
          prev.map(m => m.id === msgId ? { ...m, content: finalText } : m)
        )
        apiHistoryRef.current.push({ role: 'assistant', content: finalText })
        setIsStreaming(false)
        await saveRecord({
          companyId: id, companyName: name, ticker: tick,
          conversation: [{ role: 'assistant', content: finalText }],
        })
        refreshCompanies()
      },
      onError: (err) => {
        setMessages(prev =>
          prev.map(m => m.id === msgId ? { ...m, content: `[错误: ${err}]` } : m)
        )
        setIsStreaming(false)
      },
    })
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────────

  // Loading
  if (screen === 'loading') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#444', fontFamily: 'monospace', fontSize: 12 }}>
        {loadError ? `连接失败: ${loadError}` : '连接中…'}
      </div>
    )
  }

  // Onboarding choice
  if (screen === 'onboarding-choice') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', background: '#0a0a0a', padding: 40 }}>
        <div style={{ maxWidth: 480, width: '100%' }}>
          <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#333', letterSpacing: '0.2em', marginBottom: 12 }}>
            THE COMPOUNDER · 投资教练
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 700, color: '#e0d8c8', marginBottom: 8, letterSpacing: '-0.02em' }}>
            欢迎使用投资教练
          </h1>
          <p style={{ color: '#555', fontSize: 14, lineHeight: 1.8, marginBottom: 32, fontFamily: 'Georgia, serif' }}>
            教练会用苏格拉底式提问，帮你建立分析任何公司的基本框架。
            从商业模式到估值，5 个模块，每次只问一个问题。
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 36 }}>
            {ONBOARDING_MODULES.map((mod, i) => (
              <div key={mod} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '10px 0', borderBottom: '1px solid #141414' }}>
                <div style={{
                  width: 24, height: 24, borderRadius: '50%',
                  background: i < onboardingModuleIdx ? '#1a2a1a' : '#141414',
                  border: `1px solid ${i < onboardingModuleIdx ? '#4ade80' : '#2a2a2a'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontFamily: 'monospace', fontSize: 11,
                  color: i < onboardingModuleIdx ? '#4ade80' : '#444', flexShrink: 0,
                }}>{i < onboardingModuleIdx ? '✓' : i + 1}</div>
                <div style={{ fontSize: 13, color: i < onboardingModuleIdx ? '#666' : '#888' }}>{mod}</div>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 12 }}>
            <button
              onClick={startOnboarding}
              style={{
                flex: 1, padding: '14px 0', background: '#e0d8c8', color: '#0a0a0a',
                border: 'none', borderRadius: 4, cursor: 'pointer',
                fontSize: 15, fontWeight: 700, fontFamily: 'Georgia, serif',
              }}
            >
              {onboardingModuleIdx > 0 ? '继续新手引导' : '开始新手引导'}
            </button>
            <button
              onClick={skipOnboarding}
              style={{
                flex: 1, padding: '14px 0', background: 'transparent', color: '#555',
                border: '1px solid #2a2a2a', borderRadius: 4, cursor: 'pointer',
                fontSize: 15, fontFamily: 'Georgia, serif',
              }}
            >
              跳过，直接分析
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Onboarding chat
  if (screen === 'onboarding-chat') {
    const isLast = onboardingModuleIdx === ONBOARDING_MODULES.length - 1
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Module progress bar */}
        <div style={{
          padding: '12px 24px', background: '#080808', borderBottom: '1px solid #181818',
          display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0,
        }}>
          <div style={{ flex: 1, display: 'flex', gap: 6 }}>
            {ONBOARDING_MODULES.map((mod, i) => (
              <div key={mod} title={mod} style={{
                flex: 1, height: 4, borderRadius: 2,
                background: i < onboardingModuleIdx ? '#c0b898' : i === onboardingModuleIdx ? '#666' : '#1a1a1a',
                transition: 'background 0.3s',
              }} />
            ))}
          </div>
          <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#444', whiteSpace: 'nowrap' }}>
            {ONBOARDING_MODULES[onboardingModuleIdx]}
          </div>
          <button onClick={skipOnboarding} style={{
            background: 'none', border: 'none', color: '#333', cursor: 'pointer', fontSize: 11, fontFamily: 'monospace',
          }}>跳过</button>
        </div>

        <ChatArea
          messages={onboardingMessages}
          isStreaming={onboardingStreaming}
          onSend={sendOnboardingMessage}
          footerSlot={
            <div style={{ padding: '10px 24px 0', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                onClick={advanceOnboardingModule}
                disabled={onboardingStreaming}
                style={{
                  padding: '8px 18px',
                  background: onboardingStreaming ? '#1a1a1a' : isLast ? '#4ade80' : '#e0d8c8',
                  color: onboardingStreaming ? '#444' : '#0a0a0a',
                  border: 'none', borderRadius: 4, cursor: onboardingStreaming ? 'not-allowed' : 'pointer',
                  fontSize: 12, fontFamily: 'Georgia, serif', fontWeight: 700,
                }}
              >
                {isLast ? '完成引导 →' : `进入${ONBOARDING_MODULES[onboardingModuleIdx + 1]?.split('：')[0] || '下一模块'} →`}
              </button>
            </div>
          }
        />
      </div>
    )
  }

  // ── Main layout ──────────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Sidebar */}
      <aside style={s.sidebar}>
        <div style={s.sidebarHd}>已分析公司</div>
        <button
          onClick={() => { setSelectedId(null); setMainView('start'); setCompanyName(''); setTicker('') }}
          style={s.newBtn}
        >
          + 分析新公司
        </button>

        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          {companies.length === 0 && (
            <div style={{ padding: '12px 14px', fontSize: 11, color: '#333', fontFamily: 'monospace' }}>
              暂无记录
            </div>
          )}
          {companies.map(item => (
            <div
              key={item.company_id}
              onClick={() => selectCompany(item)}
              style={s.companyItem(selectedId === item.company_id)}
            >
              <div style={s.companyName}>{item.company_name}</div>
              <div style={s.companyMeta}>
                {item.ticker && `${item.ticker} · `}
                {item.session_count} 次 · {item.last_updated}
              </div>
            </div>
          ))}
        </div>
      </aside>

      {/* Main area */}
      <div style={s.main}>
        {mainView === 'start' && (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            height: '100%', padding: 40,
          }}>
            <div style={{ maxWidth: 420, width: '100%' }}>
              <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#333', letterSpacing: '0.2em', marginBottom: 10 }}>
                投资教练 · 苏格拉底式对话
              </div>
              <h2 style={{ fontSize: 22, color: '#e0d8c8', marginBottom: 6, letterSpacing: '-0.02em' }}>
                分析一家公司
              </h2>
              <p style={{ color: '#555', fontSize: 13, lineHeight: 1.7, marginBottom: 28, fontFamily: 'Georgia, serif' }}>
                输入公司名，教练会引导你从商业模式、护城河、财务、管理层、估值五个维度展开分析。
              </p>

              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontFamily: 'monospace', fontSize: 10, color: '#444', letterSpacing: '0.1em', marginBottom: 6 }}>
                  公司名称
                </label>
                <input
                  value={companyName}
                  onChange={e => setCompanyName(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') startAnalysis() }}
                  placeholder="如：微泰医疗、苹果、茅台"
                  style={{
                    width: '100%', padding: '10px 14px', background: '#0f0f0f',
                    border: '1px solid #2a2a2a', borderRadius: 4, color: '#e0d8c8',
                    fontFamily: 'Georgia, serif', fontSize: 14, boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ marginBottom: 24 }}>
                <label style={{ display: 'block', fontFamily: 'monospace', fontSize: 10, color: '#444', letterSpacing: '0.1em', marginBottom: 6 }}>
                  股票代码（选填）
                </label>
                <input
                  value={ticker}
                  onChange={e => setTicker(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') startAnalysis() }}
                  placeholder="如：HK:2235"
                  style={{
                    width: '100%', padding: '10px 14px', background: '#0f0f0f',
                    border: '1px solid #2a2a2a', borderRadius: 4, color: '#e0d8c8',
                    fontFamily: 'Georgia, serif', fontSize: 14, boxSizing: 'border-box',
                  }}
                />
              </div>

              <button
                onClick={startAnalysis}
                disabled={!companyName.trim()}
                style={{
                  width: '100%', padding: '13px 0',
                  background: companyName.trim() ? '#e0d8c8' : '#1a1a1a',
                  color: companyName.trim() ? '#0a0a0a' : '#444',
                  border: 'none', borderRadius: 4,
                  cursor: companyName.trim() ? 'pointer' : 'not-allowed',
                  fontSize: 15, fontWeight: 700, fontFamily: 'Georgia, serif',
                }}
              >
                开始分析
              </button>
            </div>
          </div>
        )}

        {mainView === 'chat' && (
          <ChatArea
            messages={messages}
            isStreaming={isStreaming}
            onSend={sendMessage}
            headerSlot={
              <div style={s.header}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#444', letterSpacing: '0.1em' }}>
                      正在分析
                    </div>
                    <div style={{ fontSize: 16, color: '#e0d8c8', marginTop: 2 }}>
                      {activeCompany.name}
                      {activeCompany.ticker && (
                        <span style={{ fontSize: 12, color: '#555', marginLeft: 8 }}>{activeCompany.ticker}</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => { setSelectedId(activeCompany.id); selectCompany({ company_id: activeCompany.id, company_name: activeCompany.name, ticker: activeCompany.ticker, last_updated: '', session_count: 0, modules_completed: [] }) }}
                    style={{ background: 'none', border: '1px solid #2a2a2a', color: '#555', padding: '6px 12px', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontFamily: 'monospace' }}
                  >
                    查看历史
                  </button>
                </div>
              </div>
            }
          />
        )}

        {mainView === 'history' && historyData && (
          <HistoryView
            history={historyData}
            onNewSession={startNewSessionForCompany}
            onBack={() => { setMainView('start'); setSelectedId(null) }}
          />
        )}

        {mainView === 'history' && !historyData && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#444', fontFamily: 'monospace', fontSize: 12 }}>
            加载中…
          </div>
        )}
      </div>
    </div>
  )
}
