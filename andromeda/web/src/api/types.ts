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