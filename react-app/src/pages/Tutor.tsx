import { useState, useRef, useCallback } from 'react'
import TutorChat from '../components/TutorChat'
import type { Message } from '../types'

const CHAPTERS = [
  { id: 'ch1', title: '股票 = 公司的一部分', sub: 'Graham 第一原则' },
  { id: 'ch2', title: '价格 ≠ 价值', sub: '内在价值' },
  { id: 'ch3', title: '市场先生', sub: 'Mr. Market' },
  { id: 'ch4', title: '复利的力量', sub: 'ROIC × 时间' },
  { id: 'ch5', title: '能力圈', sub: 'Circle of Competence' },
  { id: 'ch6', title: '安全边际', sub: 'Margin of Safety' },
  { id: 'ch7', title: '长期主义的真实代价', sub: '耐心是稀缺品质' },
]

interface TutorState {
  currentChapter: string
  completedChapters: string[]
}

function getBackendUrl(): string {
  return localStorage.getItem('digest-backend-url') || ''
}

export default function Tutor() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [tutorState, setTutorState] = useState<TutorState>({
    currentChapter: 'ch1',
    completedChapters: [],
  })
  const [started, setStarted] = useState(false)

  const apiHistoryRef = useRef<Array<{ role: 'user' | 'assistant'; content: string }>>([])
  const tutorStateRef = useRef(tutorState)
  tutorStateRef.current = tutorState

  const callTutorApi = useCallback(async (userText: string, state: TutorState, tutorMsgId: string) => {
    const backendUrl = getBackendUrl()
    const endpoint = backendUrl
      ? `${backendUrl.replace(/\/$/, '')}/api/tutor/stream`
      : '/api/tutor/stream'

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          history: apiHistoryRef.current,
          curriculum_state: state,
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
              setMessages(prev => prev.map(m => m.id === tutorMsgId ? { ...m, content: fullContent } : m))
            } else if (evt.type === 'done') {
              fullContent = evt.final_answer || fullContent
              setMessages(prev => prev.map(m => m.id === tutorMsgId ? { ...m, content: fullContent } : m))

              if (userText) apiHistoryRef.current.push({ role: 'user', content: userText })
              apiHistoryRef.current.push({ role: 'assistant', content: fullContent })

              if (evt.advance_to) {
                setTutorState(prev => ({
                  completedChapters: [...prev.completedChapters, prev.currentChapter],
                  currentChapter: evt.advance_to,
                }))
              }
            } else if (evt.type === 'error') {
              setMessages(prev => prev.map(m =>
                m.id === tutorMsgId ? { ...m, content: `[错误: ${evt.message}]` } : m
              ))
            }
          } catch { /* skip malformed SSE lines */ }
        }
      }
    } catch (e: any) {
      setMessages(prev => prev.map(m =>
        m.id === tutorMsgId ? { ...m, content: `[连接错误: ${e.message}。请检查后端服务是否在运行。]` } : m
      ))
    } finally {
      setIsStreaming(false)
    }
  }, [])

  async function startSession() {
    setStarted(true)
    setIsStreaming(true)
    const tutorMsgId = `t-${Date.now()}`
    setMessages([{ id: tutorMsgId, role: 'tutor', content: '', timestamp: Date.now() }])
    await callTutorApi('', tutorState, tutorMsgId)
  }

  async function handleSend(text: string) {
    const userMsg: Message = { id: `u-${Date.now()}`, role: 'student', content: text, timestamp: Date.now() }
    const tutorMsgId = `t-${Date.now() + 1}`
    setMessages(prev => [...prev, userMsg, { id: tutorMsgId, role: 'tutor', content: '', timestamp: Date.now() + 1 }])
    setIsStreaming(true)
    await callTutorApi(text, tutorStateRef.current, tutorMsgId)
  }

  const chapterIdx = CHAPTERS.findIndex(c => c.id === tutorState.currentChapter)
  const currentChapter = CHAPTERS[Math.max(0, chapterIdx)]
  const completedCount = tutorState.completedChapters.length
  const isDone = tutorState.currentChapter === 'done'

  // ── Start screen ────────────────────────────────────────────────────────────
  if (!started) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        height: '100%', background: '#0a0a0a', padding: 40,
      }}>
        <div style={{ maxWidth: 520, width: '100%' }}>
          <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#333', letterSpacing: '0.2em', marginBottom: 12 }}>
            THE COMPOUNDER · 思维训练营
          </div>
          <h1 style={{ fontSize: 28, fontWeight: 700, color: '#e0d8c8', marginBottom: 8, letterSpacing: '-0.02em' }}>
            价值投资理论课
          </h1>
          <p style={{ color: '#555', fontSize: 14, lineHeight: 1.7, marginBottom: 32, fontFamily: 'Georgia, serif' }}>
            7 个章节，苏格拉底式对话。导师不讲课——只问问题，你来回答，直到真正理解为止。
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 36 }}>
            {CHAPTERS.map((ch, i) => (
              <div key={ch.id} style={{
                display: 'flex', alignItems: 'center', gap: 14,
                padding: '10px 0', borderBottom: '1px solid #141414',
              }}>
                <div style={{
                  width: 24, height: 24, borderRadius: '50%',
                  background: '#141414', border: '1px solid #2a2a2a',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontFamily: 'monospace', fontSize: 11, color: '#444', flexShrink: 0,
                }}>
                  {i + 1}
                </div>
                <div>
                  <div style={{ fontSize: 13.5, color: '#888', fontWeight: 500 }}>{ch.title}</div>
                  <div style={{ fontSize: 11, color: '#333', marginTop: 2, fontFamily: 'monospace' }}>{ch.sub}</div>
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={startSession}
            style={{
              width: '100%', padding: '14px 0',
              background: '#e0d8c8', color: '#0a0a0a',
              border: 'none', borderRadius: 4, cursor: 'pointer',
              fontSize: 15, fontWeight: 700, letterSpacing: '0.03em',
              fontFamily: 'Georgia, serif',
            }}
          >
            开始学习
          </button>
        </div>
      </div>
    )
  }

  // ── Chapter progress header ──────────────────────────────────────────────────
  const progressPct = (completedCount / CHAPTERS.length) * 100

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#fff' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 20,
        padding: '12px 24px', background: '#080808',
        borderBottom: '1px solid #181818', flexShrink: 0,
      }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#333', letterSpacing: '0.15em', marginBottom: 3 }}>
            {isDone ? '课程完成' : `第 ${chapterIdx + 1} 章 / ${CHAPTERS.length}`}
          </div>
          <div style={{ fontSize: 13.5, color: '#c0b898', fontWeight: 600 }}>
            {isDone ? '恭喜完成全部章节' : currentChapter?.title}
          </div>
        </div>

        {/* Progress bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ display: 'flex', gap: 3 }}>
            {CHAPTERS.map((ch, i) => {
              const done = tutorState.completedChapters.includes(ch.id)
              const active = ch.id === tutorState.currentChapter
              return (
                <div key={ch.id} style={{
                  width: 20, height: 4, borderRadius: 2,
                  background: done ? '#c0b898' : active ? '#666' : '#222',
                  transition: 'background 0.4s',
                }} />
              )
            })}
          </div>
          <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#444' }}>
            {Math.round(progressPct)}%
          </div>
        </div>
      </div>

      {/* Chat */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <TutorChat
          messages={messages}
          isStreaming={isStreaming}
          currentHint=""
          onSend={handleSend}
        />
      </div>
    </div>
  )
}
