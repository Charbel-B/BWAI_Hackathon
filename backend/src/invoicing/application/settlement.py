"""Cas d'usage après validation : émission, règlements et avoirs, tous simulés côté extérieur."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from invoicing.application.context import Context, NotFoundError, new_id, operation
from invoicing.application.invoices import ENTITY, load, view
from invoicing.domain import lifecycle
from invoicing.domain.calculation import compute_invoice
from invoicing.domain.errors import BusinessRuleError, VersionConflictError
from invoicing.domain.invoice import Invoice, InvoiceLine, LineInput, Totals
from invoicing.domain.settlement import (
    CreditNote,
    CreditNoteStatus,
    Dispatch,
    Payment,
    check_credit,
    check_payment,
    is_fully_credited,
    validate_credit_note,
)
from invoicing.domain.users import User


def dispatch(ctx: Context, user: User, invoice_id: str, channel: str) -> Dispatch:
    """Émet la facture sur un canal simulé. Une seule émission réussie par canal."""
    if channel not in ctx.active_channels:
        raise BusinessRuleError(f"canal inactif : {channel}")
    with operation(ctx, user) as op:
        tx = op.tx
        invoice = load(tx, invoice_id)
        lifecycle.ensure_status(invoice, lifecycle.DISPATCHABLE, "Émission")
        if any(d.channel == channel for d in tx.dispatches_for(invoice.id)):
            raise BusinessRuleError(f"facture déjà émise par {channel}")
        sent = ctx.channel.send(
            invoice, ctx.referentials.customer(invoice.content.customer_id), channel
        )
        record = Dispatch(
            new_id("DSP"), invoice.id, channel, sent.recipient, sent.message, ctx.now(), user.id
        )
        tx.add_dispatch(record)
        issued = lifecycle.mark_issued(invoice)
        tx.save_invoice(issued)
        op.audit(
            "invoice.dispatched",
            (ENTITY, invoice.id),
            {"status": invoice.status},
            {"status": issued.status, "channel": channel},
        )
    return record


@dataclass(frozen=True, slots=True)
class RecordPayment:
    """Demande d'enregistrement d'un règlement."""

    invoice_id: str
    amount: Decimal
    method: str
    reference: str | None = None


def record_payment(ctx: Context, user: User, command: RecordPayment) -> Payment:
    """Enregistre un règlement simulé, au plus égal au solde."""
    invoice_id, amount, method, reference = (
        command.invoice_id,
        command.amount,
        command.method,
        command.reference,
    )
    with operation(ctx, user) as op:
        tx = op.tx
        invoice = load(tx, invoice_id)
        check_payment(invoice, amount, view(tx, invoice).balance)
        payment = Payment(
            id=new_id("PAY"),
            invoice_id=invoice.id,
            amount=amount,
            method=method,
            reference=reference or f"SIMULE-{new_id('MM')[3:]}".upper(),
            received_at=ctx.now(),
            recorded_by=user.id,
        )
        tx.add_payment(payment)
        op.audit(
            "payment.recorded",
            (ENTITY, invoice.id),
            after={"amount": str(amount), "method": method, "reference": payment.reference},
        )
    return payment


def create_credit_note(
    ctx: Context,
    user: User,
    invoice_id: str,
    reason: str,
    quantities: Sequence[tuple[int, Decimal]] | None,
) -> CreditNote:
    """Crée un avoir en brouillon : total si `quantities` est None, sinon ligne par ligne."""
    if not reason.strip():
        raise BusinessRuleError("un avoir exige un motif")
    with operation(ctx, user) as op:
        tx = op.tx
        invoice = load(tx, invoice_id)
        lines, totals = _credit_lines(ctx, invoice, quantities)
        check_credit(invoice, totals.gross_total, tx.credit_notes_for(invoice.id))
        credit_note = CreditNote(
            id=new_id("CRN"),
            invoice_id=invoice.id,
            status=CreditNoteStatus.DRAFT,
            reason=reason,
            lines=lines,
            totals=totals,
            version=1,
            created_by=user.id,
            created_at=ctx.now(),
        )
        tx.save_credit_note(credit_note)
        op.audit(
            "credit_note.drafted",
            ("credit_note", credit_note.id),
            after={"invoice": invoice.id, "gross": str(totals.gross_total), "reason": reason},
        )
    return credit_note


def _credit_lines(
    ctx: Context, invoice: Invoice, quantities: Sequence[tuple[int, Decimal]] | None
) -> tuple[tuple[InvoiceLine, ...], Totals]:
    if quantities is None:
        return invoice.lines, invoice.totals
    inputs: list[LineInput] = []
    for index, quantity in quantities:
        if not 0 <= index < len(invoice.lines):
            raise BusinessRuleError(f"ligne {index} inconnue")
        source = invoice.lines[index].source
        if quantity > source.quantity:
            raise BusinessRuleError(f"ligne {index} : quantité supérieure à la quantité facturée")
        inputs.append(replace(source, quantity=quantity))
    return compute_invoice(inputs, invoice.content.global_discount_rate, ctx.calculation)


def validate_credit(ctx: Context, user: User, credit_note_id: str, version: int) -> CreditNote:
    """Valide et numérote l'avoir ; annule la facture s'il couvre tout le TTC."""
    with operation(ctx, user) as op:
        tx = op.tx
        credit_note = tx.get_credit_note(credit_note_id)
        if credit_note is None:
            raise NotFoundError(f"avoir {credit_note_id}")
        if credit_note.version != version:
            raise VersionConflictError(f"version courante {credit_note.version}")
        at = ctx.now()
        number = ctx.numbering.credit_note.format(
            annee=at.year, sequence=tx.next_sequence("credit_note", at.year)
        )
        validated = validate_credit_note(credit_note, by=user.id, at=at, number=number)
        tx.save_credit_note(validated)
        op.audit(
            "credit_note.validated",
            ("credit_note", credit_note.id),
            {"status": credit_note.status},
            {"status": validated.status, "number": number},
        )
        invoice = load(tx, credit_note.invoice_id)
        if is_fully_credited(invoice, tx.credit_notes_for(invoice.id)):
            cancelled = lifecycle.cancel(invoice)
            tx.save_invoice(cancelled)
            op.audit(
                "invoice.cancelled",
                (ENTITY, invoice.id),
                {"status": invoice.status},
                {"status": cancelled.status, "credit_note": number},
            )
    return validated
