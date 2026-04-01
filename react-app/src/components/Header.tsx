import styles from './Header.module.css'

interface HeaderProps {
  caseTitle: string
}

export default function Header({ caseTitle }: HeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <span className={styles.brandCn}>复利国</span>
        <span className={styles.brandEn}>The Compounder</span>
      </div>
      <span className={styles.caseTitle}>{caseTitle}</span>
    </header>
  )
}
