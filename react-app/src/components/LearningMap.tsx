import { useEffect, useRef } from 'react'
import type { Module, CurriculumState } from '../types'
import styles from './LearningMap.module.css'

interface Props {
  modules: Module[]
  state: CurriculumState
  progressPercent: number
}

/* ── clean SVG icons (monochrome, 16×16) ─────────────────────── */
const ICONS: Record<number, JSX.Element> = {
  1: ( // building / business
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 14V4l6-2.5L14 4v10" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/><path d="M5 7h2M5 10h2M9 7h2M9 10h2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/><path d="M6 14v-2.5h4V14" stroke="currentColor" strokeWidth="1.2"/></svg>
  ),
  2: ( // shield / moat
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 1.5L2.5 4v4c0 3.5 3 5.8 5.5 7 2.5-1.2 5.5-3.5 5.5-7V4L8 1.5z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/><path d="M6 8l1.5 1.5L10.5 6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>
  ),
  3: ( // chart / financials
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 13h12" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/><path d="M4 13V8M7 13V5M10 13V7M13 13V3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>
  ),
  4: ( // person / management
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="2.5" stroke="currentColor" strokeWidth="1.3"/><path d="M3 14c0-2.8 2.2-5 5-5s5 2.2 5 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
  ),
  5: ( // scale / valuation
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2v12M4 5l4-3 4 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/><path d="M3 9l2 4h-4l2-4zM11 9l2 4h-4l2-4z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/></svg>
  ),
}

const CHECK = (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7.5l3 3 5-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
)

const MODULE_GOALS = [
  '一句话说清商业模式',
  '判断护城河变宽还是变窄',
  '用 ROIC 验证竞争优势',
  '评估管理层资本配置能力',
  '区分好公司和好投资',
]

export default function LearningMap({ modules, state, progressPercent }: Props) {
  const currentModuleId = state.currentModule
  const currentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    currentRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [currentModuleId])

  return (
    <div className={styles.map}>
      {/* ── header ────────────────────────────────────────────── */}
      <div className={styles.header}>
        <h3 className={styles.title}>学习地图</h3>
        <div className={styles.progressWrap}>
          <div className={styles.progressBar}>
            <div className={styles.progressFill} style={{ width: `${progressPercent}%` }} />
          </div>
          <span className={styles.progressLabel}>
            {progressPercent > 0 ? `${progressPercent}%` : '出发'}
          </span>
        </div>
      </div>

      {/* ── trail ─────────────────────────────────────────────── */}
      <div className={styles.trail}>
        <div className={styles.stations}>
          {modules.map((mod, idx) => {
            const isCompleted = mod.cycles.every(c => state.completedCycles.includes(c.id))
            const isCurrent = mod.id === currentModuleId
            const isFuture = mod.id > currentModuleId
            const cyclesDone = mod.cycles.filter(c => state.completedCycles.includes(c.id)).length
            const cyclesTotal = mod.cycles.length

            return (
              <div key={mod.id} className={styles.station}>
                {/* vertical connector */}
                <div className={`${styles.line} ${isCompleted ? styles.lineDone : ''}`} />

                {/* node */}
                <div
                  ref={isCurrent ? currentRef : undefined}
                  className={`${styles.node} ${isCurrent ? styles.nodeCurrent : ''} ${isCompleted ? styles.nodeDone : ''} ${isFuture ? styles.nodeFuture : ''}`}
                >
                  {/* icon */}
                  <div className={`${styles.icon} ${isCurrent ? styles.iconCurrent : ''} ${isCompleted ? styles.iconDone : ''}`}>
                    {isCompleted ? CHECK : ICONS[mod.id]}
                  </div>

                  {/* content */}
                  <div className={styles.info}>
                    <div className={styles.modHeader}>
                      <span className={styles.modTitle}>{mod.title}</span>
                      {isCurrent && <span className={styles.currentTag}>进行中</span>}
                      {isCompleted && <span className={styles.doneTag}>已掌握</span>}
                    </div>
                    <div className={styles.modGoal}>{MODULE_GOALS[idx]}</div>

                    {/* current: expanded view */}
                    {isCurrent && (
                      <div className={styles.expanded}>
                        <div className={styles.miniProgress}>
                          {Array.from({ length: cyclesTotal }).map((_, ci) => (
                            <div
                              key={ci}
                              className={`${styles.miniBar} ${ci < cyclesDone ? styles.miniBarDone : ci === cyclesDone ? styles.miniBarActive : ''}`}
                            />
                          ))}
                        </div>
                        <div className={styles.cycles}>
                          {mod.cycles.map(cycle => {
                            const done = state.completedCycles.includes(cycle.id)
                            const active = cycle.id === state.currentCycle
                            return (
                              <div
                                key={cycle.id}
                                className={`${styles.cycle} ${active ? styles.cycleActive : ''} ${done ? styles.cycleDone : ''}`}
                              >
                                <span className={styles.cycleMark}>
                                  {done ? '✓' : active ? '›' : '·'}
                                </span>
                                {cycle.title}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* summit */}
        <div className={styles.summit}>
          <div className={styles.summitIcon}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M2 16l6-12 4 6 6-8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/><path d="M2 16h16" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>
          </div>
          <div>
            <div className={styles.summitTitle}>终点：独立分析能力</div>
            <div className={styles.summitDesc}>拿到可复用的分析框架</div>
          </div>
        </div>
      </div>
    </div>
  )
}
