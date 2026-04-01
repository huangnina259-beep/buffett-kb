import { useState } from 'react'
import type { HelpLevel } from './types'
import { STEPS } from './data/steps'
import { STEP_1 } from './data/stepCardData'
import Header from './components/Header'
import ProgressBar from './components/ProgressBar'
import HelpLevelSelector from './components/HelpLevelSelector'
import StepCard from './components/StepCard'
import Sidebar from './components/Sidebar'
import styles from './App.module.css'

export default function App() {
  const [helpLevel, setHelpLevel] = useState<HelpLevel>('standard')
  const [currentStep, setCurrentStep] = useState(0)

  const totalSteps = STEPS.length
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
          {/* StepCard: hardcoded Step 1 while single-step scope is active */}
          <StepCard
            key={currentStep}
            step={STEP_1}
            stepIndex={currentStep}
            totalSteps={totalSteps}
            helpLevel={helpLevel}
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
