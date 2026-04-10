import { useEffect, useRef } from 'react'
import type { Module, CurriculumState } from '../types'
import styles from './LearningMap.module.css'

interface Props {
  modules: Module[]
  state: CurriculumState
  progressPercent: number
}

const MODULE_ICONS = ['🏠', '🛡️', '📊', '👤', '💰']
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

      {/* ── trail (top=module1, bottom=summit) ─────────────────── */}
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
                {/* vertical line segment */}
                <div className={`${styles.line} ${isCompleted ? styles.lineDone : ''}`} />

                {/* node */}
                <div
                  ref={isCurrent ? currentRef : undefined}
                  className={`${styles.node} ${isCurrent ? styles.nodeCurrent : ''} ${isCompleted ? styles.nodeDone : ''} ${isFuture ? styles.nodeFuture : ''}`}
                >
                  <div className={`${styles.icon} ${isCurrent ? styles.iconCurrent : ''} ${isCompleted ? styles.iconDone : ''}`}>
                    {isCompleted ? '✓' : MODULE_ICONS[idx]}
                  </div>

                  <div className={styles.info}>
                    <div className={styles.modTitle}>
                      {isCurrent && <span className={styles.hereBadge}>📍</span>}
                      {mod.title}
                    </div>
                    <div className={styles.modGoal}>{MODULE_GOALS[idx]}</div>

                    {/* current module: show cycles + progress */}
                    {isCurrent && (
                      <>
                        <div className={styles.miniProgress}>
                          {Array.from({ length: cyclesTotal }).map((_, ci) => (
                            <div
                              key={ci}
                              className={`${styles.miniDot} ${ci < cyclesDone ? styles.miniDotDone : ci === cyclesDone ? styles.miniDotActive : ''}`}
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
                                <span className={styles.cycleIcon}>
                                  {done ? '✓' : active ? '▶' : '○'}
                                </span>
                                {cycle.title}
                              </div>
                            )
                          })}
                        </div>
                      </>
                    )}

                    {isCompleted && <div className={styles.doneBadge}>已掌握</div>}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* summit — at bottom, the destination */}
        <div className={styles.summit}>
          <div className={styles.summitIcon}>🏔️</div>
          <div className={styles.summitTitle}>终点：独立分析能力</div>
          <div className={styles.summitDesc}>拿到你自己的分析框架，分析任何公司</div>
        </div>
      </div>
    </div>
  )
}
