"""Copy insurer grievance contacts into the country packs (`insurer_contacts`).

Source: magellan/data/insurer_contacts.json, one record per insurer with the official
page each email was read from (IN: IRDAI's list of Grievance Redressal Officers; SG: CPF
Board's Integrated Shield insurer list; MY: Bank Negara Malaysia's insurer directory).
Kavach suggests these addresses when it emails an appeal; the patient can change them.

    python magellan/ingest/build_insurer_contacts.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

contacts = json.loads((ROOT / "data" / "insurer_contacts.json").read_text(encoding="utf-8"))
for country, rows in contacts.items():
    path = ROOT / "packs" / f"{country}.json"
    pack = json.loads(path.read_text(encoding="utf-8"))
    pack["insurer_contacts"] = rows
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{country}: {len(rows)} insurer contacts")
