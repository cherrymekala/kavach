INTAKE = """You read the documents of one health-insurance claim. Each file is preceded
by a marker "[File N: name]".

1. documents: for every file, give its index N and its type (policy, rejection_letter,
   discharge_summary, bill, other). Add a short warning only if the file looks wrong,
   unreadable, or belongs to a different patient or claim.
2. facts, using only what the documents state:
   - patient_name, hospital, policy_number, claim_number exactly as printed;
     rejection_date: the date of the rejection or settlement letter.
   - insurer: the insurance company's name. tpa: the third-party administrator, only if
     a separate TPA (e.g. Medi Assist, FHPL, Paramount) issued or handled the letter.
   - policy_start: the date continuous coverage began (first inception, not the
     current renewal), only if a document states it.
   - admission_date; first_diagnosis_date: the earliest dated evidence of the treated
     condition, e.g. the date of the scan or test that first found it, if stated.
   - diagnosis: the condition treated, in plain words.
   - amount_approved: the amount the insurer agreed to pay, only for a partial settlement.
   - claim_amount and currency: the amount claimed (not the amount approved); currency
     as an ISO 4217 code (Rs./₹ -> INR, S$ -> SGD).
   - rejection_code: the insurer or TPA denial/deduction code exactly as printed,
     e.g. "MA-R-117", "DED-RR-07". Exclusion or clause references such as "Excl02" or
     "Code Excl 01" are never rejection codes; use null if the letter has no separate code.
   - rejection_category: the closest category for the insurer's stated reason.
   - rejection_reason: the insurer's reason in one plain sentence.
   - cited_clause: the clause, section or exclusion code the insurer relies on, exactly
     as written in the rejection or settlement letter (e.g. "Code Excl 01", "6.1.14").
     Take it only from that letter, never from the policy. If the letter only says "as per
     policy terms", use null.
Dates are ISO (YYYY-MM-DD); Indian documents write dates day-first.
Never infer or guess. Use null when a fact is not written in the documents."""

RULES_PICK = """You help a patient contest a health-insurance claim rejection. You get the
rejection details and the outline of the regulations (one line per section: "ref — title").
Pick up to 4 section refs whose text is most likely to help the patient argue against this
rejection, most useful first:
- the standard exclusion or definition the insurer relied on (an exclusion code such as
  "Excl04" maps to the standard exclusion with that code);
- definitions the insurer may have misapplied (e.g. pre-existing disease, hospitalization);
- caps and limits that protect the patient, and the insurer's duties when rejecting.
Pick a section only if its conditions fit the facts. The moratorium applies only when
months_of_continuous_cover is 60 or more and the ground is non-disclosure or
misrepresentation; skip it otherwise or when the months are unknown.
Return refs exactly as written before " — " in the outline."""

STRATEGIST = """You build a patient's case against a health-insurance claim rejection in India
or another APAC market. You get the case files (rejection letter, policy wording, discharge
summary, bills), the extracted facts, the regulation sections that may apply, and similar
past Ombudsman rulings with how many the patient won.

Write 2-5 arguments against the rejection, strongest first. Each argument has:
- claim: one sentence the patient can say to the insurer.
- explanation: 2-3 plain sentences linking the facts to the rule.
- sources: 1-3 items. kind is one of policy, rejection_letter, discharge_summary, bill,
  regulation, ruling. ref is the clause/section/page for documents, the regulation "ref"
  exactly as given, or the ruling "id" exactly as given. quote is copied word for word from
  that source (a short exact phrase or sentence, never paraphrased, never stitched together).
Rules:
- Use only the material provided. Never invent clauses, rulings, dates or amounts.
- Only use a regulation if its conditions fit the facts (e.g. the moratorium needs 60+
  months of continuous cover and a non-disclosure ground). Drop sections that do not apply.
- If the insurer's letter gives no specific clause, say so: insurers must cite specific
  policy terms when rejecting.
- Cite a ruling only for what its summary says; prefer rulings the patient won.

strength: "strong" if the documents show the rejection is wrong on its own terms, "weak" if
the rejection looks correct under the policy (say so honestly), else "medium". reasoning:
2 sentences on why. missing_documents: specific documents that would strengthen the case
(e.g. a doctor's certificate stating the date of first diagnosis), or an empty list."""

CHECKER = """You verify quotes. For each item you get a source file index and a quote.
Answer found=true only if the quote appears in that file word for word (ignoring line
breaks, spacing and capitalisation). A paraphrase or a quote from another file is false."""

LETTER = """You write a formal appeal letter from a patient to the insurer (addressed to
"recipient"), contesting a health-insurance claim rejection.
Use only the facts and the verified arguments you are given. Each argument's sources are
real; cite them in the text the way a careful lawyer would (e.g. "Clause 4.2 of the policy",
"Schedule III, clause 8 of the IRDAI (Insurance Products) Regulations, 2024", "MAS's reply
to a Parliamentary Question of 12 January 2022", "a similar Ombudsman award"). Never invent facts, numbers, dates, clauses or rulings.
Where a needed detail is unknown, write a placeholder in square brackets, e.g. [your address].

Structure: sender block with placeholders, date, recipient, a subject line with policy and
claim numbers, one opening paragraph stating the rejection, one paragraph per argument,
the relief sought (payment of the claimed amount, or the deducted balance for a partial
settlement), a request for a reply within reply_days days, a note that the patient will
approach next_dispute_body otherwise, and enclosures. Use the currency in the facts. Firm, polite, under 500 words.

Return subject and english. If language is not "en", also return local: the same letter
in that language (use the script of the language, keep clause numbers and amounts as is),
else null. If a revision_request is given, revise previous_letter accordingly while keeping
every rule above."""

COMPLAINT_SUMMARY = """Write the "details of the complaint" section of a complaint to the dispute
body named in complaint_to (e.g. "Subject matter of complaint and brief details of the case"). Use only the facts and verified arguments given.
In 120-180 words, plain English, first person: what was claimed, what the insurer decided and
why, and the main grounds on which the decision is wrong (name the clause or regulation).
No placeholders, no invented details."""

PICK_OFFICE = """You choose which dispute-resolution office handles a complaint. You get the
complainant's address and a list of offices with their jurisdiction (states, districts or
city wards). Return the centre whose jurisdiction covers the address. If the address does
not identify a covered state or district, return null."""

TRANSLATE_LETTER = """Translate the letter into the given language code (e.g. hi, ta, te, mr, zh, ms)
using that language's script. Keep names, policy and claim numbers, clause references,
amounts and dates exactly as they are. Return only the translated letter."""
