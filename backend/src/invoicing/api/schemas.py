"""Schémas HTTP. Les montants sont des Decimal, sérialisés en chaînes par Pydantic."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from invoicing.application.invoices import InvoiceView
from invoicing.domain.audit import AuditEntry
from invoicing.domain.documents import SourceDocument
from invoicing.domain.extraction import ExtractedField, RegionAnchor, TextAnchor
from invoicing.domain.invoice import Anomaly, InvoiceLine, Totals
from invoicing.domain.settlement import CreditNote, Dispatch, Payment
from invoicing.domain.users import User

# --- Entrées ---------------------------------------------------------------------------------


class LoginIn(BaseModel):
    """Identifiants."""

    username: str
    password: str


class ReviewIn(BaseModel):
    """Confirmer la valeur extraite, ou la corriger."""

    action: Literal["confirm", "correct"]
    value: str | None = None


class CreateInvoiceIn(BaseModel):
    """Nouveau brouillon depuis une pièce déjà importée."""

    source_document_id: str


class ResolveIn(BaseModel):
    """Levée d'une anomalie."""

    justification: str = Field(min_length=3)


class DispatchIn(BaseModel):
    """Canal d'émission."""

    channel: str


class PaymentIn(BaseModel):
    """Règlement simulé."""

    amount: Decimal = Field(gt=0)
    method: Literal["mobile_money", "especes", "virement"] = "mobile_money"
    reference: str | None = None


class CreditLineIn(BaseModel):
    """Quantité à créditer sur une ligne de la facture."""

    line_index: int = Field(ge=0)
    quantity: Decimal = Field(gt=0)


class CreditNoteIn(BaseModel):
    """Avoir : total si `lines` est absent."""

    reason: str = Field(min_length=3)
    lines: list[CreditLineIn] | None = None


# --- Sorties ---------------------------------------------------------------------------------


class UserOut(BaseModel):
    """Utilisateur courant."""

    id: str
    username: str
    display_name: str
    role: str


class TokenOut(BaseModel):
    """Jeton porteur."""

    access_token: str
    token_type: str = "bearer"  # noqa: S105 - type de jeton OAuth 2, pas un secret
    user: UserOut


class AnchorOut(BaseModel):
    """Emplacement de la valeur dans la pièce."""

    kind: Literal["text", "region"]
    start: int | None = None
    end: int | None = None
    page: int | None = None
    box: list[float] | None = Field(default=None, min_length=4, max_length=4)


class ReviewOut(BaseModel):
    """Décision humaine sur un champ."""

    state: str
    value: str | None
    by: str | None
    at: datetime | None


class FieldOut(BaseModel):
    """Champ extrait, au format du contrat champ-extrait."""

    name: str
    status: str
    value: str | None
    raw_text: str | None
    confidence: float | None
    anchor: AnchorOut | None
    review: ReviewOut
    effective_value: str | None


class DocumentOut(BaseModel):
    """Pièce source et ses champs."""

    id: str
    filename: str
    media_type: str
    file_sha256: str
    received_at: datetime
    uploaded_by: str
    extractor: str
    fields: list[FieldOut]
    text: str | None = None


class LineOut(BaseModel):
    """Ligne calculée."""

    label: str
    item_id: str | None
    quantity: Decimal
    unit: str | None
    unit_price_net: Decimal
    discount_rate: Decimal
    vat_rate: Decimal
    line_net: Decimal
    line_vat: Decimal


class VatOut(BaseModel):
    """TVA par taux."""

    rate: Decimal
    base: Decimal
    amount: Decimal


class TotalsOut(BaseModel):
    """Totaux stockés et dérivés."""

    lines_net_total: Decimal
    net_total: Decimal
    vat_total: Decimal
    gross_total: Decimal
    global_discount_amount: Decimal
    vat_breakdown: list[VatOut]


class AnomalyOut(BaseModel):
    """Anomalie et sa résolution éventuelle."""

    id: str
    code: str
    severity: str
    field: str | None
    message: str
    resolved: bool
    resolved_by: str | None
    justification: str | None


