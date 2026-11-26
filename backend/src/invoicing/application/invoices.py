"""Cas d'usage des factures : brouillon, résolution d'anomalie, validation, abandon."""

import re
from dataclasses import dataclass

from invoicing.application.context import Context, NotFoundError, Operation, new_id, operation
from invoicing.application.ports import Transaction
from invoicing.domain import lifecycle
from invoicing.domain.calculation import compute_invoice
from invoicing.domain.controls import DraftUnderReview, RelatedDocument, check_draft
from invoicing.domain.documents import SourceDocument
from invoicing.domain.drafting import build_draft, delivered_quantities
from invoicing.domain.invoice import (
    EMPTY_TOTALS,
    Anomaly,
    DraftContent,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Resolution,
    Totals,
)
from invoicing.domain.settlement import Balance, CreditNote, Dispatch, Payment, compute_balance
from invoicing.domain.users import User

ENTITY = "invoice"


@dataclass(frozen=True, slots=True)
class InvoiceView:
    """Facture et tout ce qui en dérive, pour la lecture."""

    invoice: Invoice
    balance: Balance
    credit_notes: tuple[CreditNote, ...]
    payments: tuple[Payment, ...]
    dispatches: tuple[Dispatch, ...]


@dataclass(frozen=True, slots=True)
class ResolveAnomaly:
    """Demande de levée d'une anomalie."""

    invoice_id: str
    anomaly_id: str
    justification: str
    version: int


def _state(invoice: Invoice) -> dict[str, str | int | None]:
    return {"status": invoice.status, "version": invoice.version, "number": invoice.number}


@dataclass(frozen=True, slots=True)
class _Evaluation:
    content: DraftContent
    lines: tuple[InvoiceLine, ...]
    totals: Totals
    anomalies: tuple[Anomaly, ...]


_RE_BL_TOKEN = re.compile(r"(?:^|[^a-z0-9])bl(?:[^a-z0-9]|$)")


def _evaluate(
    tx: Transaction, ctx: Context, document: SourceDocument, invoice_id: str
) -> _Evaluation:
    """Brouillon, calcul et contrôles : la même chaîne à la création et à chaque correction."""
    content = build_draft(document.fields, ctx.referentials, ctx.calculation.default_vat_rate)
    if content.lines:
        lines, totals = compute_invoice(
            content.lines, content.global_discount_rate, ctx.calculation
        )
    else:
        lines, totals = (), EMPTY_TOTALS
    duplicate = _duplicate_of(tx, document, content.customer_id, content.reference, invoice_id)
    delivered = delivered_quantities(
        document.fields, ctx.referentials, ctx.calculation.default_vat_rate
    )
    related = _related_documents(tx, document, content, invoice_id)
    draft = DraftUnderReview(
        content=content,
        totals=totals,
        fields=document.fields,
        duplicate_of=duplicate,
        delivered_quantities=delivered,
        related_documents=related,
    )
    anomalies = check_draft(draft, ctx.referentials, ctx.controls)
    return _Evaluation(content, lines, totals, anomalies)


def _related_documents(
    tx: Transaction,
    document: SourceDocument,
    content: DraftContent,
    invoice_id: str,
) -> tuple[RelatedDocument, ...]:
    """Autres pièces actives portant la même référence, pour contrôler la cohérence."""
    if not content.reference:
        return ()
    target_ref = _norm_ref(content.reference)
    related: list[RelatedDocument] = []
    seen_docs: set[str] = {document.id}
    for inv in tx.list_invoices():
        if inv.id == invoice_id or inv.status is InvoiceStatus.DISCARDED:
            continue
        if inv.source_document_id in seen_docs:
            continue
        other_ref = inv.content.reference
        if not other_ref or _norm_ref(other_ref) != target_ref:
            continue
        seen_docs.add(inv.source_document_id)
        other_doc = tx.get_document(inv.source_document_id)
        kind = _infer_related_kind(other_doc.filename if other_doc else None, other_ref)
        related.append(
            RelatedDocument(
                kind=kind,
                customer_name=inv.content.customer_name,
                reference=other_ref,
                issue_date=inv.content.issue_date,
            )
        )
    return tuple(related)


def _infer_related_kind(filename: str | None, reference: str) -> str:
    lower_name = (filename or "").lower()
    upper_ref = reference.strip().upper()
    if "devis" in lower_name or "quote" in lower_name or upper_ref.startswith("DEV-"):
        return "devis"
    if "livraison" in lower_name or _RE_BL_TOKEN.search(lower_name) or upper_ref.startswith("BL-"):
        return "bon de livraison"
    return "commande"


