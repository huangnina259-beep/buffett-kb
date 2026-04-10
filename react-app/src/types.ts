/* ── Tutor training system types ──────────────────────────────── */

export interface Module {
  id: number
  title: string
  description: string
  cycles: CycleInfo[]
  frameworkItems: string[]
}

export interface CycleInfo {
  id: string
  title: string
  hint: string
}

export interface Message {
  id: string
  role: 'tutor' | 'student'
  content: string
  timestamp: number
}

export interface CurriculumState {
  currentModule: number
  currentCycle: string        // e.g. "1.1"
  completedCycles: string[]
  frameworkInsights: string[]
  parkingLot: string[]
}
