"""Avoirs, règlements et émissions, et le statut de paiement qui en est dérivé."""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from invoicing.domain.errors import BusinessRuleError, InvalidTransitionError
from invoicing.domain.invoice import ZERO, Invoice, InvoiceLine, Totals
from invoicing.domain.lifecycle import DISPATCHABLE, ensure_status


class PaymentStatus(StrEnum):
    """Statut de paiement. Jamais stocké : calculé à chaque lecture à partir du solde."""

    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"


class CreditNoteStatus(StrEnum):
    """Cycle de vie d'un avoir."""

    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"


@dataclass(frozen=True, slots=True)
class CreditNote:
    """Avoir : annule tout ou partie d'une facture validée, qui elle ne change jamais."""

    id: str
    invoice_id: str
    status: CreditNoteStatus
    reason: str
    lines: tuple[InvoiceLine, ...]
    totals: Totals
    version: int
    created_by: str
    created_at: datetime
    number: str | None = None
    validated_by: str | None = None
    validated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Payment:
    """Règlement. Toujours simulé dans ce prototype, et affiché comme tel."""

    id: str
    invoice_id: str
    amount: Decimal
    method: str
    reference: str
    received_at: datetime
    recorded_by: str
    is_simulated: bool = True


@dataclass(frozen=True, slots=True)
class Dispatch:
    """Émission d'une facture sur un canal. Toujours simulée dans ce prototype."""

    id: str
    invoice_id: str
    channel: str
    recipient: str
    message: str
    sent_at: datetime
    sent_by: str
    is_simulated: bool = True


@dataclass(frozen=True, slots=True)
class Balance:
    """Solde dérivé d'une facture."""

    gross_total: Decimal
    credited_total: Decimal
    paid_total: Decimal

    @property
    def amount_due(self) -> Decimal:
        """Montant net des avoirs, encore à régler."""
        return self.gross_total - self.credited_total - self.paid_total

    @property
    def status(self) -> PaymentStatus:
        """Statut de paiement selon docs/contrats/cycle-de-vie.md."""
        if self.amount_due <= ZERO:
            return PaymentStatus.PAID
        if self.paid_total > ZERO:
            return PaymentStatus.PARTIALLY_PAID
        return PaymentStatus.UNPAID


def compute_balance(
    invoice: Invoice, credit_notes: Iterable[CreditNote], payments: Iterable[Payment]
) -> Balance:
    """Solde = TTC - avoirs validés - règlements."""
    credited = sum(
        (c.totals.gross_total for c in credit_notes if c.status is CreditNoteStatus.VALIDATED),
        ZERO,
    )
    paid = sum((p.amount for p in payments), ZERO)
    return Balance(invoice.totals.gross_total, credited, paid)


def check_payment(invoice: Invoice, amount: Decimal, balance: Balance) -> None:
    """Un règlement porte sur une facture validée et ne dépasse pas le solde."""
    ensure_status(invoice, DISPATCHABLE, "Règlement")
    if amount <= ZERO:
        raise BusinessRuleError("le montant d'un règlement doit être positif")
    if amount > balance.amount_due:
        raise BusinessRuleError(f"montant {amount} supérieur au solde {balance.amount_due}")


def check_credit(
    invoice: Invoice, credit_gross: Decimal, credit_notes: Iterable[CreditNote]
) -> None:
    """Un avoir ne crédite pas plus que ce qui reste à créditer."""
    ensure_status(invoice, DISPATCHABLE, "Avoir")
    already = sum((c.totals.gross_total for c in credit_notes), ZERO)
    if credit_gross <= ZERO:
        raise BusinessRuleError("un avoir doit porter un montant positif")
    if already + credit_gross > invoice.totals.gross_total:
        remaining = invoice.totals.gross_total - already
        raise BusinessRuleError(f"avoir supérieur au montant restant à créditer ({remaining})")


def validate_credit_note(
    credit_note: CreditNote, *, by: str, at: datetime, number: str
) -> CreditNote:
    """Valide un avoir en brouillon ; le numéro est attribué dans la même transaction."""
    if credit_note.status is not CreditNoteStatus.DRAFT:
        raise InvalidTransitionError("seul un avoir en brouillon peut être validé")
    return replace(
        credit_note,
        status=CreditNoteStatus.VALIDATED,
        number=number,
        validated_by=by,
        validated_at=at,
        version=credit_note.version + 1,
    )


def is_fully_credited(invoice: Invoice, credit_notes: Iterable[CreditNote]) -> bool:
    """Vrai si les avoirs validés couvrent tout le TTC : la facture passe à CANCELLED."""
    validated = (c for c in credit_notes if c.status is CreditNoteStatus.VALIDATED)
    return sum((c.totals.gross_total for c in validated), ZERO) >= invoice.totals.gross_total
