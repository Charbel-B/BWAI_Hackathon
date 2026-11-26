"""Vérification publique d'une facture par son QR code, sans authentification."""

from dataclasses import dataclass
from enum import StrEnum

from invoicing.application.context import Context
from invoicing.domain.audit import verify_chain
from invoicing.domain.fingerprint import invoice_fingerprint, verification_code
from invoicing.domain.invoice import Invoice, InvoiceStatus


class Verdict(StrEnum):
    """Ce que la page publique affiche."""

    AUTHENTIC = "AUTHENTIC"
    CANCELLED = "CANCELLED"
    ALTERED = "ALTERED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class Verification:
    """Résultat ; la facture n'est rendue que si le code du QR correspond."""

    verdict: Verdict
    invoice: Invoice | None = None
    journal_intact: bool | None = None


def verify(ctx: Context, invoice_id: str, code: str) -> Verification:
    """Trois preuves concordantes : code du QR, empreinte recalculée, empreinte journalisée."""
    with ctx.store.transaction() as tx:
        invoice = tx.get_invoice(invoice_id)
        entries = tx.audit_entries(invoice_id)
        whole_chain = tx.audit_entries()
    if invoice is None or invoice.content_sha256 is None:
        return Verification(Verdict.UNKNOWN)
    if code != verification_code(invoice.content_sha256):
        return Verification(Verdict.UNKNOWN)

    logged = next(
        (
            e.event.after.get("content_sha256")
            for e in entries
            if e.event.action == "invoice.validated" and e.event.after is not None
        ),
        None,
    )
    intact_chain = verify_chain(whole_chain) is None
    recomputed = invoice_fingerprint(invoice)
    if recomputed != invoice.content_sha256 or logged != invoice.content_sha256 or not intact_chain:
        return Verification(Verdict.ALTERED, invoice, intact_chain)
    if invoice.status is InvoiceStatus.CANCELLED:
        return Verification(Verdict.CANCELLED, invoice, intact_chain)
    return Verification(Verdict.AUTHENTIC, invoice, intact_chain)
