"""Empreinte du contenu d'une facture validée.

Calculée à la validation et inscrite dans le journal chaîné : la recalculer plus tard et
retrouver la même valeur prouve que la facture n'a pas été modifiée depuis.
"""

import hashlib
import json

from invoicing.domain.invoice import Invoice


def invoice_fingerprint(invoice: Invoice) -> str:
    """SHA-256 d'une sérialisation canonique des données qui font la facture."""
    content = invoice.content
    payload = {
        "number": invoice.number,
        "customer_id": content.customer_id,
        "customer_name": content.customer_name,
        "reference": content.reference,
        "issue_date": content.issue_date.isoformat() if content.issue_date else None,
        "due_date": content.due_date.isoformat() if content.due_date else None,
        "lines": [
            {
                "label": line.source.label,
                "quantity": str(line.source.quantity),
                "unit_price_net": str(line.source.unit_price_net),
                "discount_rate": str(line.source.discount_rate),
                "vat_rate": str(line.source.vat_rate),
                "line_net": str(line.line_net),
            }
            for line in invoice.lines
        ],
        "net_total": str(invoice.totals.net_total),
        "vat_total": str(invoice.totals.vat_total),
        "gross_total": str(invoice.totals.gross_total),
        "config_sha256": invoice.config_sha256,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


VERIFICATION_CODE_LENGTH = 16


def verification_code(fingerprint: str) -> str:
    """Code court porté par le QR code : le début de l'empreinte."""
    return fingerprint[:VERIFICATION_CODE_LENGTH]
