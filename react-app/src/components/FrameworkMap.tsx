import type { Module, CurriculumState } from '../types'
import styles from './FrameworkMap.module.css'

interface Props {
  modules: Module[]
  state: CurriculumState
}

export default function FrameworkMap({ modules, state }: Props) {
  return (
    <div className={styles.framework}>
      <h3 className={styles.title}>你的分析框架</h3>
      <p className={styles.subtitle}>每完成一步，框架填一块</p>

      <div className={styles.sections}>
        {modules.map(mod => {
          const isCompleted = mod.cycles.every(c => state.completedCycles.includes(c.id))
          const isCurrent = mod.id === state.currentModule
          const isFuture = mod.id > state.currentModule

          return (
            <div key={mod.id} className={`${styles.section} ${isFuture ? styles.future : ''}`}>
              <div className={styles.sectionHeader}>
                <span className={isCompleted ? styles.filled : styles.empty}>
                  {isCompleted ? '■' : '□'}
                </span>
                <span className={styles.sectionTitle}>{mod.title}</span>
                {isCurrent && <span className={styles.currentBadge}>当前</span>}
              </div>

              <div className={styles.items}>
                {mod.frameworkItems.map((item, i) => {
                  const unlocked = state.frameworkInsights.includes(item)
                  return (
                    <div
                      key={i}
                      className={`${styles.item} ${unlocked ? styles.unlocked : ''}`}
                    >
                      <span className={styles.itemIcon}>
                        {unlocked ? '✓' : '·'}
                      </span>
                      <span>{item}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      {/* parking lot */}
      {state.parkingLot.length > 0 && (
        <div className={styles.parkingLot}>
          <div className={styles.parkingTitle}>📌 待探讨</div>
          {state.parkingLot.map((q, i) => (
            <div key={i} className={styles.parkingItem}>{q}</div>
          ))}
        </div>
      )}
    </div>
  )
}
