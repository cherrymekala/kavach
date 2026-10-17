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
export type AskAnswer = components['schemas']['AskAnswer']
export type AskRequest = components['schemas']['AskRequest']
export type NoteRequest = components['schemas']['NoteRequest']
export type TitleRequest = components['schemas']['TitleRequest']
export type CaseKind = components['schemas']['CaseKind']
export type Risk = components['schemas']['Risk']
export type DischargeCheck = components['schemas']['DischargeCheck']
export type InsightRow = components['schemas']['InsightRow']
export type Insights = components['schemas']['Insights']

/** POST /cases/{id}/checkout (an untyped dict in the backend). */
export type Checkout =
  | { provider: 'razorpay'; key_id: string; order_id: string; amount: number; currency: string; name: string }
  | { provider: 'stripe'; url: string; amount: number; currency: string }
