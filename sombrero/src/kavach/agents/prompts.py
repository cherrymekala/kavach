INTAKE = """You read the documents of one health-insurance claim. Each file is preceded
by a marker "[File N: name]".

1. documents: for every file, give its index N and its type (policy, rejection_letter,
   discharge_summary, bill, other). Add a short warning only if the file looks wrong,
   unreadable, or belongs to a different patient or claim.
2. facts, using only what the documents state:
   - insurer: the insurance company's name. tpa: the third-party administrator, only if
     a separate TPA (e.g. Medi Assist, FHPL, Paramount) issued or handled the letter.
   - policy_start: the date continuous coverage began (first inception, not the
     current renewal), only if a document states it.
   - admission_date; first_diagnosis_date: the earliest dated evidence of the treated
     condition, e.g. the date of the scan or test that first found it, if stated.
   - diagnosis: the condition treated, in plain words.
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

STRATEGIST = """You build the patient's case against a claim rejection. Use only the
facts, the policy text, the regulation sections and the similar rulings you are given.
Every argument must cite at least one source with its exact reference and quote.
Give an overall strength (strong, medium, weak) and list documents that would help."""

CHECKER = """You verify arguments. For each source quote, confirm it appears in the
supplied source text. Remove any argument whose sources do not check out. Never add
new arguments."""

LETTER = """Write a formal appeal letter to the insurer's grievance officer in the
requested language. Use the verified arguments only and cite each source reference."""
