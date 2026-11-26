"""Routes des factures : brouillon, anomalies, validation, émission, règlements, avoirs."""

import re
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from invoicing.api.deps import Ctx
from invoicing.api.schemas import (
    CreateInvoiceIn,
    CreditNoteIn,
    CreditNoteOut,
    DispatchIn,
    InvoiceOut,
    InvoiceSummaryOut,
    PaymentIn,
    ResolveIn,
    credit_note_out,
    invoice_out,
    summary_out,
)
from invoicing.api.security import Operator, Validator, Version
from invoicing.application import invoices, settlement
from invoicing.application.context import Context
from invoicing.domain.invoice import InvoiceStatus

router = APIRouter(tags=["factures"])


def _read(ctx: Context, invoice_id: str) -> InvoiceOut:
    with ctx.store.transaction() as tx:
        return invoice_out(invoices.view(tx, invoices.load(tx, invoice_id)))


@router.get("/invoices")
def list_invoices(
    ctx: Ctx, _: Operator, status: InvoiceStatus | None = None
) -> list[InvoiceSummaryOut]:
    """Liste, la plus récente d'abord, filtrable par statut."""
    with ctx.store.transaction() as tx:
        return [summary_out(invoices.view(tx, i)) for i in tx.list_invoices(status)]


@router.post("/invoices", status_code=201)
def create_invoice(ctx: Ctx, user: Operator, body: CreateInvoiceIn) -> InvoiceOut:
    """Nouveau brouillon depuis une pièce déjà importée."""
    invoice = invoices.new_draft_from_document(ctx, user, body.source_document_id)
    return _read(ctx, invoice.id)


@router.get("/invoices/{invoice_id}")
def get_invoice(ctx: Ctx, _: Operator, invoice_id: str) -> InvoiceOut:
    """Facture, totaux, anomalies et statut de paiement dérivé."""
    return _read(ctx, invoice_id)


@router.get("/invoices/{invoice_id}/pdf")
def get_invoice_pdf(ctx: Ctx, _: Operator, invoice_id: str) -> Response:
    """Brouillon ou facture en PDF (mention BROUILLON si non validée)."""
    if ctx.renderer is None:
        return Response(status_code=501)
    with ctx.store.transaction() as tx:
        invoice = invoices.load(tx, invoice_id)
    customer = ctx.referentials.customer(invoice.content.customer_id)
    pdf_bytes = ctx.renderer.render_pdf(invoice, customer)
    raw_name = invoice.number or f"brouillon-{invoice.id}"
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", raw_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@dataclass(frozen=True, slots=True)
class AnomalyPath:
    """Facture et anomalie visées, lues dans le chemin."""

    invoice_id: str
    anomaly_id: str


@router.post("/invoices/{invoice_id}/anomalies/{anomaly_id}/resolve")
def resolve_anomaly(
    ctx: Ctx,
    user: Operator,
    version: Version,
    target: Annotated[AnomalyPath, Depends()],
    body: ResolveIn,
) -> InvoiceOut:
    """Lève une anomalie avec justification."""
    command = invoices.ResolveAnomaly(
        target.invoice_id, target.anomaly_id, body.justification, version
    )
    invoices.resolve(ctx, user, command)
    return _read(ctx, target.invoice_id)


@router.post("/invoices/{invoice_id}/validate")
def validate_invoice(ctx: Ctx, user: Validator, version: Version, invoice_id: str) -> InvoiceOut:
    """Valide et numérote."""
    invoices.validate(ctx, user, invoice_id, version)
    return _read(ctx, invoice_id)


@router.post("/invoices/{invoice_id}/discard")
def discard_invoice(ctx: Ctx, user: Operator, version: Version, invoice_id: str) -> InvoiceOut:
    """Abandonne un brouillon."""
    invoices.discard(ctx, user, invoice_id, version)
    return _read(ctx, invoice_id)


@router.post("/invoices/{invoice_id}/dispatch")
def dispatch_invoice(ctx: Ctx, user: Operator, invoice_id: str, body: DispatchIn) -> InvoiceOut:
    """Émet sur un canal simulé."""
    settlement.dispatch(ctx, user, invoice_id, body.channel)
    return _read(ctx, invoice_id)


@router.post("/invoices/{invoice_id}/payments", status_code=201)
def record_payment(ctx: Ctx, user: Operator, invoice_id: str, body: PaymentIn) -> InvoiceOut:
    """Enregistre un règlement simulé."""
    command = settlement.RecordPayment(invoice_id, body.amount, body.method, body.reference)
    settlement.record_payment(ctx, user, command)
    return _read(ctx, invoice_id)


@router.post("/invoices/{invoice_id}/credit-notes", status_code=201)
def create_credit_note(
    ctx: Ctx, user: Validator, invoice_id: str, body: CreditNoteIn
) -> CreditNoteOut:
    """Crée un avoir en brouillon, total ou par ligne."""
    quantities = None
    if body.lines is not None:
        quantities = [(line.line_index, line.quantity) for line in body.lines]
    return credit_note_out(
        settlement.create_credit_note(ctx, user, invoice_id, body.reason, quantities)
    )


@router.post("/credit-notes/{credit_note_id}/validate")
def validate_credit_note(
    ctx: Ctx, user: Validator, version: Version, credit_note_id: str
) -> CreditNoteOut:
    """Valide et numérote l'avoir."""
    return credit_note_out(settlement.validate_credit(ctx, user, credit_note_id, version))
