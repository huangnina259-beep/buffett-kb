import type { Module, CurriculumState } from '../types'
import styles from './LearningMap.module.css'

interface Props {
  modules: Module[]
  state: CurriculumState
  progressPercent: number
}

export default function LearningMap({ modules, state, progressPercent }: Props) {
  const currentModuleId = state.currentModule

  return (
    <div className={styles.map}>
      <h3 className={styles.title}>学习地图</h3>

      <div className={styles.progressBar}>
        <div className={styles.progressFill} style={{ width: `${progressPercent}%` }} />
      </div>
      <div className={styles.progressLabel}>{progressPercent}% 完成</div>

      <div className={styles.modules}>
        {modules.map(mod => {
          const isCompleted = mod.cycles.every(c => state.completedCycles.includes(c.id))
          const isCurrent = mod.id === currentModuleId
          const isFuture = mod.id > currentModuleId

          return (
            <div key={mod.id} className={styles.module}>
              {/* module header */}
              <div className={`${styles.moduleHeader} ${isCurrent ? styles.active : ''} ${isCompleted ? styles.completed : ''} ${isFuture ? styles.future : ''}`}>
                <span className={styles.dot}>
                  {isCompleted ? '✓' : isCurrent ? '●' : '○'}
                </span>
                <div>
                  <div className={styles.moduleTitle}>{mod.title}</div>
                  <div className={styles.moduleDesc}>{mod.description}</div>
                </div>
              </div>

              {/* cycle list — only show for current module */}
              {isCurrent && (
                <div className={styles.cycles}>
                  {mod.cycles.map(cycle => {
                    const cycleCompleted = state.completedCycles.includes(cycle.id)
                    const cycleCurrent = cycle.id === state.currentCycle
                    return (
                      <div
                        key={cycle.id}
                        className={`${styles.cycle} ${cycleCurrent ? styles.cycleCurrent : ''} ${cycleCompleted ? styles.cycleCompleted : ''}`}
                      >
                        <span className={styles.cycleDot}>
                          {cycleCompleted ? '✓' : cycleCurrent ? '▸' : '·'}
                        </span>
                        {cycle.title}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* destination */}
      <div className={styles.destination}>
        <div className={styles.destIcon}>🏁</div>
        <div className={styles.destText}>拿到你的分析框架</div>
      </div>
    </div>
  )
}
