"""Tests unitaires et API du rendu HTML et PDF des factures (port DocumentRenderer)."""

from datetime import UTC, date, datetime
from decimal import Decimal

from invoicing.domain.calculation import CalculationRules, compute_invoice
from invoicing.domain.invoice import DraftContent, Invoice, InvoiceStatus, LineInput
from invoicing.domain.referentials import Customer
from invoicing.infrastructure.pdf_renderer import HtmlPdfDocumentRenderer

AT = datetime(2026, 11, 25, tzinfo=UTC)


def _sample_invoice(
    status: InvoiceStatus, number: str | None, content_sha256: str | None = None
) -> Invoice:
    line_inputs = (
        LineInput(
            "Ciment CPJ 35 (sac de 50 kg)", Decimal(20), Decimal(5500), Decimal(18), unit="sac"
        ),
        LineInput("Fer à béton HA 10 mm", Decimal(10), Decimal(4300), Decimal(18), unit="barre"),
    )
    lines, totals = compute_invoice(line_inputs, Decimal(0), CalculationRules())
    content = DraftContent(
        customer_id="CLI-001",
        customer_name="Entreprise Kpadonou et Fils",
        reference="CMD-2026-001",
        issue_date=date(2026, 11, 25),
        due_date=date(2026, 12, 25),
        global_discount_rate=Decimal(0),
        lines=line_inputs,
    )
    return Invoice(
        id="INV-demo",
        source_document_id="DOC-demo",
        status=status,
        content=content,
        lines=lines,
        totals=totals,
        anomalies=(),
        version=2,
        created_by="operateur",
        created_at=AT,
        number=number,
        config_sha256="abc123",
        content_sha256=content_sha256,
    )


def _sample_customer() -> Customer:
    return Customer(
        id="CLI-001",
        legal_name="Entreprise Kpadonou et Fils",
        tax_id="3999900000011",
        phone="+2290199990001",
        email="contact@kpadonou.example",
        preferred_channel="whatsapp",
        payment_terms_days=30,
        vat_liable=True,
    )


def test_pdf_and_html_contain_number_customer_and_gross_total() -> None:
    renderer = HtmlPdfDocumentRenderer()
    sha = "0123456789abcdef" * 4
    invoice = _sample_invoice(InvoiceStatus.VALIDATED, "FA-2026-00001", content_sha256=sha)
    customer = _sample_customer()

    rendered_html = renderer.render_html(invoice, customer)
    assert "FA-2026-00001" in rendered_html
    assert "180 540 FCFA" in rendered_html
    assert "Entreprise Kpadonou et Fils" in rendered_html
    assert "/verifier/INV-demo?code=0123456789abcdef" in rendered_html
    assert "BROUILLON" not in rendered_html

    pdf_bytes = renderer.render_pdf(invoice, customer)
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert pdf_bytes.rstrip().endswith(b"%%EOF")
    assert b"FA-2026-00001" in pdf_bytes
    assert b"180 540 FCFA" in pdf_bytes
    assert "SIMULÉ".encode("cp1252") in pdf_bytes
    assert b"TVA 18 %" in pdf_bytes
    assert b"/verifier/INV-demo?code=0123456789abcdef" in pdf_bytes
    assert b"BROUILLON" not in pdf_bytes


def test_cancelled_invoice_banner_and_html_xss_escaping() -> None:
    renderer = HtmlPdfDocumentRenderer()
    cancelled = _sample_invoice(InvoiceStatus.CANCELLED, "FA-2026-00002")
    pdf_bytes = renderer.render_pdf(cancelled, None)
    assert "ANNULÉE".encode("cp1252") in pdf_bytes

    xss_customer = Customer(
        id="CLI-XSS",
        legal_name="<script>alert(1)</script>",
        tax_id="3999900000011",
        phone="+2290199990001",
        email="x@example.test",
        preferred_channel="email",
        payment_terms_days=30,
        vat_liable=True,
    )
    rendered_html = renderer.render_html(cancelled, xss_customer)
    assert "<script>" not in rendered_html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered_html


def test_draft_pdf_carries_brouillon_mention_and_handles_empty_lines() -> None:
    renderer = HtmlPdfDocumentRenderer()
    draft = _sample_invoice(InvoiceStatus.DRAFT, None)
    pdf_bytes = renderer.render_pdf(draft, _sample_customer())
    assert b"BROUILLON" in pdf_bytes
    assert b"180 540 FCFA" in pdf_bytes


def test_long_invoice_paginates_cleanly_across_multiple_pdf_pages() -> None:
    renderer = HtmlPdfDocumentRenderer()
    many_lines = tuple(
        LineInput(f"Article chantier #{i}", Decimal(2), Decimal(1000), Decimal(18), unit="unité")
        for i in range(45)
    )
    lines, totals = compute_invoice(many_lines, Decimal(0), CalculationRules())
    content = DraftContent(
        customer_id="CLI-001",
        customer_name="Entreprise\nKpadonou",
        reference="CMD-LONG",
        issue_date=date(2026, 11, 25),
        due_date=date(2026, 12, 25),
        global_discount_rate=Decimal(0),
        lines=many_lines,
    )
    inv = Invoice(
        id="INV-long",
        source_document_id="DOC-long",
        status=InvoiceStatus.VALIDATED,
        content=content,
        lines=lines,
        totals=totals,
        anomalies=(),
        version=2,
        created_by="operateur",
        created_at=AT,
        number="FA-2026-00099",
    )
    pdf_bytes = renderer.render_pdf(inv, None)
    assert b"/Count 2" in pdf_bytes
    assert b"FA-2026-00099" in pdf_bytes
    assert b"106 200 FCFA" in pdf_bytes
