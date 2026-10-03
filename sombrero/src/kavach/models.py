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
    kind: str  # policy | rejection_letter | discharge_summary | bill | regulation | ruling
    ref: str  # e.g. "Clause 4.2, p.11", a regulation ref, or a ruling id
    quote: str  # verbatim from the source
    verified: bool = False


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
    SUB_LIMIT = "sub_limit"  # coverage cap, co-pay, deductible
    UNDER_24_HOURS = "under_24_hours"
    HOSPITAL_INELIGIBLE = "hospital_ineligible"
    DUPLICATE_CLAIM = "duplicate_claim"
    FRAUD = "fraud"
    OTHER = "other"


class CaseFacts(BaseModel):
    insurer: str | None = None
    tpa: str | None = None
    patient_name: str | None = None
    hospital: str | None = None
    policy_number: str | None = None
    claim_number: str | None = None
    rejection_date: date | None = None
    policy_start: date | None = None
    admission_date: date | None = None
    first_diagnosis_date: date | None = None
    diagnosis: str | None = None
    claim_amount: float | None = None
    amount_approved: float | None = None  # partial settlements; None if fully rejected
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


DISCLAIMER = (
    "Kavach prepares documents from your files and public rules to help you raise a dispute. "
    "It is not legal advice. Check every detail before you sign or send anything."
)


class Assessment(BaseModel):
    strength: str  # strong | medium | weak
    score: float = Field(ge=0, le=1)
    arguments: list[Argument] = []
    similar_cases_won: int = 0
    similar_cases_total: int = 0
    missing_documents: list[str] = []
    disclaimer: str = DISCLAIMER


class Letter(BaseModel):
    subject: str
    english: str
    local: str | None = None  # same letter in Case.language when that is not English
    language: str = "en"


class Complainant(BaseModel):
    """What only the patient knows; the filing pack leaves blanks for anything missing."""

    name: str | None = None
    address: str | None = None
    mobile: str | None = None
    email: str | None = None
    relationship_to_insured: str | None = None
    insurer_office_address: str | None = None
    grievance_date: date | None = None  # when the patient complained to the insurer
    grievance_reply_date: date | None = None
    grievance_outcome: str | None = None
    court_proceedings: str | None = None
    ported: bool | None = None


class FilingPack(BaseModel):
    form: str
    dispute_body: str
    fields: list[dict]  # [{"label", "value"}] in form order; value "" means fill in by hand
    missing: list[str]  # labels the patient still has to fill


class CaseEvent(BaseModel):
    at: datetime
    kind: str  # filed | reply | escalated | reminder | resolved | warning
    text: str  # shown on the tracker screen and used for notifications
    step: int | None = None


class FiledRequest(BaseModel):
    filed_on: date
    step: int | None = None  # defaults to the case's current step


class ReplyRequest(BaseModel):
    outcome: str  # paid | partly_paid | rejected
    replied_on: date
    amount_paid: float | None = None


class Case(BaseModel):
    id: str
    owner: str
    country: str = "IN"
    language: str = "en"
    status: CaseStatus = CaseStatus.COLLECTING
    documents: list[Document] = []
    facts: CaseFacts | None = None
    assessment: Assessment | None = None
    letter: Letter | None = None
    complainant: Complainant | None = None
    next_deadline: datetime | None = None
    escalation_step: int = 0
    events: list[CaseEvent] = []
    amount_recovered: float | None = None
    progress: str | None = None  # shown live in the UI, e.g. "Checking sources"


class CreateCase(BaseModel):
    country: str = "IN"
    language: str = "en"
