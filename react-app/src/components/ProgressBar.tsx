import styles from './ProgressBar.module.css'

interface ProgressBarProps {
  current: number
  total: number
  percent: number
}

export default function ProgressBar({ current, total, percent }: ProgressBarProps) {
  return (
    <div className={styles.wrap}>
      <div className={styles.track} role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
        <div className={styles.fill} style={{ width: `${percent}%` }} />
      </div>
      <span className={styles.label}>
        {current} / {total}
      </span>
    </div>
  )
}
