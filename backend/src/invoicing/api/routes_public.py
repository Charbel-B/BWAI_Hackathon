"""Routes publiques, sans authentification : uniquement la vérification d'une facture."""

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel

from invoicing.api.deps import Ctx
from invoicing.application.verification import verify

router = APIRouter(prefix="/public", tags=["public"])


class VerificationOut(BaseModel):
    """Ce qu'un client voit en scannant le QR code : le strict nécessaire, rien de plus."""

    verdict: str
    number: str | None = None
    customer_name: str | None = None
    issue_date: date | None = None
    gross_total: Decimal | None = None
    validated_at: datetime | None = None
    content_sha256: str | None = None
    journal_intact: bool | None = None


@router.get("/verify/{invoice_id}")
def verify_invoice(ctx: Ctx, invoice_id: str, code: str = "") -> VerificationOut:
    """Authentique, annulée par avoir, altérée, ou inconnue (code faux ou facture absente)."""
    result = verify(ctx, invoice_id, code)
    invoice = result.invoice
    if invoice is None:
        return VerificationOut(verdict=result.verdict)
    return VerificationOut(
        verdict=result.verdict,
        number=invoice.number,
        customer_name=invoice.content.customer_name,
        issue_date=invoice.content.issue_date,
        gross_total=invoice.totals.gross_total,
        validated_at=invoice.validated_at,
        content_sha256=invoice.content_sha256,
        journal_intact=result.journal_intact,
    )
