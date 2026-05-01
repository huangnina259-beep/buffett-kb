import { useState } from 'react'

interface Story {
  headline: string
  headline_en: string
  date: string
  summary: string
  signal: 'OPPORTUNITY' | 'RISK' | 'WATCH' | 'CONTEXT'
  source: string
}

const CATEGORIES = [
  {
    id: 'global', label: '全球商业', en: 'Global Business',
    prompt: 'Based on your knowledge of recent global business developments, identify 3-4 important stories for long-term value investors. Focus on corporate strategy shifts, competitive dynamics changes, and significant earnings trends. Avoid daily stock price movements.',
  },
  {
    id: 'us', label: '美国市场', en: 'US Markets',
    prompt: 'Based on your knowledge of recent US market and corporate developments, identify 3-4 important stories for value investors. Focus on major US company fundamentals, sector structural shifts, Fed policy impact on business economics. Avoid daily price noise.',
  },
  {
    id: 'china', label: '中国市场', en: 'China A-shares',
    prompt: 'Based on your knowledge of recent China A-share market developments, identify 3-4 important stories for value investors. Focus on regulatory changes, SOE reforms, major corporate fundamentals, and Beijing policy signals affecting listed companies.',
  },
  {
    id: 'hk', label: '香港市场', en: 'Hong Kong Markets',
    prompt: 'Based on your knowledge of recent Hong Kong market developments, identify 3-4 important stories for value investors. Focus on Hang Seng listed companies, HK-listed Chinese company fundamentals, notable valuation dislocations, and cross-border capital flow signals.',
  },
  {
    id: 'signal', label: '价值信号', en: 'Value Signals',
    prompt: 'Identify 3-4 notable value investing signals. Focus on: market dislocations, Berkshire Hathaway or Warren Buffett activity, major value investor moves, significant insider transactions, and situations where Mr. Market appears irrational.',
  },
  {
    id: 'macro', label: '宏观周期', en: 'Macro & Cycles',
    prompt: 'Identify 3-4 key macroeconomic data points relevant to value investors. Think Howard Marks framework: where are we in the credit cycle, what does the risk appetite indicate, how do current interest rates affect business valuations?',
  },
]

const SYSTEM_PROMPT = `You are a value investing analyst trained in the Buffett/Munger/Howard Marks tradition.

Respond ONLY with a valid JSON object. No markdown, no backticks, no explanation outside the JSON.

Required format:
{"stories":[{"headline":"中文标题","headline_en":"English headline","date":"时间背景如'2025年Q1'或'2024年下半年'","summary":"三层分析：①事件本质是什么（1句）②对企业护城河、管理层质量或估值的影响（1-2句）③对价值投资者的行动含义（1句）。总计不超过130字。","signal":"OPPORTUNITY","source":"具体来源如'Berkshire 2024年报'或'Financial Times'或'港交所公告'"}]}

signal must be exactly one of: OPPORTUNITY, RISK, WATCH, CONTEXT
Return 3-4 stories. Output ONLY the JSON object, nothing else.`

function getApiConfig(): { url: string; key: string; model: string } {
  return {
    url: localStorage.getItem('digest-api-url') || 'https://api.anthropic.com/v1/messages',
    key: localStorage.getItem('digest-api-key') || '',
    model: localStorage.getItem('digest-api-model') || 'claude-sonnet-4-20250514',
  }
}