def _norm_ref(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _duplicate_of(
    tx: Transaction,
    document: SourceDocument,
    customer_id: str | None,
    reference: str | None,
    invoice_id: str,
) -> str | None:
    """Même fichier, ou même client et même référence, déjà traité dans une autre facture."""
    for other in tx.documents_by_sha(document.file_sha256):
        if other.id != document.id:
            return other.filename
    if customer_id and reference:
        for inv in tx.list_invoices():
            same = inv.content.customer_id == customer_id and inv.content.reference == reference
            if same and inv.id != invoice_id and inv.status is not InvoiceStatus.DISCARDED:
                return inv.number or inv.id
    return None


def create_draft(op: Operation, document: SourceDocument) -> Invoice:
    """Crée le brouillon d'une pièce : recalcul et contrôles, version 1."""
    tx, ctx = op.tx, op.ctx
    invoice_id = new_id("INV")
    evaluation = _evaluate(tx, ctx, document, invoice_id)
    invoice = Invoice(
        id=invoice_id,
        source_document_id=document.id,
        status=InvoiceStatus.DRAFT,
        content=evaluation.content,
        lines=evaluation.lines,
        totals=evaluation.totals,
        anomalies=evaluation.anomalies,
        version=1,
        created_by=op.user.id,
        created_at=ctx.now(),
    )
    tx.save_invoice(invoice)
    op.audit("invoice.drafted", (ENTITY, invoice.id), after=_state(invoice))
    return invoice


def refresh_drafts(op: Operation, document: SourceDocument) -> None:
    """Recalcule les brouillons issus d'une pièce après la revue d'un champ."""
    tx, ctx = op.tx, op.ctx
    for invoice in tx.invoices_for_document(document.id):
        if invoice.status is not InvoiceStatus.DRAFT:
            continue
        e = _evaluate(tx, ctx, document, invoice.id)
        updated = lifecycle.recompute_draft(invoice, e.content, e.lines, e.totals, e.anomalies)
        tx.save_invoice(updated)
        op.audit(
            "invoice.recomputed",
            (ENTITY, invoice.id),
            _state(invoice),
            _state(updated),
        )


def new_draft_from_document(ctx: Context, user: User, document_id: str) -> Invoice:
    """Nouveau brouillon depuis une pièce déjà importée (par exemple après un avoir total)."""
    with operation(ctx, user) as op:
        tx = op.tx
        document = tx.get_document(document_id)
        if document is None:
            raise NotFoundError(f"pièce {document_id}")
        return create_draft(op, document)


def load(tx: Transaction, invoice_id: str) -> Invoice:
    """Facture par identifiant."""
    invoice = tx.get_invoice(invoice_id)
    if invoice is None:
        raise NotFoundError(f"facture {invoice_id}")
    return invoice


def view(tx: Transaction, invoice: Invoice) -> InvoiceView:
    """Facture avec son solde et son statut de paiement, dérivés à la lecture."""
    credit_notes = tuple(tx.credit_notes_for(invoice.id))
    payments = tuple(tx.payments_for(invoice.id))
    return InvoiceView(
        invoice,
        compute_balance(invoice, credit_notes, payments),
        credit_notes,
        payments,
        tuple(tx.dispatches_for(invoice.id)),
    )


def resolve(ctx: Context, user: User, command: ResolveAnomaly) -> Invoice:
    """Lève une anomalie avec justification."""
    invoice_id, anomaly_id = command.invoice_id, command.anomaly_id
    justification, version = command.justification, command.version
    with operation(ctx, user) as op:
        tx = op.tx
        invoice = load(tx, invoice_id)
        lifecycle.ensure_version(invoice, version)
        updated = lifecycle.resolve_anomaly(
            invoice, anomaly_id, Resolution(user.id, ctx.now(), justification)
        )
        tx.save_invoice(updated)
        op.audit(
            "anomaly.resolved",
            (ENTITY, invoice.id),
            {"anomaly": anomaly_id},
            {"anomaly": anomaly_id, "justification": justification},
        )
    return updated


def validate(ctx: Context, user: User, invoice_id: str, version: int) -> Invoice:
    """Valide et numérote. Le compteur n'avance que si toute la transaction réussit."""
    with operation(ctx, user) as op:
        tx = op.tx
        invoice = load(tx, invoice_id)
        lifecycle.ensure_version(invoice, version)
        lifecycle.check_can_validate(invoice, user.id, ctx.separation_of_duties)
        at = ctx.now()
        sequence = tx.next_sequence("invoice", at.year)
        number = ctx.numbering.invoice.format(annee=at.year, sequence=sequence)
        stamp = lifecycle.ValidationStamp(user.id, at, number, ctx.config_sha256)
        updated = lifecycle.validate(invoice, stamp, ctx.separation_of_duties)
        tx.save_invoice(updated)
        op.audit(
            "invoice.validated",
            (ENTITY, invoice.id),
            _state(invoice),
            _state(updated),
        )
    return updated


def discard(ctx: Context, user: User, invoice_id: str, version: int) -> Invoice:
    """Abandonne un brouillon, sans consommer de numéro."""
    with operation(ctx, user) as op:
        tx = op.tx
        invoice = load(tx, invoice_id)
        lifecycle.ensure_version(invoice, version)
        updated = lifecycle.discard(invoice)
        tx.save_invoice(updated)
        op.audit(
            "invoice.discarded",
            (ENTITY, invoice.id),
            _state(invoice),
            _state(updated),
        )
    return updated
