import { useState } from 'react'
import DailyDigest from './pages/DailyDigest'
import Holdings from './pages/Holdings'
import Tutor from './pages/Tutor'
import Coach from './pages/Coach'
import KnowledgeBase from './pages/KnowledgeBase'

type Page = 'digest' | 'holdings' | 'tutor' | 'coach' | 'kb'

const NAV_ITEMS: { id: Page; label: string; en: string }[] = [
  { id: 'digest', label: '每日简报', en: 'Daily Digest' },
  { id: 'holdings', label: '持仓分析', en: 'Holdings' },
  { id: 'tutor', label: '思维训练营', en: 'Tutor' },
  { id: 'coach', label: '投资教练', en: 'Coach' },
  { id: 'kb', label: '知识库问答', en: 'Knowledge Base' },
]

export default function App() {
  const [page, setPage] = useState<Page>('digest')

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* Sidebar */}
      <aside style={{
        width: 220, minWidth: 220, height: '100vh',
        background: '#080808', borderRight: '1px solid #181818',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* Brand */}
        <div style={{ padding: '20px 18px 16px', borderBottom: '1px solid #141414' }}>
          <div style={{
            fontFamily: 'monospace', fontSize: 9, color: '#333',
            letterSpacing: '0.2em', marginBottom: 6,
          }}>
            THE COMPOUNDER
          </div>
          <div style={{
            fontSize: 18, fontWeight: 700, color: '#e0d8c8',
            letterSpacing: '-0.01em',
          }}>
            漏木工作台
          </div>
          <div style={{
            fontFamily: 'monospace', fontSize: 10, color: '#333',
            marginTop: 4,
          }}>
            {new Date().toLocaleDateString('zh-CN', {
              year: 'numeric', month: 'long', day: 'numeric',
            })}
          </div>
        </div>

        {/* Nav */}
        <nav style={{ padding: '12px 0', flex: 1 }}>
          {NAV_ITEMS.map(item => {
            const active = page === item.id
            return (
              <button
                key={item.id}
                onClick={() => setPage(item.id)}
                style={{
                  display: 'block', width: '100%', textAlign: 'left',
                  padding: '10px 18px',
                  background: active ? '#141414' : 'transparent',
                  border: 'none', cursor: 'pointer',
                  borderLeft: active ? '2px solid #e0d8c8' : '2px solid transparent',
                  transition: 'all 0.15s',
                }}
              >
                <div style={{
                  fontSize: 14, fontWeight: active ? 700 : 400,
                  color: active ? '#e0d8c8' : '#666',
                  fontFamily: 'Georgia, serif',
                }}>
                  {item.label}
                </div>
                <div style={{
                  fontFamily: 'monospace', fontSize: 10,
                  color: active ? '#444' : '#2a2a2a',
                  marginTop: 2, letterSpacing: '0.05em',
                }}>
                  {item.en}
                </div>
              </button>
            )
          })}
        </nav>

        {/* Footer */}
        <div style={{
          padding: '12px 18px', borderTop: '1px solid #141414',
          fontFamily: 'monospace', fontSize: 10, color: '#222',
        }}>
          复利国 · 非投资建议
        </div>
      </aside>

      {/* Main content */}
      <main style={{
        flex: 1, height: '100vh', overflow: 'auto',
        background: '#0a0a0a',
      }}>
        {page === 'digest' && <DailyDigest />}
        {page === 'holdings' && <Holdings />}
        {page === 'tutor' && <Tutor />}
        {page === 'coach' && <Coach />}
        {page === 'kb' && <KnowledgeBase />}
      </main>
    </div>
  )
}
