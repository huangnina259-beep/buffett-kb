import { useState, useRef, useEffect } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Source {
  title: string
  author: string
  text: string
}

interface QAMessage {
  id: string
  role: 'user' | 'ai'
  content: string
  sources?: Source[]
  followUps?: string[]
}

// ─── Suggested questions ──────────────────────────────────────────────────────

const SUGGESTED = [
  '什么是价值投资的四大支柱？',
  '如何判断一家公司有护城河？',
  '安全边际是什么意思？',
  '巴菲特如何评估管理层？',
  '什么是能力圈？',
  '复利的本质是什么？',
  '什么样的公司值得长期持有？',
  '如何理解市场先生这个概念？',
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function apiUrl(path: string): string {
  const base = localStorage.getItem('digest-backend-url') || ''
  return base ? `${base.replace(/\/$/, '')}${path}` : path
}

// ─── Source card ──────────────────────────────────────────────────────────────

function SourceCard({ source, idx }: { source: Source; idx: number }) {
  const [expanded, setExpanded] = useState(false)
  const preview = source.text.slice(0, 120)
  const hasMore = source.text.length > 120

  return (
    <div style={{
      background: '#0f0f0f', border: '1px solid #1e1e1e', borderRadius: 5,
      padding: '12px 14px', fontSize: 13,
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
        <div style={{
          width: 20, height: 20, borderRadius: '50%', background: '#1a1a1a',
          border: '1px solid #2a2a2a', flexShrink: 0, display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          fontFamily: 'monospace', fontSize: 10, color: '#555',
        }}>{idx + 1}</div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
            {source.author && (
              <span style={{
                fontFamily: 'monospace', fontSize: 10, color: '#c0b898',
                letterSpacing: '0.06em',
              }}>{source.author}</span>
            )}
            {source.title && (
              <span style={{ fontFamily: 'monospace', fontSize: 10, color: '#444' }}>
                · {source.title}
              </span>
            )}
          </div>
          <div style={{ color: '#777', lineHeight: 1.65, fontFamily: 'Georgia, serif' }}>
            {expanded ? source.text : preview}
            {hasMore && !expanded && '…'}
          </div>
          {hasMore && (
            <button
              onClick={() => setExpanded(e => !e)}
              style={{
                background: 'none', border: 'none', color: '#444', cursor: 'pointer',
                fontSize: 11, fontFamily: 'monospace', marginTop: 4, padding: 0,
              }}
            >
              {expanded ? '收起' : '展开原文'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Message ──────────────────────────────────────────────────────────────────

function Message({ msg, onFollowUp }: { msg: QAMessage; onFollowUp: (q: string) => void }) {
  if (msg.role === 'user') {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 28 }}>
        <div style={{
          maxWidth: 560, background: '#141414', border: '1px solid #2a2a2a',
          borderRadius: '8px 0 8px 8px', padding: '12px 18px',
          fontSize: 15, color: '#e0d8c8', lineHeight: 1.7, fontFamily: 'Georgia, serif',
        }}>
          {msg.content}
        </div>
      </div>
    )
  }

  return (
    <div style={{ marginBottom: 36 }}>
      {/* Answer */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 16 }}>
        <div style={{
          width: 30, height: 30, borderRadius: '50%', background: '#141414',
          border: '1px solid #2a2a2a', flexShrink: 0, display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          fontFamily: 'monospace', fontSize: 11, color: '#c0b898',
        }}>知</div>
        <div style={{
          flex: 1, fontSize: 15, color: '#c0b898', lineHeight: 1.8,
          fontFamily: 'Georgia, serif', whiteSpace: 'pre-wrap',
        }}>
          {msg.content}
        </div>
      </div>

      {/* Sources */}
      {msg.sources && msg.sources.length > 0 && (
        <div style={{ marginLeft: 44, marginBottom: 14 }}>
          <div style={{
            fontFamily: 'monospace', fontSize: 10, color: '#333',
            letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8,
          }}>
            原文出处 · {msg.sources.length} 条
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {msg.sources.map((s, i) => (
              <SourceCard key={i} source={s} idx={i} />
            ))}
          </div>
        </div>
      )}

      {/* Follow-ups */}
      {msg.followUps && msg.followUps.length > 0 && (
        <div style={{ marginLeft: 44 }}>
          <div style={{
            fontFamily: 'monospace', fontSize: 10, color: '#333',
            letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8,
          }}>
            延伸提问
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {msg.followUps.map((q, i) => (
              <button
                key={i}
                onClick={() => onFollowUp(q)}
                style={{
                  background: 'none', border: '1px solid #2a2a2a', borderRadius: 20,
                  color: '#666', padding: '6px 14px', fontSize: 13,
                  fontFamily: 'Georgia, serif', cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={e => {
                  ;(e.target as HTMLElement).style.borderColor = '#444'
                  ;(e.target as HTMLElement).style.color = '#999'
                }}
                onMouseLeave={e => {
                  ;(e.target as HTMLElement).style.borderColor = '#2a2a2a'
                  ;(e.target as HTMLElement).style.color = '#666'
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function KnowledgeBase() {
  const [messages, setMessages] = useState<QAMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<Array<{ role: string; content: string }>>([])
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const ta = textareaRef.current
    if (ta) { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 140) + 'px' }
  }, [input])

  async function ask(question: string) {
    if (!question.trim() || loading) return
    setInput('')
    setLoading(true)

    const userMsg: QAMessage = {
      id: `u-${Date.now()}`, role: 'user', content: question,
    }
    const aiMsgId = `ai-${Date.now() + 1}`
    const loadingMsg: QAMessage = {
      id: aiMsgId, role: 'ai', content: '查询知识库中…',
    }
    setMessages(prev => [...prev, userMsg, loadingMsg])

    try {
      const res = await fetch(apiUrl('/query'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          language: 'cn',
          history,
        }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      if (data.error) throw new Error(data.error)

      setMessages(prev => prev.map(m =>
        m.id === aiMsgId ? {
          ...m,
          content: data.answer || '（无回答）',
          sources: data.sources || [],
          followUps: data.follow_ups || [],
        } : m
      ))

      // Update conversation history for context
      setHistory(prev => [
        ...prev,
        { role: 'user', content: question },
        { role: 'assistant', content: data.answer || '' },
      ])
    } catch (e: any) {
      setMessages(prev => prev.map(m =>
        m.id === aiMsgId ? { ...m, content: `[错误: ${e.message}]` } : m
      ))
    } finally {
      setLoading(false)
    }
  }

  function handleSend() {
    ask(input.trim())
  }

  // ── Empty state ──────────────────────────────────────────────────────────────
  if (messages.length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Center content */}
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          padding: '40px 24px',
        }}>
          <div style={{ maxWidth: 580, width: '100%', textAlign: 'center' }}>
            <div style={{
              fontFamily: 'monospace', fontSize: 10, color: '#333',
              letterSpacing: '0.2em', marginBottom: 14,
            }}>
              THE COMPOUNDER · 知识库
            </div>
            <h1 style={{ fontSize: 26, color: '#e0d8c8', marginBottom: 10, letterSpacing: '-0.02em' }}>
              问任何价值投资的问题
            </h1>
            <p style={{ color: '#555', fontSize: 14, lineHeight: 1.8, marginBottom: 36, fontFamily: 'Georgia, serif' }}>
              基于巴菲特、芒格、霍华德·马克斯、李录的原始文献，给你有出处的回答。
            </p>

            {/* Quick start chips */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center', marginBottom: 48 }}>
              {SUGGESTED.slice(0, 6).map((q, i) => (
                <button
                  key={i}
                  onClick={() => ask(q)}
                  style={{
                    background: 'none', border: '1px solid #2a2a2a', borderRadius: 20,
                    color: '#666', padding: '8px 16px', fontSize: 13,
                    fontFamily: 'Georgia, serif', cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={e => {
                    ;(e.target as HTMLElement).style.borderColor = '#444'
                    ;(e.target as HTMLElement).style.color = '#999'
                  }}
                  onMouseLeave={e => {
                    ;(e.target as HTMLElement).style.borderColor = '#2a2a2a'
                    ;(e.target as HTMLElement).style.color = '#666'
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Input */}
        <InputBar
          value={input}
          onChange={setInput}
          onSend={handleSend}
          loading={loading}
          textareaRef={textareaRef}
        />
      </div>
    )
  }

  // ── Chat view ────────────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{
        padding: '12px 24px', background: '#080808',
        borderBottom: '1px solid #181818', flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ fontFamily: 'monospace', fontSize: 11, color: '#444', letterSpacing: '0.1em' }}>
          知识库问答 · 原文出处
        </div>
        <button
          onClick={() => { setMessages([]); setHistory([]) }}
          style={{
            background: 'none', border: '1px solid #2a2a2a', color: '#555',
            padding: '5px 12px', borderRadius: 4, cursor: 'pointer',
            fontSize: 11, fontFamily: 'monospace',
          }}
        >
          新对话
        </button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '32px 28px 16px', maxWidth: 760, width: '100%', margin: '0 auto', boxSizing: 'border-box' }}>
        {messages.map(msg => (
          <Message key={msg.id} msg={msg} onFollowUp={ask} />
        ))}
        {loading && messages[messages.length - 1]?.role === 'ai' && messages[messages.length - 1]?.content === '查询知识库中…' && (
          <div style={{ marginLeft: 44, display: 'flex', gap: 4 }}>
            {[0, 1, 2].map(i => (
              <div key={i} style={{
                width: 6, height: 6, borderRadius: '50%', background: '#333',
                animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
              }} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <InputBar
        value={input}
        onChange={setInput}
        onSend={handleSend}
        loading={loading}
        textareaRef={textareaRef}
      />
    </div>
  )
}

// ─── Input bar (shared) ───────────────────────────────────────────────────────

function InputBar({ value, onChange, onSend, loading, textareaRef }: {
  value: string
  onChange: (v: string) => void
  onSend: () => void
  loading: boolean
  textareaRef: React.RefObject<HTMLTextAreaElement>
}) {
  return (
    <div style={{
      padding: '14px 24px 20px', borderTop: '1px solid #181818',
      background: '#080808', flexShrink: 0,
    }}>
      <div style={{ maxWidth: 760, margin: '0 auto', display: 'flex', gap: 10 }}>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend() } }}
          placeholder="输入你的价值投资问题…（Enter 发送）"
          rows={1}
          disabled={loading}
          style={{
            flex: 1, background: '#0f0f0f', border: '1px solid #2a2a2a',
            borderRadius: 4, color: '#e0d8c8', fontFamily: 'Georgia, serif',
            fontSize: 14, padding: '10px 14px', resize: 'none', outline: 'none',
          }}
        />
        <button
          onClick={onSend}
          disabled={loading || !value.trim()}
          style={{
            padding: '10px 20px', alignSelf: 'flex-end',
            background: loading || !value.trim() ? '#1a1a1a' : '#e0d8c8',
            color: loading || !value.trim() ? '#444' : '#0a0a0a',
            border: 'none', borderRadius: 4,
            cursor: loading || !value.trim() ? 'not-allowed' : 'pointer',
            fontFamily: 'Georgia, serif', fontSize: 14, fontWeight: 700,
            flexShrink: 0,
          }}
        >
          {loading ? '…' : '提问'}
        </button>
      </div>
      <div style={{
        maxWidth: 760, margin: '8px auto 0',
        fontFamily: 'monospace', fontSize: 10, color: '#2a2a2a', textAlign: 'center',
      }}>
        回答来源于价值投资经典文献 · 仅供学习参考 · 非投资建议
      </div>
    </div>
  )
}
