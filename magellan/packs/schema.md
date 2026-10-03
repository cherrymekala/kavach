# Country pack schema

| Key | Type | Used by |
|---|---|---|
| `country`, `currency`, `languages`, `regulator` | strings | orchestrator, UI |
| `dispute_process[]` | steps with `dispute_body`, `deadline_days`, `form`, `form_fields[]` = `{label, source}`; source is `facts.<field>`, `complainant.<field>`, `generated.summary`, `computed.loss/relief/enclosures` or `const:<text>` | filing, escalation |
| `rejection_codes` | map `"TPA:CODE"` or `"CODE"` -> `{meaning, category, source}`; IN uses the 44 NHCX adjudication reasons (`rejection_codes_source`) | code_decoder |
| `limitation` | `{days, body, from}`: time limit for the final dispute body (IN 365 days to the Ombudsman, SG 183 days to FIDReC) | escalation |
| `ombudsman_offices` | (IN) offices with jurisdiction; a step's `offices` key points here | filing |
| `regulations[]` | outline tree: `{ref, text?, children?}` | policy_rules (tree search) |

Adding a country = adding one JSON file. No code changes.

## Tree search
`regulations[]` is a tree. `policy_rules.find_sections` shows Gemini only `ref — title` lines, gets up to 4 refs back and returns those leaves verbatim. IN is built by `ingest/build_in_regulations.py` from the IRDAI Products Regulations 2024 (Sch. III), the Health Master Circular 2024 (Ch. I + claims handling) and the Standardization Master Circular 2020 (46 standard definitions, banned exclusions, standard exclusions Excl01–Excl18): 103 sections.
