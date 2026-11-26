from datetime import date

import pytest

from invoicing.domain.collection import (
    CollectionRules,
    ReminderStep,
    Standing,
    days_late,
    next_step,
    standing,
)
from invoicing.domain.errors import InvariantViolationError

RULES = CollectionRules(
    3,
    (
        ReminderStep("rappel", "Rappel", -3, "t"),
        ReminderStep("relance", "Relance", 1, "t"),
        ReminderStep("dernier-rappel", "Dernier", 7, "t"),
    ),
)
DUE = date(2026, 12, 20)


def test_standing_follows_the_calendar() -> None:
    assert standing(DUE, date(2026, 12, 1), RULES) is Standing.NOT_DUE
    assert standing(DUE, date(2026, 12, 17), RULES) is Standing.DUE_SOON
    assert standing(DUE, date(2026, 12, 21), RULES) is Standing.OVERDUE
    assert standing(None, DUE, RULES) is Standing.NO_DUE_DATE


def test_days_late_is_never_negative() -> None:
    assert days_late(DUE, date(2026, 12, 25)) == 5
    assert days_late(DUE, date(2026, 12, 1)) == 0
    assert days_late(None, DUE) == 0


def test_next_step_is_the_latest_reached_and_not_yet_sent() -> None:
    assert next_step(DUE, date(2026, 12, 10), RULES, []) is None
    assert next_step(DUE, date(2026, 12, 17), RULES, [])
    step = next_step(DUE, date(2026, 12, 30), RULES, ["rappel"])
    assert step is not None and step.code == "dernier-rappel"
    assert next_step(DUE, date(2026, 12, 30), RULES, ["dernier-rappel"]) is None
    assert next_step(None, DUE, RULES, []) is None


def test_steps_must_be_ordered_and_unique() -> None:
    with pytest.raises(InvariantViolationError):
        CollectionRules(3, (ReminderStep("a", "A", 5, "t"), ReminderStep("b", "B", 1, "t")))
