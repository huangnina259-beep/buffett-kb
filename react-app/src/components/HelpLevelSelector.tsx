import type { HelpLevel } from '../types'
import styles from './HelpLevelSelector.module.css'

interface HelpLevelSelectorProps {
  value: HelpLevel
  onChange: (level: HelpLevel) => void
}

const LEVELS: { value: HelpLevel; label: string; title: string }[] = [
  { value: 'guided',    label: 'Guided',    title: 'Guidance expanded by default' },
  { value: 'standard', label: 'Standard',  title: 'Guidance collapsed by default' },
  { value: 'challenge', label: 'Challenge', title: 'Guidance hidden behind a hint link' },
]

export default function HelpLevelSelector({ value, onChange }: HelpLevelSelectorProps) {
  return (
    <div className={styles.wrap}>
      <span className={styles.prefix}>Mode</span>
      <div className={styles.buttons} role="group" aria-label="Help level">
        {LEVELS.map(level => (
          <button
            key={level.value}
            className={`${styles.btn} ${value === level.value ? styles.active : ''}`}
            onClick={() => onChange(level.value)}
            title={level.title}
            aria-pressed={value === level.value}
          >
            {level.label}
          </button>
        ))}
      </div>
    </div>
  )
}
