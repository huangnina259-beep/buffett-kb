import { useState, useEffect, useRef } from 'react'
import type { Message } from '../types'
import styles from './TutorChat.module.css'

interface Props {
  messages: Message[]
  isStreaming: boolean
  currentHint: string
  onSend: (text: string) => void
}

/* ── simple inline bold: **text** → <strong>text</strong> ───── */
function renderContent(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    return <span key={i}>{part}</span>
  })
}

export default function TutorChat({ messages, isStreaming, currentHint, onSend }: Props) {
  const [input, setInput] = useState('')
  const [showHint, setShowHint] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  /* auto-scroll on new messages */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  /* reset hint visibility when hint changes (new cycle) */
  useEffect(() => {
    setShowHint(false)
  }, [currentHint])

  /* auto-resize textarea */
  useEffect(() => {
    const ta = textareaRef.current
    if (ta) {
      ta.style.height = 'auto'
      ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
    }
  }, [input])

  function handleSubmit() {
    const text = input.trim()
    if (!text || isStreaming) return
    onSend(text)
    setInput('')
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className={styles.chat}>
      {/* ── messages ─────────────────────────────────────────── */}
      <div className={styles.messages}>
        {messages.map(msg => (
          <div
            key={msg.id}
            className={msg.role === 'tutor' ? styles.tutorRow : styles.studentRow}
          >
            {msg.role === 'tutor' && (
              <div className={styles.avatar}>导</div>
            )}
            <div className={msg.role === 'tutor' ? styles.tutorBubble : styles.studentBubble}>
              {renderContent(msg.content)}
            </div>
          </div>
        ))}

        {isStreaming && messages[messages.length - 1]?.content === '' && (
          <div className={styles.tutorRow}>
            <div className={styles.avatar}>导</div>
            <div className={styles.typing}>
              <span /><span /><span />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── hint area ────────────────────────────────────────── */}
      {currentHint && (
        <div className={styles.hintArea}>
          {showHint ? (
            <div className={styles.hintContent}>
              <div className={styles.hintLabel}>提示</div>
              {currentHint}
            </div>
          ) : (
            <button className={styles.hintBtn} onClick={() => setShowHint(true)}>
              💡 求助
            </button>
          )}
        </div>
      )}

      {/* ── input area ───────────────────────────────────────── */}
      <div className={styles.inputArea}>
        <textarea
          ref={textareaRef}
          className={styles.textarea}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的回答…"
          rows={1}
          disabled={isStreaming}
        />
        <button
          className={styles.sendBtn}
          onClick={handleSubmit}
          disabled={isStreaming || !input.trim()}
        >
          提交
        </button>
      </div>
    </div>
  )
}
