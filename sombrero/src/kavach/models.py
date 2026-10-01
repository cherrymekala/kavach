"""API contract shared with andromeda. Change it here first, then tell the frontend."""
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DocType(StrEnum):
    POLICY = "policy"
    REJECTION_LETTER = "rejection_letter"
    DISCHARGE_SUMMARY = "discharge_summary"
    BILL = "bill"
    OTHER = "other"


class CaseStatus(StrEnum):
    COLLECTING = "collecting"
    ANALYSING = "analysing"
    READY = "ready"
    FILED = "filed"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class Document(BaseModel):
    id: str
    filename: str
    gcs_uri: str
    doc_type: DocType = DocType.OTHER
    pages: int | None = None
    warning: str | None = None


class Source(BaseModel):
    kind: str  # policy | discharge_summary | regulation | ruling
    ref: str  # e.g. "Clause 4.2, p.11"
    quote: str


class Argument(BaseModel):
    claim: str
    explanation: str
    sources: list[Source]


class RejectionCategory(StrEnum):
    PRE_EXISTING = "pre_existing"
    SPECIFIC_WAITING_PERIOD = "specific_waiting_period"
    INITIAL_WAITING_PERIOD = "initial_waiting_period"
    NON_DISCLOSURE = "non_disclosure"
    ROOM_RENT = "room_rent"
    REASONABLE_CHARGES = "reasonable_charges"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    NOT_MEDICALLY_NECESSARY = "not_medically_necessary"
    EXCLUDED_TREATMENT = "excluded_treatment"
    MISSING_DOCUMENTS = "missing_documents"
    LATE_INTIMATION = "late_intimation"
    OTHER = "other"


class CaseFacts(BaseModel):
    insurer: str | None = None
    tpa: str | None = None
    policy_start: date | None = None
    admission_date: date | None = None
    first_diagnosis_date: date | None = None
    diagnosis: str | None = None
    claim_amount: float | None = None
    currency: str | None = None
    rejection_code: str | None = None
    rejection_category: RejectionCategory | None = None
    rejection_reason: str | None = None
    cited_clause: str | None = None


class DocLabel(BaseModel):
    index: int  # position of the file in the request
    doc_type: DocType
    warning: str | None = None


class IntakeResult(BaseModel):
    documents: list[DocLabel]
    facts: CaseFacts


class Assessment(BaseModel):
    strength: str  # strong | medium | weak
    score: float = Field(ge=0, le=1)
    arguments: list[Argument] = []
    similar_cases_won: int = 0
    similar_cases_total: int = 0
    missing_documents: list[str] = []


class Case(BaseModel):
    id: str
    owner: str
    country: str = "IN"
    language: str = "en"
    status: CaseStatus = CaseStatus.COLLECTING
    documents: list[Document] = []
    facts: CaseFacts | None = None
    assessment: Assessment | None = None
    letter: str | None = None
    next_deadline: datetime | None = None
    escalation_step: int = 0
    progress: str | None = None  # shown live in the UI, e.g. "Checking sources"


class CreateCase(BaseModel):
    country: str = "IN"
    language: str = "en"
