import type { components } from './schema'

// Convenient aliases for the generated OpenAPI types.
export type Case = components['schemas']['Case']
export type CaseFacts = components['schemas']['CaseFacts']
export type CaseStatus = components['schemas']['CaseStatus']
export type CaseEvent = components['schemas']['CaseEvent']
export type Document = components['schemas']['Document']
export type DocType = components['schemas']['DocType']
export type Assessment = components['schemas']['Assessment']
export type Argument = components['schemas']['Argument']
export type Source = components['schemas']['Source']
export type Letter = components['schemas']['Letter']
export type Complainant = components['schemas']['Complainant']
export type FilingPack = components['schemas']['FilingPack']
export type CreateCase = components['schemas']['CreateCase']
export type FiledRequest = components['schemas']['FiledRequest']
export type ReplyRequest = components['schemas']['ReplyRequest']
export type LetterRequest = components['schemas']['LetterRequest']
export type RejectionCategory = components['schemas']['RejectionCategory']
export type CaseSummary = components['schemas']['CaseSummary']
export type PackInfo = components['schemas']['PackInfo']
export type LadderStep = components['schemas']['LadderStep']

// Endpoints added after the last openapi-typescript run — regenerate schema.d.ts
// from /openapi.json once the backend with `title` / `ask` / `notes` deploys.
export interface AskAnswer {
  answer: string
}

export interface AskRequest {
  question: string
}

export interface NoteRequest {
  text: string
}

export interface TitleRequest {
  title: string
}

/** A case (or summary) carrying the new `title` field. */
export interface WithTitle {
  title: string | null
}
// GET /insights/{country} — regenerate schema.d.ts after the backend deploys.
export interface InsightRow {
  key: string
  total: number
  allowed: number
  partly_allowed: number
  dismissed: number
  won_pct: number
}

export interface Insights {
  country: string
  source: string
  period: { from: string; to: string }
  overall: InsightRow
  by_category: InsightRow[]
  by_insurer: InsightRow[]
  by_year: InsightRow[]
  note: string
}

// Pre-discharge check (Case.kind / Case.discharge_check) — regenerate schema.d.ts after deploy.
export type CaseKind = 'dispute' | 'pre_discharge'

export interface Risk {
  title: string
  severity: 'high' | 'medium' | 'low' | string
  why: string
  fix: string
  sources: { kind: string; ref: string; quote: string; verified?: boolean }[]
}

export interface DischargeCheck {
  verdict: 'clear' | 'some_risks' | 'high_risk' | string
  summary: string
  risks: Risk[]
  disclaimer: string
}

/** A case carrying the pre-discharge fields. */
export interface WithDischarge {
  kind?: CaseKind
  discharge_check?: DischargeCheck | null
}
