"""Routes des pièces sources : import, lecture, fichier original, revue des champs."""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import Response

from invoicing.api.deps import Ctx
from invoicing.api.errors import ApiError
from invoicing.api.schemas import DocumentOut, ImportOut, ReviewIn, document_out, invoice_out
from invoicing.api.security import Operator
from invoicing.application import documents, invoices

router = APIRouter(prefix="/source-documents", tags=["pièces"])
MAX_BYTES = 2_000_000


@router.post("", status_code=201)
async def import_document(
    ctx: Ctx, user: Operator, file: Annotated[UploadFile, File()]
) -> ImportOut:
    """Importe une pièce, l'extrait et crée son brouillon."""
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ApiError(413, "INVALID_INPUT", "pièce trop volumineuse (2 Mo au plus)")
    media_type = file.content_type or "application/octet-stream"
    document, invoice = documents.import_document(
        ctx, user, file.filename or "piece", media_type, content
    )
    with ctx.store.transaction() as tx:
        return ImportOut(
            document=document_out(document, content),
            invoice=invoice_out(invoices.view(tx, invoice)),
        )


@router.get("/{document_id}")
def get_document(ctx: Ctx, _: Operator, document_id: str) -> DocumentOut:
    """Pièce, champs extraits et texte pour l'affichage côte à côte."""
    with ctx.store.transaction() as tx:
        document = documents.get_document(tx, document_id)
        return document_out(document, tx.get_document_content(document_id))


@router.get("/{document_id}/file")
def get_file(ctx: Ctx, _: Operator, document_id: str) -> Response:
    """Fichier original."""
    with ctx.store.transaction() as tx:
        document = documents.get_document(tx, document_id)
        content = tx.get_document_content(document_id) or b""
    return Response(content, media_type=document.media_type)


@router.post("/{document_id}/fields/{name}/review")
def review_field(
    ctx: Ctx, user: Operator, document_id: str, name: str, body: ReviewIn
) -> DocumentOut:
    """Confirme ou corrige un champ ; les brouillons de la pièce sont recalculés."""
    if body.action == "correct" and body.value is None:
        raise ApiError(422, "INVALID_INPUT", "une correction porte une valeur")
    value = body.value if body.action == "correct" else None
    document = documents.review(ctx, user, document_id, name, value)
    with ctx.store.transaction() as tx:
        return document_out(document, tx.get_document_content(document_id))
