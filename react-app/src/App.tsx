import { useState, useCallback, useRef } from 'react'
import type { Message, CurriculumState } from './types'
import { CURRICULUM, OPENING_MESSAGES, INITIAL_STATE } from './data/curriculum'
import LearningMap from './components/LearningMap'
import TutorChat from './components/TutorChat'
import FrameworkMap from './components/FrameworkMap'
import styles from './App.module.css'

const API_BASE = ''  // same origin

export default function App() {
  const [messages, setMessages] = useState<Message[]>(OPENING_MESSAGES)
  const [currState, setCurrState] = useState<CurriculumState>(INITIAL_STATE)
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  /* ── current hint (from curriculum) ─────────────────────────── */
  const currentHint = (() => {
    for (const mod of CURRICULUM) {
      const cycle = mod.cycles.find(c => c.id === currState.currentCycle)
      if (cycle) return cycle.hint
    }
    return ''
  })()

  /* ── send message to tutor API ──────────────────────────────── */
  const handleSend = useCallback(async (text: string) => {
    const studentMsg: Message = {
      id: `s-${Date.now()}`,
      role: 'student',
      content: text,
      timestamp: Date.now(),
    }
    setMessages(prev => [...prev, studentMsg])
    setIsStreaming(true)

    // Build history for API (skip intro messages)
    const history = [...messages, studentMsg]
      .filter(m => m.id !== 'intro' && m.id !== 'method')
      .map(m => ({ role: m.role === 'tutor' ? 'assistant' : 'user', content: m.content }))

    const tutorMsgId = `t-${Date.now()}`
    setMessages(prev => [...prev, { id: tutorMsgId, role: 'tutor', content: '', timestamp: Date.now() }])

    try {
      abortRef.current = new AbortController()
      const resp = await fetch(`${API_BASE}/api/tutor/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history,
          curriculum_state: currState,
        }),
        signal: abortRef.current.signal,
      })

      const reader = resp.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) throw new Error('No reader')

      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const evt = JSON.parse(line.slice(6))
            if (evt.type === 'token') {
              setMessages(prev =>
                prev.map(m => m.id === tutorMsgId ? { ...m, content: m.content + evt.text } : m)
              )
            } else if (evt.type === 'done') {
              // Process state updates from tutor
              if (evt.advance_to) {
                setCurrState(prev => ({
                  ...prev,
                  completedCycles: [...prev.completedCycles, prev.currentCycle],
                  currentCycle: evt.advance_to,
                  currentModule: parseInt(evt.advance_to.split('.')[0]),
                }))
              }
              if (evt.framework_insight) {
                setCurrState(prev => ({
                  ...prev,
                  frameworkInsights: [...prev.frameworkInsights, evt.framework_insight],
                }))
              }
              if (evt.parking_lot) {
                setCurrState(prev => ({
                  ...prev,
                  parkingLot: [...prev.parkingLot, evt.parking_lot],
                }))
              }
            }
          } catch { /* skip malformed lines */ }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setMessages(prev =>
          prev.map(m => m.id === tutorMsgId ? { ...m, content: '连接出错，请重试。' } : m)
        )
      }
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }, [messages, currState])

  /* ── progress calculation ────────────────────────────────────── */
  const totalCycles = CURRICULUM.reduce((sum, m) => sum + m.cycles.length, 0)
  const completedCount = currState.completedCycles.length
  const progressPercent = Math.round((completedCount / totalCycles) * 100)

  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <div className={styles.brand}>复利国 · 实践课程</div>
        <div className={styles.case}>案例：可口可乐</div>
      </header>

      <div className={styles.body}>
        <aside className={styles.leftSidebar}>
          <LearningMap
            modules={CURRICULUM}
            state={currState}
            progressPercent={progressPercent}
          />
        </aside>

        <main className={styles.chatArea}>
          <TutorChat
            messages={messages}
            isStreaming={isStreaming}
            currentHint={currentHint}
            onSend={handleSend}
          />
        </main>

        <aside className={styles.rightSidebar}>
          <FrameworkMap modules={CURRICULUM} state={currState} />
        </aside>
      </div>
    </div>
  )
}
