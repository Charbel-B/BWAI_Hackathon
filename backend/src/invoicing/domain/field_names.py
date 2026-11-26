"""Noms lisibles des champs extraits, pour les messages destinés aux humains."""

import re

_LINE = re.compile(r"^lines\[(\d+)\]\.(\w+)$")
_FIELDS = {
    "customer.name": "Client",
    "customer.tax_id": "IFU",
    "document.reference": "Référence",
    "document.date": "Date de la pièce",
    "discount.global_rate": "Remise globale",
    "payment.terms_days": "Délai de paiement",
    "payment.due_date": "Échéance",
    "totals.net": "Total HT lu",
    "totals.vat": "TVA lue",
    "totals.gross": "Total TTC lu",
    "lines": "Lignes",
}
_LINE_ATTRS = {
    "label": "Désignation",
    "quantity": "Quantité",
    "unit": "Unité",
    "unit_price": "Prix unitaire",
    "discount_rate": "Remise",
    "delivered_quantity": "Quantité livrée",
}


def human_field(name: str) -> str:
    """« lines[0].quantity » devient « Quantité, ligne 1 » ; un nom inconnu est rendu tel quel."""
    match = _LINE.match(name)
    if match:
        index, attr = match.groups()
        return f"{_LINE_ATTRS.get(attr, attr)}, ligne {int(index) + 1}"
    return _FIELDS.get(name, name)
