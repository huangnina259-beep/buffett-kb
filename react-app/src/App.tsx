import { useState } from 'react'
import type { HelpLevel } from './types'
import { STEPS } from './data/steps'
import Header from './components/Header'
import ProgressBar from './components/ProgressBar'
import HelpLevelSelector from './components/HelpLevelSelector'
import MainCard from './components/MainCard'
import Sidebar from './components/Sidebar'
import styles from './App.module.css'

export default function App() {
  const [helpLevel, setHelpLevel] = useState<HelpLevel>('standard')
  const [currentStep, setCurrentStep] = useState(0)

  const totalSteps = STEPS.length
  const step = STEPS[currentStep]
  const progressPercent = Math.round((currentStep / totalSteps) * 100)

  function handleContinue() {
    if (currentStep < totalSteps - 1) {
      setCurrentStep(s => s + 1)
    }
  }

  return (
    <div className={styles.layout}>
      <Header caseTitle="Coca-Cola, 1988" />

      <div className={styles.controls}>
        <ProgressBar current={currentStep + 1} total={totalSteps} percent={progressPercent} />
        <HelpLevelSelector value={helpLevel} onChange={setHelpLevel} />
      </div>

      <div className={styles.body}>
        <main className={styles.main}>
          <MainCard
            key={currentStep}
            step={step}
            helpLevel={helpLevel}
            stepIndex={currentStep}
            totalSteps={totalSteps}
            onContinue={handleContinue}
          />
        </main>
        <aside className={styles.aside}>
          <Sidebar helpLevel={helpLevel} progressPercent={progressPercent} />
        </aside>
      </div>
    </div>
  )
}
