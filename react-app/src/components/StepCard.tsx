import { useState, useEffect } from 'react'
import type { StepCardData, HelpLevel } from '../types'
import styles from './StepCard.module.css'

interface StepCardProps {
  step: StepCardData
  stepIndex: number
  totalSteps: number
  helpLevel: HelpLevel
  onContinue: () => void
}

export default function StepCard({
  step,
  stepIndex,
  totalSteps,
  helpLevel,
  onContinue,
}: StepCardProps) {
  const [radioValue, setRadioValue] = useState<string | null>(null)
  const [textValue, setTextValue] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [guidanceOpen, setGuidanceOpen] = useState(helpLevel === 'guided')

  // Sync guidance visibility when helpLevel changes mid-step
  useEffect(() => {
    setGuidanceOpen(helpLevel === 'guided')
  }, [helpLevel])

  const isRadio = step.answerType === 'radio'
  const isChallenge = helpLevel === 'challenge'
  const isLastStep = stepIndex === totalSteps - 1
  const canSubmit = isRadio ? radioValue !== null : textValue.trim().length > 0

  // For radio: derive correctness from selected option
  const isCorrect = isRadio && submitted && radioValue !== null
    ? radioValue === step.correctOptionId
    : null

  function handleSubmit() {
    if (!canSubmit) return
    setSubmitted(true)
  }

  return (
    <div className={styles.card}>

      {/* Step label */}
      <div className={styles.stepLabel}>
        Step {stepIndex + 1} / {totalSteps} — {step.label}
      </div>

      {/* Question */}
      <h2 className={styles.question}>{step.question}</h2>

      {/* Why this matters */}
      <div className={styles.why}>
        <span className={styles.whyLabel}>Why this matters</span>
        <p className={styles.whyText}>{step.whyItMatters}</p>
      </div>

      {/* Answer input */}
      {isRadio ? (
        <RadioInput
          options={step.options ?? []}
          value={radioValue}
          correctId={step.correctOptionId ?? null}
          submitted={submitted}
          onChange={setRadioValue}
        />
      ) : (
        <textarea
          className={styles.textarea}
          value={textValue}
          onChange={e => setTextValue(e.target.value)}
          placeholder={step.placeholder ?? 'Write your answer...'}
          disabled={submitted}
          rows={5}
          aria-label="Your answer"
        />
      )}

      {/* Submit button */}
      {!submitted && (
        <div className={styles.submitRow}>
          <button
            className={styles.submitBtn}
            onClick={handleSubmit}
            disabled={!canSubmit}
          >
            Submit
          </button>
        </div>
      )}

      {/* Feedback block */}
      {submitted && (
        <FeedbackBlock
          isCorrect={isCorrect}
          explanation={step.feedback.explanation}
        />
      )}

      {/* Guidance */}
      <GuidanceSection
        guidance={step.guidance}
        helpLevel={helpLevel}
        isChallenge={isChallenge}
        open={guidanceOpen}
        onToggle={() => setGuidanceOpen(o => !o)}
      />

      {/* Continue */}
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

// ── Sub-components ─────────────────────────────────────────────

interface RadioInputProps {
  options: { id: string; text: string }[]
  value: string | null
  correctId: string | null
  submitted: boolean
  onChange: (id: string) => void
}

function RadioInput({ options, value, correctId, submitted, onChange }: RadioInputProps) {
  return (
    <div className={styles.radioGroup} role="radiogroup">
      {options.map(opt => {
        const isSelected = value === opt.id
        const isCorrectOpt = opt.id === correctId
        let optState: 'default' | 'selected' | 'correct' | 'wrong' = 'default'
        if (submitted) {
          if (isCorrectOpt) optState = 'correct'
          else if (isSelected) optState = 'wrong'
        } else if (isSelected) {
          optState = 'selected'
        }

        return (
          <label
            key={opt.id}
            className={`${styles.radioLabel} ${styles[`radioLabel--${optState}`]}`}
          >
            <input
              type="radio"
              name="step-answer"
              value={opt.id}
              checked={isSelected}
              disabled={submitted}
              onChange={() => onChange(opt.id)}
              className={styles.radioInput}
            />
            <span className={styles.radioMark} aria-hidden="true" />
            <span className={styles.radioText}>{opt.text}</span>
          </label>
        )
      })}
    </div>
  )
}

interface FeedbackBlockProps {
  isCorrect: boolean | null
  explanation: string
}

function FeedbackBlock({ isCorrect, explanation }: FeedbackBlockProps) {
  const hasJudgment = isCorrect !== null

  return (
    <div className={styles.feedback}>
      {hasJudgment && (
        <div className={`${styles.feedbackVerdict} ${isCorrect ? styles.verdictCorrect : styles.verdictWrong}`}>
          {isCorrect ? 'Correct' : 'Not quite'}
        </div>
      )}
      <p className={styles.feedbackExplanation}>{explanation}</p>
    </div>
  )
}

interface GuidanceSectionProps {
  guidance: StepCardData['guidance']
  helpLevel: HelpLevel
  isChallenge: boolean
  open: boolean
  onToggle: () => void
}

function GuidanceSection({ guidance, isChallenge, open, onToggle }: GuidanceSectionProps) {
  const triggerLabel = isChallenge
    ? open ? 'Hide hint' : 'Need a hint?'
    : open ? '▾ Guidance' : '▸ Guidance'

  return (
    <div className={`${styles.guidanceWrap} ${isChallenge ? styles.guidanceChallenge : ''}`}>
      <button
        className={isChallenge ? styles.hintLink : styles.guidanceToggle}
        onClick={onToggle}
        aria-expanded={open}
      >
        {triggerLabel}
      </button>

      {open && (
        <dl className={styles.guidanceBody}>
          <GuidanceRow label="Where to find" text={guidance.whereToFind} />
          <GuidanceRow label="What to look for" text={guidance.whatToLookFor} />
          <GuidanceRow label="What to do" text={guidance.whatToDo} />
          <GuidanceRow label="Strong answer" text={guidance.strongAnswerExample} isExample />
          <GuidanceRow label="Common mistake" text={guidance.commonMistake} isWarning />
        </dl>
      )}
    </div>
  )
}

function GuidanceRow({
  label,
  text,
  isExample = false,
  isWarning = false,
}: {
  label: string
  text: string
  isExample?: boolean
  isWarning?: boolean
}) {
  return (
    <div className={`${styles.guidanceRow} ${isExample ? styles.guidanceRowExample : ''} ${isWarning ? styles.guidanceRowWarning : ''}`}>
      <dt className={styles.guidanceTerm}>{label}</dt>
      <dd className={styles.guidanceDef}>{text}</dd>
    </div>
  )
}
