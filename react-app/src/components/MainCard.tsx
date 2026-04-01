import { useState, useEffect } from 'react'
import type { Step, HelpLevel } from '../types'
import styles from './MainCard.module.css'

interface MainCardProps {
  step: Step
  helpLevel: HelpLevel
  stepIndex: number
  totalSteps: number
  onContinue: () => void
}

export default function MainCard({ step, helpLevel, stepIndex, totalSteps, onContinue }: MainCardProps) {
  const [answer, setAnswer] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [guidanceOpen, setGuidanceOpen] = useState(helpLevel === 'guided')

  // Sync guidance visibility when helpLevel changes mid-step
  useEffect(() => {
    setGuidanceOpen(helpLevel === 'guided')
  }, [helpLevel])

  const isChallenge = helpLevel === 'challenge'
  const isLastStep = stepIndex === totalSteps - 1

  function handleSubmit() {
    if (answer.trim().length === 0) return
    setSubmitted(true)
    // Scoring / feedback logic goes here in future passes
  }

  return (
    <div className={styles.card}>

      {/* 1. Step label */}
      <div className={styles.stepLabel}>
        Step {stepIndex + 1} of {totalSteps} — {step.label}
      </div>

      {/* 2. Question */}
      <h2 className={styles.question}>{step.question}</h2>

      {/* 3. Why this matters */}
      <div className={styles.why}>
        <span className={styles.whyLabel}>Why this matters</span>
        <p className={styles.whyText}>{step.whyItMatters}</p>
      </div>

      {/* 4. Answer input */}
      <textarea
        className={styles.textarea}
        value={answer}
        onChange={e => setAnswer(e.target.value)}
        placeholder={step.placeholder}
        disabled={submitted}
        rows={5}
        aria-label="Your answer"
      />

      {/* 5. Submit */}
      {!submitted && (
        <div className={styles.submitRow}>
          <button
            className={styles.submitBtn}
            onClick={handleSubmit}
            disabled={answer.trim().length === 0}
          >
            Submit →
          </button>
        </div>
      )}

      {/* 6. Feedback block — placeholder until scoring is implemented */}
      {submitted && (
        <div className={styles.feedback}>
          <p className={styles.feedbackPlaceholder}>
            Feedback and analysis will appear here once scoring is implemented.
          </p>
        </div>
      )}

      {/* 7. Guidance area */}
      {!isChallenge && (
        <div className={styles.guidanceWrap}>
          <button
            className={styles.guidanceToggle}
            onClick={() => setGuidanceOpen(o => !o)}
            aria-expanded={guidanceOpen}
          >
            {guidanceOpen ? '▾ Guidance' : '▸ Guidance'}
          </button>
          {guidanceOpen && (
            <p className={styles.guidanceText}>{step.guidanceText}</p>
          )}
        </div>
      )}

      {/* Challenge mode: subtle hint link */}
      {isChallenge && (
        <div className={styles.hintWrap}>
          <button
            className={styles.hintLink}
            onClick={() => setGuidanceOpen(o => !o)}
          >
            {guidanceOpen ? 'Hide hint' : 'Need a hint?'}
          </button>
          {guidanceOpen && (
            <p className={styles.guidanceText}>{step.guidanceText}</p>
          )}
        </div>
      )}

      {/* 8. Continue button — shown after submission */}
      {submitted && (
        <div className={styles.continueRow}>
          <button className={styles.continueBtn} onClick={onContinue}>
            {isLastStep ? 'Finish' : 'Continue →'}
          </button>
        </div>
      )}

    </div>
  )
}
