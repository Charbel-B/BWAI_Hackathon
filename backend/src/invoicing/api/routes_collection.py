"""Routes du recouvrement : échéancier et relances simulées."""

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel

from invoicing.api.deps import Ctx
from invoicing.api.schemas import InvoiceSummaryOut, summary_out
from invoicing.api.security import Operator
from invoicing.application import collection
from invoicing.domain.collection import Reminder

router = APIRouter(tags=["recouvrement"])


class ReminderOut(BaseModel):
    """Relance envoyée (simulée)."""

    id: str
    step: str
    channel: str
    recipient: str
    message: str
    sent_at: datetime
    is_simulated: bool


class NextStepOut(BaseModel):
    """Relance à envoyer aujourd'hui."""

    code: str
    label: str


class ReceivableOut(BaseModel):
    """Facture non soldée et sa situation."""

    invoice: InvoiceSummaryOut
    amount_due: Decimal
    due_date: date | None
    standing: str
    days_late: int
    next_step: NextStepOut | None
    reminders: list[ReminderOut]


class StepOut(BaseModel):
    """Étape de relance configurée."""

    code: str
    label: str
    offset_days: int


class ReceivablesOut(BaseModel):
    """Échéancier, ses totaux et les étapes de relance configurées."""

    outstanding: Decimal
    overdue_count: int
    overdue_amount: Decimal
    due_soon_count: int
    due_soon_amount: Decimal
    steps: list[StepOut]
    items: list[ReceivableOut]


def _reminder(r: Reminder) -> ReminderOut:
    return ReminderOut(
        id=r.id,
        step=r.step,
        channel=r.channel,
        recipient=r.recipient,
        message=r.message,
        sent_at=r.sent_at,
        is_simulated=r.is_simulated,
    )


@router.get("/receivables")
def list_receivables(ctx: Ctx, _: Operator) -> ReceivablesOut:
    """Factures validées avec un reste dû, les plus en retard d'abord."""
    items, summary = collection.receivables(ctx)
    return ReceivablesOut(
        outstanding=summary.outstanding,
        overdue_count=summary.overdue_count,
        overdue_amount=summary.overdue_amount,
        due_soon_count=summary.due_soon_count,
        due_soon_amount=summary.due_soon_amount,
        steps=[
            StepOut(code=s.code, label=s.label, offset_days=s.offset_days)
            for s in ctx.collection.steps
        ],
        items=[
            ReceivableOut(
                invoice=summary_out(r.view),
                amount_due=r.view.balance.amount_due,
                due_date=r.view.invoice.content.due_date,
                standing=r.standing,
                days_late=r.days_late,
                next_step=NextStepOut(code=r.next_step.code, label=r.next_step.label)
                if r.next_step
                else None,
                reminders=[_reminder(m) for m in r.reminders],
            )
            for r in items
        ],
    )


@router.post("/invoices/{invoice_id}/reminders", status_code=201)
def send_reminder(ctx: Ctx, user: Operator, invoice_id: str) -> ReminderOut:
    """Envoie la relance due aujourd'hui, sur le canal préféré du client (simulé)."""
    return _reminder(collection.send_reminder(ctx, user, invoice_id))