class CreditNoteOut(BaseModel):
    """Avoir."""

    id: str
    invoice_id: str
    status: str
    number: str | None
    reason: str
    version: int
    lines: list[LineOut]
    totals: TotalsOut
    created_at: datetime


class PaymentOut(BaseModel):
    """Règlement simulé."""

    id: str
    amount: Decimal
    method: str
    reference: str
    received_at: datetime
    is_simulated: bool


class DispatchOut(BaseModel):
    """Émission simulée."""

    id: str
    channel: str
    recipient: str
    message: str
    sent_at: datetime
    is_simulated: bool


class BalanceOut(BaseModel):
    """Solde dérivé."""

    credited_total: Decimal
    paid_total: Decimal
    amount_due: Decimal


class InvoiceOut(BaseModel):
    """Facture complète."""

    id: str
    status: str
    number: str | None
    version: int
    source_document_id: str
    customer_id: str | None
    customer_name: str | None
    reference: str | None
    issue_date: date | None
    due_date: date | None
    global_discount_rate: Decimal
    lines: list[LineOut]
    totals: TotalsOut
    balance: BalanceOut
    payment_status: str
    anomalies: list[AnomalyOut]
    blocking_count: int
    credit_notes: list[CreditNoteOut]
    payments: list[PaymentOut]
    dispatches: list[DispatchOut]
    created_by: str
    created_at: datetime
    validated_by: str | None
    validated_at: datetime | None
    config_sha256: str | None


class InvoiceSummaryOut(BaseModel):
    """Ligne de la liste des factures."""

    id: str
    status: str
    number: str | None
    customer_name: str | None
    gross_total: Decimal
    payment_status: str
    blocking_count: int
    created_at: datetime


class ImportOut(BaseModel):
    """Résultat d'un import : la pièce extraite et son brouillon."""

    document: DocumentOut
    invoice: InvoiceOut


class AuditOut(BaseModel):
    """Entrée du journal."""

    seq: int
    at: datetime
    user_id: str
    action: str
    entity: str
    entity_id: str
    before: dict[str, str | int | None] | None
    after: dict[str, str | int | None] | None
    hash: str


class AuditVerifyOut(BaseModel):
    """Résultat de la vérification de la chaîne."""

    intact: bool
    entries: int
    first_broken_seq: int | None


# --- Conversions ---------------------------------------------------------------------------


def user_out(user: User) -> UserOut:
    """Utilisateur."""
    return UserOut(
        id=user.id, username=user.username, display_name=user.display_name, role=user.role
    )


def _anchor(field: ExtractedField) -> AnchorOut | None:
    if isinstance(field.anchor, TextAnchor):
        return AnchorOut(kind="text", start=field.anchor.start, end=field.anchor.end)
    if isinstance(field.anchor, RegionAnchor):
        return AnchorOut(kind="region", page=field.anchor.page, box=list(field.anchor.box))
    return None


def field_out(field: ExtractedField) -> FieldOut:
    """Champ extrait."""
    r = field.review
    return FieldOut(
        name=field.name,
        status=field.status,
        value=field.value,
        raw_text=field.raw_text,
        confidence=field.confidence,
        anchor=_anchor(field),
        review=ReviewOut(state=r.state, value=r.value, by=r.by, at=r.at),
        effective_value=field.effective_value,
    )


def document_out(document: SourceDocument, content: bytes | None = None) -> DocumentOut:
    """Pièce ; le texte est joint pour l'affichage côte à côte des pièces texte."""
    text = None
    if content is not None and document.media_type.startswith("text/"):
        text = content.decode("utf-8", errors="replace").replace("\r\n", "\n")
    return DocumentOut(
        id=document.id,
        filename=document.filename,
        media_type=document.media_type,
        file_sha256=document.file_sha256,
        received_at=document.received_at,
        uploaded_by=document.uploaded_by,
        extractor=document.extractor,
        fields=[field_out(f) for f in document.fields],
        text=text,
    )


def _line(line: InvoiceLine) -> LineOut:
    s = line.source
    return LineOut(
        label=s.label,
        item_id=s.item_id,
        quantity=s.quantity,
        unit=s.unit,
        unit_price_net=s.unit_price_net,
        discount_rate=s.discount_rate,
        vat_rate=s.vat_rate,
        line_net=line.line_net,
        line_vat=line.line_vat,
    )


