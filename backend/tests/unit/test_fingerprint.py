from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from invoicing.domain.calculation import CalculationRules, compute_invoice
from invoicing.domain.fingerprint import invoice_fingerprint, verification_code
from invoicing.domain.invoice import DraftContent, Invoice, InvoiceStatus, LineInput

AT = datetime(2026, 11, 26, 8, tzinfo=UTC)


def _invoice() -> Invoice:
    line = LineInput("Ciment", Decimal(20), Decimal(5500), Decimal(18))
    lines, totals = compute_invoice([line], Decimal(0), CalculationRules())
    content = DraftContent("CLI-001", "Kpadonou", "CMD-1", None, None, Decimal(0), (line,))
    return Invoice(
        "INV-1",
        "DOC-1",
        InvoiceStatus.VALIDATED,
        content,
        lines,
        totals,
        (),
        2,
        "u",
        AT,
        number="FA-2026-00001",
    )


def test_fingerprint_is_stable_and_sensitive_to_content() -> None:
    invoice = _invoice()
    assert invoice_fingerprint(invoice) == invoice_fingerprint(invoice)
    renamed = replace(invoice, content=replace(invoice.content, customer_name="Autre"))
    assert invoice_fingerprint(renamed) != invoice_fingerprint(invoice)


def test_fingerprint_ignores_lifecycle_status() -> None:
    invoice = _invoice()
    assert invoice_fingerprint(
        replace(invoice, status=InvoiceStatus.ISSUED)
    ) == invoice_fingerprint(invoice)


def test_verification_code_is_the_fingerprint_prefix() -> None:
    fingerprint = invoice_fingerprint(_invoice())
    assert verification_code(fingerprint) == fingerprint[:16]
