export type HelpLevel = 'guided' | 'standard' | 'challenge';

// Original skeleton Step type — used by existing STEPS data
export interface Step {
  id: number;
  label: string;
  question: string;
  whyItMatters: string;
  guidanceText: string;
  placeholder: string;
}

// ── StepCard types ──────────────────────────────────────────────

export type AnswerType = 'radio' | 'textarea';

export interface RadioOption {
  id: string;
  text: string;
}

export interface Guidance {
  whereToFind: string;
  whatToLookFor: string;
  whatToDo: string;
  strongAnswerExample: string;
  commonMistake: string;
}

/**
 * correct === true | false  →  radio: judgment shown after submit
 * correct === null          →  textarea: open-ended, no judgment
 */
export interface Feedback {
  correct: boolean | null;
  explanation: string;
}

export interface StepCardData {
  id: number;
  label: string;
  question: string;
  whyItMatters: string;
  answerType: AnswerType;
  options?: RadioOption[];      // radio only
  correctOptionId?: string;     // radio only
  placeholder?: string;         // textarea only
  feedback: Feedback;
  guidance: Guidance;
}
