import type { HelpLevel } from '../types'
import styles from './Sidebar.module.css'

interface SidebarProps {
  helpLevel: HelpLevel
  progressPercent: number
}

const CONCEPTS = [
  'Moat',
  'Pricing power',
  'Asset-light model',
  'ROIC',
  'Durability',
  'Capital allocation',
  'Valuation',
] as const

const LEVEL_LABELS: Record<HelpLevel, string> = {
  guided: 'Guided',
  standard: 'Standard',
  challenge: 'Challenge',
}

export default function Sidebar({ helpLevel, progressPercent }: SidebarProps) {
  return (
    <div className={styles.sidebar}>

      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Case</h3>
        <div className={styles.row}>
          <span className={styles.rowLabel}>Company</span>
          <span className={styles.rowValue}>Coca-Cola</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>Industry</span>
          <span className={styles.rowValue}>Branded beverages</span>
        </div>
      </section>

      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Core Concepts</h3>
        <ul className={styles.conceptList}>
          {CONCEPTS.map(c => (
            <li key={c} className={styles.concept}>{c}</li>
          ))}
        </ul>
      </section>

      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Session</h3>
        <div className={styles.row}>
          <span className={styles.rowLabel}>Level</span>
          <span className={styles.rowValue}>{LEVEL_LABELS[helpLevel]}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>Progress</span>
          <span className={styles.rowValue}>{progressPercent}%</span>
        </div>
      </section>

    </div>
  )
}
