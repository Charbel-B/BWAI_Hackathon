"""Rendu HTML et PDF 1.4 multi-pages d'un brouillon ou d'une facture (port DocumentRenderer)."""

import html
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from string import Template

from invoicing.domain.invoice import Invoice, InvoiceLine, InvoiceStatus
from invoicing.domain.referentials import Customer

_TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "invoice.html"
_SIMULATION_MENTION = "SIMULÉ — e-MECeF simulé, document de démonstration non valable fiscalement"
_PAGE_START_Y = 795
_PAGE_BOTTOM_Y = 60
_LEFT_X = 45
_RIGHT_X = 550


@dataclass(frozen=True, slots=True)
class IssuerInfo:
    """Coordonnées fictives de la PME émettrice."""

    name: str = "Z-Flow Distribution SARL (fictif)"
    address: str = "Lot 245 Akpakpa, Cotonou, Bénin"
    tax_id: str = "3201234567890"
    phone: str = "+229 01 21 00 00 00"


@dataclass(frozen=True, slots=True)
class _PdfItem:
    """Élément visuel d'une page PDF : ligne de texte ou filet horizontal vectoriel."""

    kind: str  # "text" | "rule"
    font: str = "F1"
    size: int = 10
    text: str = ""


def _fmt_fcfa(amount: Decimal) -> str:
    rounded = int(amount)
    return f"{rounded:,}".replace(",", " ") + " FCFA"


def _fmt_rate(rate: Decimal) -> str:
    pct = rate * Decimal(100)
    return f"{pct.normalize():f} %" if pct else "0 %"


def _escape_pdf_text(text: str) -> str:
    one_line = " ".join(text.splitlines())
    latin = one_line.encode("cp1252", errors="replace").decode("cp1252")
    return latin.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class HtmlPdfDocumentRenderer:
    """Rend une facture depuis son gabarit HTML et génère un PDF 1.4 multi-pages autonome."""

    def __init__(self, issuer: IssuerInfo | None = None) -> None:
        self._issuer = issuer or IssuerInfo()
        self._template = Template(_TEMPLATE_PATH.read_text(encoding="utf-8"))

    def render_html(self, invoice: Invoice, customer: Customer | None) -> str:
        """Rend le gabarit HTML complet avec échappement strict des valeurs."""
        is_draft = invoice.status is InvoiceStatus.DRAFT
        banner = (
            '<div class="banner">BROUILLON — NON VALIDÉ, NON VALABLE FISCALEMENT</div>'
            if is_draft
            else ""
        )
        rows = (
            "\n".join(self._html_row(line) for line in invoice.lines)
            if invoice.lines
            else '<tr><td colspan="7">Aucune ligne extraite (brouillon incomplet)</td></tr>'
        )
        vat_rows = "\n".join(
            f"<tr><th>TVA {html.escape(str(v.rate))} % (base {html.escape(_fmt_fcfa(v.base))})</th>"
            f'<td class="num">{html.escape(_fmt_fcfa(v.amount))}</td></tr>'
            for v in invoice.totals.vat_breakdown
        )
        return self._template.substitute(
            draft_banner=banner,
            issuer_name=html.escape(self._issuer.name),
            issuer_address=html.escape(self._issuer.address),
            issuer_ifu=html.escape(self._issuer.tax_id),
            issuer_phone=html.escape(self._issuer.phone),
            number=html.escape(invoice.number or "BROUILLON"),
            status=html.escape(invoice.status.value),
            issue_date=html.escape(str(invoice.content.issue_date or "-")),
            due_date=html.escape(str(invoice.content.due_date or "-")),
            customer_name=html.escape(
                customer.legal_name if customer else (invoice.content.customer_name or "-")
            ),
            customer_ifu=html.escape((customer.tax_id if customer else None) or "Non renseigné"),
            customer_phone=html.escape((customer.phone if customer else None) or "-"),
            customer_email=html.escape((customer.email if customer else None) or "-"),
            rows_html=rows,
            net_total=html.escape(_fmt_fcfa(invoice.totals.net_total)),
            global_discount=html.escape(_fmt_fcfa(invoice.totals.global_discount_amount)),
            vat_breakdown_html=vat_rows,
            vat_total=html.escape(_fmt_fcfa(invoice.totals.vat_total)),
            gross_total=html.escape(_fmt_fcfa(invoice.totals.gross_total)),
            config_sha256=html.escape(invoice.config_sha256 or "brouillon"),
        )

    def render_pdf(self, invoice: Invoice, customer: Customer | None) -> bytes:
        """Génère un PDF 1.4 A4 paginé automatiquement contenant toutes les mentions."""
        _ = self.render_html(invoice, customer)
        items = self._pdf_items(invoice, customer)
        page_streams = _paginate_pdf_items(items)
        return _assemble_multipage_pdf(page_streams)

    @staticmethod
    def _html_row(line: InvoiceLine) -> str:
        src = line.source
        return (
            "<tr>"
            f"<td>{html.escape(src.label)}</td>"
            f'<td class="num">{html.escape(str(src.quantity))}</td>'
            f"<td>{html.escape(src.unit or '-')}</td>"
            f'<td class="num">{html.escape(_fmt_fcfa(src.unit_price_net))}</td>'
            f'<td class="num">{html.escape(_fmt_rate(src.discount_rate))}</td>'
            f'<td class="num">{html.escape(_fmt_fcfa(line.line_net))}</td>'
            f'<td class="num">{html.escape(_fmt_fcfa(line.line_vat))}</td>'
            "</tr>"
        )

    def _pdf_items(self, invoice: Invoice, customer: Customer | None) -> list[_PdfItem]:
        doc_num = invoice.number or "BROUILLON"
        cust_name = customer.legal_name if customer else (invoice.content.customer_name or "-")
        cust_ifu = (customer.tax_id if customer else None) or "Non renseigné"

        items: list[_PdfItem] = []
        if invoice.status is InvoiceStatus.DRAFT:
            items.append(
                _PdfItem("text", "F2", 14, "BROUILLON - NON VALIDÉ, NON VALABLE FISCALEMENT")
            )
        items.extend(
            [
                _PdfItem("text", "F2", 14, self._issuer.name),
                _PdfItem("text", "F1", 10, f"{self._issuer.address} | IFU : {self._issuer.tax_id}"),
                _PdfItem("text", "F1", 10, f"Tél. : {self._issuer.phone}"),
                _PdfItem("rule"),
                _PdfItem(
                    "text", "F2", 13, f"FACTURE : {doc_num}  (Statut : {invoice.status.value})"
                ),
                _PdfItem(
                    "text",
                    "F1",
                    10,
                    f"Date : {invoice.content.issue_date or '-'}   |   "
                    f"Échéance : {invoice.content.due_date or '-'}",
                ),
                _PdfItem("text", "F2", 11, f"Client : {cust_name}"),
                _PdfItem("text", "F1", 10, f"IFU client : {cust_ifu}"),
                _PdfItem("rule"),
                _PdfItem("text", "F2", 10, "Désignation | Qté | PU HT | HT | TVA"),
            ]
        )
        if not invoice.lines:
            items.append(_PdfItem("text", "F1", 10, "Aucune ligne extraite (brouillon incomplet)"))
        for line in invoice.lines:
            src = line.source
            items.append(
                _PdfItem(
                    "text",
                    "F1",
                    9,
                    f"{src.label[:42]} | {src.quantity} {src.unit or ''} | "
                    f"{_fmt_fcfa(src.unit_price_net)} | {_fmt_fcfa(line.line_net)} | "
                    f"TVA {_fmt_fcfa(line.line_vat)}",
                )
            )
        items.append(_PdfItem("rule"))
        items.append(
            _PdfItem("text", "F1", 11, f"Total HT : {_fmt_fcfa(invoice.totals.net_total)}")
        )
        items.append(
            _PdfItem(
                "text",
                "F1",
                10,
                f"Remise globale : {_fmt_fcfa(invoice.totals.global_discount_amount)}",
            )
        )
        for v in invoice.totals.vat_breakdown:
            items.append(
                _PdfItem(
                    "text",
                    "F1",
                    9,
                    f"TVA {v.rate} % (base {_fmt_fcfa(v.base)}) : {_fmt_fcfa(v.amount)}",
                )
            )
        items.extend(
            [
                _PdfItem("text", "F1", 11, f"Total TVA : {_fmt_fcfa(invoice.totals.vat_total)}"),
                _PdfItem("text", "F2", 13, f"TOTAL TTC : {_fmt_fcfa(invoice.totals.gross_total)}"),
                _PdfItem("rule"),
                _PdfItem("text", "F1", 8, _SIMULATION_MENTION),
                _PdfItem(
                    "text", "F1", 8, f"Empreinte règles : {invoice.config_sha256 or 'brouillon'}"
                ),
            ]
        )
        return items


