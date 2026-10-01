"""Score agent output against whirlpool/cases. TODO(week 1): call sombrero /analyse per case."""
import json
from pathlib import Path

for path in sorted(Path(__file__).parent.glob("cases/*.json")):
    case = json.loads(path.read_text())
    print(f"{case['id']}: expected {case['expected']}")
