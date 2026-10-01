# Country pack schema

| Key | Type | Used by |
|---|---|---|
| `country`, `currency`, `languages`, `regulator` | strings | orchestrator, UI |
| `dispute_process[]` | steps with `deadline_days`, `form`, `form_fields` | filing, escalation |
| `rejection_codes` | map `"TPA:CODE"` or `"CODE"` -> `{meaning, category, source}`; IN uses the 44 NHCX adjudication reasons (`rejection_codes_source`) | code_decoder |
| `regulations[]` | outline tree: `{ref, text?, children?}` | policy_rules (tree search) |

Adding a country = adding one JSON file. No code changes.
