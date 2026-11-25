"""Cas d'usage des pièces sources : import avec extraction, puis revue des champs."""

import hashlib

from invoicing.application.context import Context, NotFoundError, new_id, operation
from invoicing.application.invoices import create_draft, refresh_drafts
from invoicing.application.ports import Transaction
from invoicing.domain.documents import SourceDocument, add_field, review_field
from invoicing.domain.extraction import ExtractedField, FieldStatus
from invoicing.domain.invoice import Invoice
from invoicing.domain.users import User


def import_document(
    ctx: Context, user: User, filename: str, media_type: str, content: bytes
) -> tuple[SourceDocument, Invoice]:
    """Enregistre la pièce, lance l'extraction et crée le brouillon dans la même transaction."""
    fields = tuple(ctx.extractor.extract(content, media_type))
    document = SourceDocument(
        id=new_id("DOC"),
        filename=filename,
        media_type=media_type,
        file_sha256=hashlib.sha256(content).hexdigest(),
        received_at=ctx.now(),
        uploaded_by=user.id,
        extractor=ctx.extractor.name,
        fields=fields,
    )
    with operation(ctx, user) as op:
        tx = op.tx
        tx.save_document(document)
        tx.save_document_content(document.id, content)
        op.audit(
            "document.imported",
            ("source_document", document.id),
            after={"filename": filename, "extractor": document.extractor},
        )
        invoice = create_draft(op, document)
    return document, invoice


def get_document(tx: Transaction, document_id: str) -> SourceDocument:
    """Pièce par identifiant."""
    document = tx.get_document(document_id)
    if document is None:
        raise NotFoundError(f"pièce {document_id}")
    return document


def review(
    ctx: Context, user: User, document_id: str, name: str, corrected_value: str | None
) -> SourceDocument:
    """Confirme ou corrige un champ, puis recalcule les brouillons issus de la pièce."""
    with operation(ctx, user) as op:
        tx = op.tx
        document = get_document(tx, document_id)
        if not any(f.name == name for f in document.fields):
            if corrected_value is None:
                raise NotFoundError(f"champ {name}")
            document = add_field(
                document, ExtractedField(name, FieldStatus.MISSING, None, None, None, None)
            )
        before = document.field(name).effective_value
        document = review_field(
            document, name, corrected_value=corrected_value, by=user.id, at=ctx.now()
        )
        tx.save_document(document)
        action = "field.confirmed" if corrected_value is None else "field.corrected"
        op.audit(
            action,
            ("source_document", document.id),
            before={"field": name, "value": before},
            after={"field": name, "value": document.field(name).effective_value},
        )
        refresh_drafts(op, document)
    return document
