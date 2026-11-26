"""Cas d'usage du recouvrement : échéancier des factures non soldées et relances simulées."""

from dataclasses import dataclass
from decimal import Decimal

from invoicing.application.context import Context, new_id, operation
from invoicing.application.invoices import ENTITY, InvoiceView, load, view
from invoicing.domain import collection
from invoicing.domain.collection import Reminder, ReminderStep, Standing
from invoicing.domain.errors import BusinessRuleError
from invoicing.domain.invoice import ZERO, InvoiceStatus
from invoicing.domain.users import User

OPEN_STATUSES = (InvoiceStatus.VALIDATED, InvoiceStatus.ISSUED)
DEFAULT_CHANNEL = "whatsapp"
_ORDER = {Standing.OVERDUE: 0, Standing.DUE_SOON: 1, Standing.NOT_DUE: 2, Standing.NO_DUE_DATE: 3}


@dataclass(frozen=True, slots=True)
class Receivable:
    """Une facture non soldée et sa situation de recouvrement."""

    view: InvoiceView
    standing: Standing
    days_late: int
    next_step: ReminderStep | None
    reminders: tuple[Reminder, ...]


@dataclass(frozen=True, slots=True)
class ReceivablesSummary:
    """Totaux de l'échéancier, calculés ici pour que l'interface n'additionne rien."""

    outstanding: Decimal
    overdue_count: int
    overdue_amount: Decimal
    due_soon_count: int
    due_soon_amount: Decimal


def receivables(ctx: Context) -> tuple[list[Receivable], ReceivablesSummary]:
    """Factures validées avec un reste dû, les plus en retard d'abord."""
    today = ctx.now().date()
    rules = ctx.collection
    items: list[Receivable] = []
    with ctx.store.transaction() as tx:
        for invoice in tx.list_invoices():
            if invoice.status not in OPEN_STATUSES:
                continue
            current = view(tx, invoice)
            if current.balance.amount_due <= ZERO:
                continue
            due = invoice.content.due_date
            sent = tuple(tx.reminders_for(invoice.id))
            items.append(
                Receivable(
                    view=current,
                    standing=collection.standing(due, today, rules),
                    days_late=collection.days_late(due, today),
                    next_step=collection.next_step(due, today, rules, [r.step for r in sent]),
                    reminders=sent,
                )
            )
    items.sort(
        key=lambda r: (_ORDER[r.standing], -r.days_late, r.view.invoice.content.due_date or today)
    )
    return items, _summarize(items)


def _summarize(items: list[Receivable]) -> ReceivablesSummary:
    def total(standing: Standing | None) -> Decimal:
        return sum(
            (
                r.view.balance.amount_due
                for r in items
                if standing is None or r.standing is standing
            ),
            ZERO,
        )

    return ReceivablesSummary(
        outstanding=total(None),
        overdue_count=sum(1 for r in items if r.standing is Standing.OVERDUE),
        overdue_amount=total(Standing.OVERDUE),
        due_soon_count=sum(1 for r in items if r.standing is Standing.DUE_SOON),
        due_soon_amount=total(Standing.DUE_SOON),
    )


def _grouped(amount: Decimal) -> str:
    return f"{amount:,.0f}".replace(",", " ")


def send_reminder(ctx: Context, user: User, invoice_id: str) -> Reminder:
    """Envoie, en simulé, la relance due aujourd'hui sur le canal préféré du client."""
    today = ctx.now().date()
    with operation(ctx, user) as op:
        tx = op.tx
        invoice = load(tx, invoice_id)
        if invoice.status not in OPEN_STATUSES:
            raise BusinessRuleError("seule une facture validée non soldée se relance")
        balance = view(tx, invoice).balance
        if balance.amount_due <= ZERO:
            raise BusinessRuleError("facture soldée : aucune relance")
        due = invoice.content.due_date
        sent = [r.step for r in tx.reminders_for(invoice.id)]
        step = collection.next_step(due, today, ctx.collection, sent)
        if step is None or due is None:
            raise BusinessRuleError("aucune relance à envoyer aujourd'hui")
        customer = ctx.referentials.customer(invoice.content.customer_id)
        channel = customer.preferred_channel if customer else DEFAULT_CHANNEL
        text = step.template.format(
            client=invoice.content.customer_name or "",
            numero=invoice.number,
            montant=_grouped(balance.amount_due),
            echeance=due.strftime("%d/%m/%Y"),
            jours=collection.days_late(due, today),
        )
        delivered = ctx.channel.send_text(customer, channel, text)
        reminder = Reminder(
            id=new_id("REM"),
            invoice_id=invoice.id,
            step=step.code,
            channel=channel,
            recipient=delivered.recipient,
            message=delivered.message,
            sent_at=ctx.now(),
            sent_by=user.id,
        )
        tx.add_reminder(reminder)
        op.audit(
            "invoice.reminded",
            (ENTITY, invoice.id),
            after={"step": step.code, "channel": channel, "amount_due": str(balance.amount_due)},
        )
    return reminder