async function callLLM(prompt: string): Promise<string> {
  const { url, key, model } = getApiConfig()
  if (!key) throw new Error('请先在设置中配置 API Key')

  const isAnthropic = url.includes('anthropic.com')

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  let body: string

  if (isAnthropic) {
    headers['x-api-key'] = key
    headers['anthropic-version'] = '2023-06-01'
    headers['anthropic-dangerous-direct-browser-access'] = 'true'
    body = JSON.stringify({
      model,
      max_tokens: 2000,
      system: SYSTEM_PROMPT,
      messages: [{ role: 'user', content: prompt }],
    })
  } else {
    headers['Authorization'] = `Bearer ${key}`
    body = JSON.stringify({
      model,
      max_tokens: 2000,
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: prompt },
      ],
    })
  }

  const res = await fetch(url, { method: 'POST', headers, body })
  const rawText = await res.text()
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${rawText.slice(0, 200)}`)

  const data = JSON.parse(rawText)
  if (data.error) throw new Error(`API错误: ${data.error.message || JSON.stringify(data.error)}`)

  if (isAnthropic) {
    return (data.content || []).filter((b: any) => b.type === 'text').map((b: any) => b.text).join('').trim()
  }
  return data.choices?.[0]?.message?.content?.trim() || ''
}

function parseStories(raw: string): Story[] {
  const text = raw.replace(/```json|```/gi, '').trim()
  const start = text.indexOf('{')
  const end = text.lastIndexOf('}')
  if (start === -1 || end === -1) throw new Error(`未找到JSON: ${text.slice(0, 80)}`)
  const parsed = JSON.parse(text.slice(start, end + 1))
  if (!Array.isArray(parsed.stories)) throw new Error('stories字段缺失')
  return parsed.stories
}

function SignalBadge({ signal }: { signal: string }) {
  const cfg: Record<string, { label: string; bg: string; color: string; border: string }> = {
    OPPORTUNITY: { label: '机会', bg: '#1a3a2a', color: '#4ade80', border: '#166534' },
    RISK: { label: '风险', bg: '#3a1a1a', color: '#f87171', border: '#991b1b' },
    WATCH: { label: '关注', bg: '#2a2a1a', color: '#fbbf24', border: '#92400e' },
    CONTEXT: { label: '背景', bg: '#1a2a3a', color: '#60a5fa', border: '#1e40af' },
  }
  const c = cfg[signal] || cfg.CONTEXT
  return (
    <span style={{
      fontSize: 10, fontFamily: 'monospace', fontWeight: 700,
      letterSpacing: '0.08em', padding: '2px 8px', borderRadius: 2,
      backgroundColor: c.bg, color: c.color, border: `1px solid ${c.border}`,
      whiteSpace: 'nowrap',
    }}>{c.label}</span>
  )
}

function StoryCard({ story, index }: { story: Story; index: number }) {
  const [open, setOpen] = useState(false)
  return (
    <div
      onClick={() => setOpen(!open)}
      style={{ borderBottom: '1px solid #1a1a1a', padding: '14px 0', cursor: 'pointer' }}
    >
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
        <span style={{ fontFamily: 'monospace', fontSize: 10, color: '#333', minWidth: 18, paddingTop: 3 }}>
          {String(index + 1).padStart(2, '0')}
        </span>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 6, alignItems: 'center' }}>
            <SignalBadge signal={story.signal} />
            {story.date && <span style={{ fontSize: 10, color: '#555', fontFamily: 'monospace' }}>{story.date}</span>}
            <span style={{ fontSize: 10, color: '#444', fontFamily: 'monospace' }}>· {story.source}</span>
          </div>
          <p style={{ margin: 0, fontSize: 14, fontFamily: 'Georgia, serif', color: '#e0d8c8', lineHeight: 1.5, fontWeight: 600 }}>
            {story.headline}
          </p>
          <p style={{ margin: '3px 0 0', fontSize: 10, color: '#3a3a3a', fontFamily: 'monospace' }}>
            {story.headline_en}
          </p>
          {open && (
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #1e1e1e' }}>
              <p style={{ margin: 0, fontSize: 13, color: '#b0a898', fontFamily: 'Georgia, serif', lineHeight: 1.85 }}>
                {story.summary}
              </p>
            </div>
          )}
        </div>
        <span style={{ color: '#333', fontSize: 10, paddingTop: 4, flexShrink: 0 }}>
          {open ? '▲' : '▼'}
        </span>
      </div>
    </div>
  )
}

function Panel({ cat, stories, loading, error, onFetch }: {
  cat: typeof CATEGORIES[0]
  stories: Story[]
  loading: boolean
  error: string | null
  onFetch: () => void
}) {
  return (
    <div style={{
      backgroundColor: '#0f0f0f',
      border: `1px solid ${loading ? '#3a3a3a' : '#1e1e1e'}`,
      borderRadius: 3, overflow: 'hidden', transition: 'border-color 0.2s',
    }}>
      <div style={{
        padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderBottom: (loading || error || stories.length > 0) ? '1px solid #181818' : 'none',
      }}>
        <div>
          <span style={{ fontFamily: 'Georgia, serif', fontWeight: 700, fontSize: 14, color: '#e0d8c8', marginRight: 8 }}>
            {cat.label}
          </span>
          <span style={{ fontFamily: 'monospace', fontSize: 10, color: '#333', letterSpacing: '0.05em' }}>
            {cat.en}
          </span>
        </div>
        <button
          onClick={onFetch} disabled={loading}
          style={{
            padding: '5px 13px', fontSize: 11, fontFamily: 'monospace', fontWeight: 700,
            letterSpacing: '0.06em',
            backgroundColor: loading ? '#181818' : '#e0d8c8',
            color: loading ? '#444' : '#0a0a0a',
            border: 'none', borderRadius: 2,
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? '生成中…' : stories.length > 0 ? '↺ 刷新' : '获取'}
        </button>
      </div>

      {loading && (
        <div style={{ padding: '24px 16px', textAlign: 'center' }}>
          <div style={{
            display: 'inline-block', width: 16, height: 16,
            border: '2px solid #222', borderTop: '2px solid #e0d8c8',
            borderRadius: '50%', animation: 'spin 0.8s linear infinite',
          }} />
          <p style={{ margin: '10px 0 0', color: '#444', fontSize: 11, fontFamily: 'monospace' }}>
            正在生成…
          </p>
        </div>
      )}

      {!loading && error && (
        <div style={{ padding: '14px 16px' }}>
          <p style={{ margin: 0, fontSize: 10, fontFamily: 'monospace', color: '#f87171', lineHeight: 1.7, wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>
            {error}
          </p>
        </div>
      )}

      {!loading && !error && stories.length > 0 && (
        <div style={{ padding: '0 16px' }}>
          {stories.map((s, i) => <StoryCard key={i} story={s} index={i} />)}
        </div>
      )}
    </div>
  )
}

function SettingsPanel({ onClose }: { onClose: () => void }) {
  const [url, setUrl] = useState(localStorage.getItem('digest-api-url') || 'https://api.anthropic.com/v1/messages')
  const [key, setKey] = useState(localStorage.getItem('digest-api-key') || '')
  const [model, setModel] = useState(localStorage.getItem('digest-api-model') || 'claude-sonnet-4-20250514')

  const save = () => {
    localStorage.setItem('digest-api-url', url)
    localStorage.setItem('digest-api-key', key)
    localStorage.setItem('digest-api-model', model)
    onClose()
  }

  return (
    <div style={{
      background: '#0f0f0f', border: '1px solid #1e1e1e', borderRadius: 3,
      padding: 20, marginBottom: 16,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <span style={{ fontFamily: 'Georgia, serif', fontWeight: 700, fontSize: 14, color: '#e0d8c8' }}>
          API 设置
        </span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer', fontSize: 14 }}>✕</button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div>
          <label style={{ display: 'block', fontFamily: 'monospace', fontSize: 10, color: '#666', marginBottom: 4, letterSpacing: '0.06em', textTransform: 'uppercase' as const }}>
            API URL
          </label>
          <input value={url} onChange={e => setUrl(e.target.value)}
            style={{ width: '100%', padding: '7px 10px', background: '#0a0a0a', border: '1px solid #2a2a2a', borderRadius: 2, color: '#e0d8c8', fontFamily: 'monospace', fontSize: 12 }}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontFamily: 'monospace', fontSize: 10, color: '#666', marginBottom: 4, letterSpacing: '0.06em', textTransform: 'uppercase' as const }}>
            API KEY
          </label>
          <input type="password" value={key} onChange={e => setKey(e.target.value)}
            style={{ width: '100%', padding: '7px 10px', background: '#0a0a0a', border: '1px solid #2a2a2a', borderRadius: 2, color: '#e0d8c8', fontFamily: 'monospace', fontSize: 12 }}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontFamily: 'monospace', fontSize: 10, color: '#666', marginBottom: 4, letterSpacing: '0.06em', textTransform: 'uppercase' as const }}>
            MODEL
          </label>
          <input value={model} onChange={e => setModel(e.target.value)}
            style={{ width: '100%', padding: '7px 10px', background: '#0a0a0a', border: '1px solid #2a2a2a', borderRadius: 2, color: '#e0d8c8', fontFamily: 'monospace', fontSize: 12 }}
          />
        </div>
        <button onClick={save} style={{
          padding: '7px 16px', background: '#e0d8c8', color: '#0a0a0a', border: 'none', borderRadius: 2,
          fontFamily: 'monospace', fontSize: 11, fontWeight: 700, cursor: 'pointer', alignSelf: 'flex-end',
        }}>
          保存
        </button>
      </div>
    </div>
  )
}

export default function DailyDigest() {
  const [data, setData] = useState<Record<string, Story[]>>({})
  const [loading, setLoading] = useState<Record<string, boolean>>({})
  const [errors, setErrors] = useState<Record<string, string | null>>({})
  const [cache, setCache] = useState<Record<string, { stories: Story[]; date: string }>>({})
  const [showSettings, setShowSettings] = useState(false)

  const todayKey = new Date().toISOString().slice(0, 10)
  const today = new Date().toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
  })

  const fetchCat = async (cat: typeof CATEGORIES[0], forceRefresh = false) => {
    if (!forceRefresh && cache[cat.id]?.date === todayKey) {
      setData(p => ({ ...p, [cat.id]: cache[cat.id].stories }))
      return
    }

    setLoading(p => ({ ...p, [cat.id]: true }))
    setErrors(p => ({ ...p, [cat.id]: null }))

    let lastError: Error | null = null
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const raw = await callLLM(cat.prompt)
        const stories = parseStories(raw)
        setData(p => ({ ...p, [cat.id]: stories }))
        setCache(p => ({ ...p, [cat.id]: { stories, date: todayKey } }))
        setLoading(p => ({ ...p, [cat.id]: false }))
        return
      } catch (e) {
        lastError = e as Error
        if (attempt === 0) await new Promise(r => setTimeout(r, 1500))
      }
    }

    setErrors(p => ({ ...p, [cat.id]: lastError?.message || '未知错误' }))
    setLoading(p => ({ ...p, [cat.id]: false }))
  }

  const fetchAll = () => { CATEGORIES.forEach(cat => fetchCat(cat)) }
  const anyLoading = Object.values(loading).some(Boolean)
  const hasKey = !!localStorage.getItem('digest-api-key')

  return (
    <div style={{ minHeight: '100vh', color: '#e0d8c8' }}>
      {/* Header */}
      <div style={{
        borderBottom: '1px solid #181818', padding: '20px 24px 16px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end',
        flexWrap: 'wrap', gap: 12,
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontFamily: 'Georgia, serif', fontWeight: 700, letterSpacing: '-0.01em' }}>
            每日商业简报
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: 11, fontFamily: 'monospace', color: '#333' }}>
            {today} · 价值投资者信息过滤器
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => setShowSettings(!showSettings)} style={{
            padding: '8px 14px', fontSize: 11, fontFamily: 'monospace',
            background: 'none', border: '1px solid #2a2a2a', borderRadius: 2,
            color: '#666', cursor: 'pointer',
          }}>
            ⚙ 设置
          </button>
          <button onClick={fetchAll} disabled={anyLoading || !hasKey} style={{
            padding: '8px 18px', fontSize: 11, fontFamily: 'monospace', fontWeight: 700,
            letterSpacing: '0.1em',
            backgroundColor: (anyLoading || !hasKey) ? '#181818' : '#e0d8c8',
            color: (anyLoading || !hasKey) ? '#444' : '#0a0a0a',
            border: 'none', borderRadius: 2,
            cursor: (anyLoading || !hasKey) ? 'not-allowed' : 'pointer',
          }}>
            {anyLoading ? '获取中…' : '▶ 一键获取全部'}
          </button>
        </div>
      </div>

      <div style={{ padding: '16px 24px' }}>
        {/* Settings */}
        {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}

        {/* No API key notice */}
        {!hasKey && !showSettings && (
          <div style={{
            background: '#1a2a3a', border: '1px solid #1e40af', borderRadius: 3,
            padding: '14px 16px', marginBottom: 16,
            fontSize: 12, color: '#60a5fa', fontFamily: 'monospace',
          }}>
            首次使用请点击「⚙ 设置」配置 API Key
          </div>
        )}

        {/* Legend */}
        <div style={{ marginBottom: 14, display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'center' }}>
          {([['机会', '#4ade80'], ['风险', '#f87171'], ['关注', '#fbbf24'], ['背景', '#60a5fa']] as const).map(([l, c]) => (
            <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 5, height: 5, borderRadius: '50%', backgroundColor: c }} />
              <span style={{ fontSize: 10, color: '#3a3a3a', fontFamily: 'monospace' }}>{l}</span>
            </div>
          ))}
          <span style={{ fontSize: 10, color: '#252525', fontFamily: 'monospace' }}>· 点击标题展开深度分析</span>
        </div>

        {/* Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
          gap: 12,
        }}>
          {CATEGORIES.map(cat => (
            <Panel
              key={cat.id} cat={cat}
              stories={data[cat.id] || []}
              loading={loading[cat.id] || false}
              error={errors[cat.id] || null}
              onFetch={() => fetchCat(cat, true)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
