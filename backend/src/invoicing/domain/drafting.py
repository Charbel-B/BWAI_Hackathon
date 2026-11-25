"""Passage des champs revus d'une pièce au contenu d'un brouillon de facture."""

import re
from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from invoicing.domain.errors import InvariantViolationError
from invoicing.domain.extraction import ExtractedField
from invoicing.domain.invoice import ZERO, DraftContent, LineInput
from invoicing.domain.referentials import Referentials

LINE_FIELD = re.compile(r"^lines\[(?P<idx>\d+)\]\.(?P<attr>\w+)$")
REQUIRED_HEADER_FIELDS = ("customer.name", "document.date")
REQUIRED_LINE_ATTRS = ("label", "quantity", "unit_price")


def parse_decimal(value: str | None) -> Decimal | None:
    """Décimal ou None si la valeur est absente ou illisible."""
    if value is None:
        return None
    try:
        result = Decimal(value)
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def parse_date(value: str | None) -> date | None:
    """Date ISO ou None si la valeur est absente ou illisible."""
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def effective_values(fields: Sequence[ExtractedField]) -> dict[str, str | None]:
    """Valeur retenue de chaque champ : la correction humaine prime sur l'extraction."""
    return {f.name: f.effective_value for f in fields}


def line_indexes(fields: Sequence[ExtractedField]) -> list[int]:
    """Indices des lignes présentes dans les champs, triés."""
    found = {int(m["idx"]) for f in fields if (m := LINE_FIELD.match(f.name))}
    return sorted(found)


def build_draft(
    fields: Sequence[ExtractedField],
    referentials: Referentials,
    default_vat_rate: Decimal,
) -> DraftContent:
    """Construit le brouillon. Une ligne incomplète est écartée ; les contrôles la signalent."""
    values = effective_values(fields)
    customer = referentials.find_customer(
        values.get("customer.name"), values.get("customer.tax_id")
    )
    vat_liable = customer.vat_liable if customer else True
    lines = tuple(
        line
        for idx in line_indexes(fields)
        if (line := _build_line(values, idx, referentials, default_vat_rate, vat_liable))
    )
    issue_date = parse_date(values.get("document.date"))
    return DraftContent(
        customer_id=customer.id if customer else None,
        customer_name=customer.legal_name if customer else values.get("customer.name"),
        reference=values.get("document.reference"),
        issue_date=issue_date,
        due_date=_due_date(values, issue_date, customer.payment_terms_days if customer else None),
        global_discount_rate=parse_decimal(values.get("discount.global_rate")) or ZERO,
        lines=lines,
        declared_net=parse_decimal(values.get("totals.net")),
        declared_gross=parse_decimal(values.get("totals.gross")),
    )


def _build_line(
    values: dict[str, str | None],
    idx: int,
    referentials: Referentials,
    default_vat_rate: Decimal,
    vat_liable: bool,
) -> LineInput | None:
    label = values.get(f"lines[{idx}].label")
    quantity = parse_decimal(values.get(f"lines[{idx}].quantity"))
    price = parse_decimal(values.get(f"lines[{idx}].unit_price"))
    if label is None or quantity is None or price is None:
        return None
    item = referentials.find_item(label)
    rate = (item.vat_rate if item else default_vat_rate) if vat_liable else ZERO
    try:
        return LineInput(
            label=label,
            quantity=quantity,
            unit_price_net=price,
            vat_rate=rate,
            item_id=item.id if item else None,
            unit=values.get(f"lines[{idx}].unit") or (item.unit if item else None),
            discount_rate=parse_decimal(values.get(f"lines[{idx}].discount_rate")) or ZERO,
        )
    except InvariantViolationError:
        return None


def _due_date(
    values: dict[str, str | None], issue_date: date | None, default_terms: int | None
) -> date | None:
    explicit = parse_date(values.get("payment.due_date"))
    if explicit or issue_date is None:
        return explicit
    terms = parse_decimal(values.get("payment.terms_days"))
    days = int(terms) if terms is not None else default_terms
    return issue_date + timedelta(days=days) if days is not None else None
