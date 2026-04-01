import type { StepCardData } from '../types'

export const STEP_1: StepCardData = {
  id: 1,
  label: 'Business Type',
  question: "How would you describe Coca-Cola's core business model?",
  whyItMatters:
    'The structure of a business determines its economics. Getting this right first prevents you from applying the wrong analytical lens for everything that follows.',
  answerType: 'radio',
  options: [
    {
      id: 'A',
      text: 'Coke manufactures beverages in its own factories and sells them directly to retailers worldwide.',
    },
    {
      id: 'B',
      text: 'Coke owns the brand, formulas, and concentrate. Licensed bottlers handle manufacturing, packaging, and local distribution.',
    },
    {
      id: 'C',
      text: 'Coke is primarily a distribution network that happens to own some beverage brands.',
    },
    {
      id: 'D',
      text: 'Coke is a diversified consumer goods conglomerate across food, beverages, and retail.',
    },
  ],
  correctOptionId: 'B',
  feedback: {
    correct: null,
    explanation:
      'Coca-Cola is an asset-light brand and concentrate business. It sells syrup and concentrate to independent bottlers who bear the capital cost of manufacturing and distribution. This split is why Coke earns extraordinary margins on invested capital while its balance sheet stays lean.',
  },
  guidance: {
    whereToFind:
      `Coca-Cola's 10-K, specifically the "Business" section and the segment breakdown. Also the 1988-1989 annual letters where Buffett first articulates why the business model matters.`,
    whatToLookFor:
      'The concentrate/syrup vs. bottling distinction. Note that Coke consolidates some bottlers for accounting purposes -- look past that to the underlying economics of the core brand business.',
    whatToDo:
      'Identify which parts of the value chain Coke owns vs. outsources. Map fixed costs to each layer. Determine where the margin is generated and why.',
    strongAnswerExample:
      `"Coke's core model is owning the brand and formula, manufacturing concentrate at very low cost, and selling it to bottlers at high margin. Bottlers own the capital-heavy distribution infrastructure. This means Coke grows revenue without growing its asset base at the same rate."`,
    commonMistake:
      "Treating Coke as a manufacturer. It isn't -- or at least, that's not where the value sits. Analysts who model it like a beverage factory systematically underestimate its return on capital.",
  },
}