def _paginate_pdf_items(items: list[_PdfItem]) -> list[bytes]:
    pages: list[list[str]] = [[]]
    y = _PAGE_START_Y

    for item in items:
        step = 12 if item.kind == "rule" else item.size + 6
        if y - step < _PAGE_BOTTOM_Y and pages[-1]:
            pages.append([])
            y = _PAGE_START_Y
        if item.kind == "rule":
            pages[-1].append(f"0.6 w 0.65 G {_LEFT_X} {y} m {_RIGHT_X} {y} l S 0 G")
        else:
            escaped = _escape_pdf_text(item.text)
            pages[-1].append(f"BT /{item.font} {item.size} Tf {_LEFT_X} {y} Td ({escaped}) Tj ET")
        y -= step

    return ["\n".join(cmds).encode("cp1252", errors="replace") for cmds in pages]


def _assemble_multipage_pdf(page_streams: list[bytes]) -> bytes:
    """Assemble un document PDF 1.4 multi-pages avec table xref exacte."""
    # Objets fixes : 1=Catalog, 2=Pages, 3=Helvetica, 4=Helvetica-Bold
    page_ids: list[int] = []
    dynamic_objects: list[bytes] = []
    next_id = 5
    for stream in page_streams:
        page_id = next_id
        content_id = next_id + 1
        next_id += 2
        page_ids.append(page_id)
        page_dict = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        )
        dynamic_objects.append(page_dict.encode("ascii"))
        dynamic_objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream"
        )

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        *dynamic_objects,
    ]
    parts: list[bytes] = [b"%PDF-1.4\n"]
    offsets: list[int] = [0]
    for obj_num, body in enumerate(objects, start=1):
        offsets.append(sum(len(p) for p in parts))
        parts.append(f"{obj_num} 0 obj\n".encode("ascii") + body + b"\nendobj\n")

    xref_pos = sum(len(p) for p in parts)
    xref_lines = [f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii")]
    for off in offsets[1:]:
        xref_lines.append(f"{off:010d} 00000 n \n".encode("ascii"))
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode("ascii")
    return b"".join(parts + xref_lines + [trailer])
