"""Escalation tracker: move cases to the next step when a deadline passes."""
from datetime import UTC, datetime

from ..tools import store


def advance_overdue_cases() -> int:
    now = datetime.now(UTC)
    moved = 0
    for case in store.cases_due(now):
        case.escalation_step += 1
        case.next_deadline = None  # TODO(week 2): set from the pack's step deadline
        store.save_case(case)
        moved += 1
    return moved
