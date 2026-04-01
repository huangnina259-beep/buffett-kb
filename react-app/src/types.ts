export type HelpLevel = 'guided' | 'standard' | 'challenge';

export interface Step {
  id: number;
  label: string;
  question: string;
  whyItMatters: string;
  guidanceText: string;
  placeholder: string;
}