def _totals(t: Totals) -> TotalsOut:
    return TotalsOut(
        lines_net_total=t.net_total + t.global_discount_amount,
        net_total=t.net_total,
        vat_total=t.vat_total,
        gross_total=t.gross_total,
        global_discount_amount=t.global_discount_amount,
        vat_breakdown=[VatOut(rate=v.rate, base=v.base, amount=v.amount) for v in t.vat_breakdown],
    )


def _anomaly(a: Anomaly) -> AnomalyOut:
    r = a.resolution
    return AnomalyOut(
        id=a.id,
        code=a.code,
        severity=a.severity,
        field=a.field,
        message=a.message,
        resolved=r is not None,
        resolved_by=r.by if r else None,
        justification=r.justification if r else None,
    )


def credit_note_out(c: CreditNote) -> CreditNoteOut:
    """Avoir."""
    return CreditNoteOut(
        id=c.id,
        invoice_id=c.invoice_id,
        status=c.status,
        number=c.number,
        reason=c.reason,
        version=c.version,
        lines=[_line(line) for line in c.lines],
        totals=_totals(c.totals),
        created_at=c.created_at,
    )


def payment_out(p: Payment) -> PaymentOut:
    """Règlement."""
    return PaymentOut(
        id=p.id,
        amount=p.amount,
        method=p.method,
        reference=p.reference,
        received_at=p.received_at,
        is_simulated=p.is_simulated,
    )


def dispatch_out(d: Dispatch) -> DispatchOut:
    """Émission."""
    return DispatchOut(
        id=d.id,
        channel=d.channel,
        recipient=d.recipient,
        message=d.message,
        sent_at=d.sent_at,
        is_simulated=d.is_simulated,
    )


def invoice_out(v: InvoiceView) -> InvoiceOut:
    """Facture complète, avec ce qui en est dérivé."""
    inv, content = v.invoice, v.invoice.content
    return InvoiceOut(
        id=inv.id,
        status=inv.status,
        number=inv.number,
        version=inv.version,
        source_document_id=inv.source_document_id,
        customer_id=content.customer_id,
        customer_name=content.customer_name,
        reference=content.reference,
        issue_date=content.issue_date,
        due_date=content.due_date,
        global_discount_rate=content.global_discount_rate,
        lines=[_line(line) for line in inv.lines],
        totals=_totals(inv.totals),
        balance=BalanceOut(
            credited_total=v.balance.credited_total,
            paid_total=v.balance.paid_total,
            amount_due=v.balance.amount_due,
        ),
        payment_status=v.balance.status,
        anomalies=[_anomaly(a) for a in inv.anomalies],
        blocking_count=len(inv.open_blocking_anomalies),
        credit_notes=[credit_note_out(c) for c in v.credit_notes],
        payments=[payment_out(p) for p in v.payments],
        dispatches=[dispatch_out(d) for d in v.dispatches],
        created_by=inv.created_by,
        created_at=inv.created_at,
        validated_by=inv.validated_by,
        validated_at=inv.validated_at,
        config_sha256=inv.config_sha256,
    )


def summary_out(v: InvoiceView) -> InvoiceSummaryOut:
    """Résumé pour la liste."""
    inv = v.invoice
    return InvoiceSummaryOut(
        id=inv.id,
        status=inv.status,
        number=inv.number,
        customer_name=inv.content.customer_name,
        gross_total=inv.totals.gross_total,
        payment_status=v.balance.status,
        blocking_count=len(inv.open_blocking_anomalies),
        created_at=inv.created_at,
    )


def audit_out(e: AuditEntry) -> AuditOut:
    """Entrée du journal."""
    ev = e.event
    return AuditOut(
        seq=e.seq,
        at=ev.at,
        user_id=ev.user_id,
        action=ev.action,
        entity=ev.entity,
        entity_id=ev.entity_id,
        before=dict(ev.before) if ev.before is not None else None,
        after=dict(ev.after) if ev.after is not None else None,
        hash=e.hash,
    )
