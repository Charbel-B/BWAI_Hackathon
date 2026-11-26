"""Recouvrement : situation d'une facture par rapport à son échéance, et relance à envoyer.

Fonctions pures : la date du jour est passée en paramètre, jamais lue ici.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

from invoicing.domain.errors import InvariantViolationError


class Standing(StrEnum):
    """Situation d'une facture qui n'est pas soldée."""

    NOT_DUE = "NOT_DUE"
    DUE_SOON = "DUE_SOON"
    OVERDUE = "OVERDUE"
    NO_DUE_DATE = "NO_DUE_DATE"


@dataclass(frozen=True, slots=True)
class ReminderStep:
    """Étape de relance lue dans config/relances.yaml."""

    code: str
    label: str
    offset_days: int
    template: str


@dataclass(frozen=True, slots=True)
class CollectionRules:
    """Règles de relance ; les étapes sont dans l'ordre chronologique."""

    due_soon_days: int
    steps: tuple[ReminderStep, ...]

    def __post_init__(self) -> None:
        offsets = [s.offset_days for s in self.steps]
        if offsets != sorted(offsets) or len({s.code for s in self.steps}) != len(self.steps):
            raise InvariantViolationError("étapes de relance non ordonnées ou en double")


@dataclass(frozen=True, slots=True)
class Reminder:
    """Relance envoyée. Toujours simulée dans ce prototype."""

    id: str
    invoice_id: str
    step: str
    channel: str
    recipient: str
    message: str
    sent_at: datetime
    sent_by: str
    is_simulated: bool = True


def standing(due_date: date | None, today: date, rules: CollectionRules) -> Standing:
    """À échoir, bientôt due, en retard, ou sans échéance."""
    if due_date is None:
        return Standing.NO_DUE_DATE
    if today > due_date:
        return Standing.OVERDUE
    if (due_date - today).days <= rules.due_soon_days:
        return Standing.DUE_SOON
    return Standing.NOT_DUE


def days_late(due_date: date | None, today: date) -> int:
    """Jours de retard ; zéro si la facture n'est pas échue."""
    return max(0, (today - due_date).days) if due_date else 0


def next_step(
    due_date: date | None, today: date, rules: CollectionRules, sent: Sequence[str]
) -> ReminderStep | None:
    """La dernière étape atteinte et pas encore envoyée ; les étapes déjà dépassées sont sautées."""
    if due_date is None:
        return None
    reached = [s for s in rules.steps if today >= due_date + timedelta(days=s.offset_days)]
    if not reached or reached[-1].code in sent:
        return None
    return reached[-1]
