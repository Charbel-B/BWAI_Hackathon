"""Contrôles d'un brouillon contre la pièce et les référentiels.

Couvre 8 des 10 codes du contrat. QUANTITY_MISMATCH et DOCUMENT_INCONSISTENCY portent sur
plusieurs pièces d'un même dossier, que ce prototype ne regroupe pas encore.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from invoicing.domain.drafting import (
    REQUIRED_HEADER_FIELDS,
    REQUIRED_LINE_ATTRS,
    effective_values,
    line_indexes,
    parse_date,
    parse_decimal,
)
from invoicing.domain.extraction import ExtractedField, FieldStatus, ReviewState
from invoicing.domain.invoice import Anomaly, DraftContent, Severity, Totals
from invoicing.domain.referentials import Referentials

HUNDRED = Decimal(100)


@dataclass(frozen=True, slots=True)
class ControlRules:
    """Seuils et gravités lus dans config/controles.yaml et config/extraction.yaml."""

    unusual_price_percent: Decimal
    high_amount_gross: Decimal
    review_threshold: float
    severities: Mapping[str, Severity]

    def severity(self, code: str) -> Severity:
        """Gravité configurée ; bloquante par défaut, par prudence."""
        return self.severities.get(code, Severity.BLOCKING)


@dataclass(frozen=True, slots=True)
class DraftUnderReview:
    """Ce que les contrôles examinent : le brouillon calculé et les champs de sa pièce."""

    content: DraftContent
    totals: Totals
    fields: Sequence[ExtractedField]
    duplicate_of: str | None = None


def check_draft(
    draft: DraftUnderReview, referentials: Referentials, rules: ControlRules
) -> tuple[Anomaly, ...]:
    """Liste les anomalies. L'identifiant code:champ reste stable d'un recalcul à l'autre."""
    content, totals, fields, duplicate_of = (
        draft.content,
        draft.totals,
        draft.fields,
        draft.duplicate_of,
    )
    found: list[tuple[str, str | None, str]] = []
    found += _field_checks(fields, rules)
    if content.customer_id is None and content.customer_name:
        found.append(
            (
                "UNKNOWN_CUSTOMER",
                "customer.name",
                f"Client « {content.customer_name} » absent du référentiel",
            )
        )
    for idx, line in enumerate(content.lines):
        item = referentials.find_item(line.label)
        if item is None:
            found.append(
                (
                    "UNKNOWN_ITEM",
                    f"lines[{idx}].label",
                    f"Article « {line.label} » absent du référentiel",
                )
            )
        elif (
            item.unit_price_net
            and _deviation(line.unit_price_net, item.unit_price_net) > rules.unusual_price_percent
        ):
            found.append(
                (
                    "UNUSUAL_PRICE",
                    f"lines[{idx}].unit_price",
                    f"Prix {line.unit_price_net} loin du prix de référence {item.unit_price_net}",
                )
            )
    found += _amount_checks(content, totals, rules)
    if duplicate_of:
        found.append(("DUPLICATE_DOCUMENT", None, f"Pièce déjà traitée : {duplicate_of}"))
    return tuple(
        Anomaly(
            id=f"{code}:{field or '-'}",
            code=code,
            severity=rules.severity(code),
            field=field,
            message=message,
        )
        for code, field, message in found
    )


def _field_checks(
    fields: Sequence[ExtractedField], rules: ControlRules
) -> list[tuple[str, str | None, str]]:
    values = effective_values(fields)
    required = [*REQUIRED_HEADER_FIELDS]
    indexes = line_indexes(fields)
    required += [f"lines[{i}].{attr}" for i in indexes for attr in REQUIRED_LINE_ATTRS]
    result: list[tuple[str, str | None, str]] = []
    if not indexes:
        result.append(
            ("MISSING_REQUIRED_FIELD", "lines", "Aucune ligne de facture trouvée dans la pièce")
        )
    for name in required:
        if not _is_readable(name, values.get(name)):
            result.append(
                (
                    "MISSING_REQUIRED_FIELD",
                    name,
                    f"Champ obligatoire « {name} » absent ou illisible",
                )
            )
    for f in fields:
        uncertain = f.status is FieldStatus.AMBIGUOUS or (
            f.confidence is not None and f.confidence < rules.review_threshold
        )
        if uncertain and f.value is not None and f.review.state is ReviewState.PENDING:
            result.append(
                (
                    "LOW_CONFIDENCE",
                    f.name,
                    f"Champ « {f.name} » incertain : à confirmer ou corriger",
                )
            )
    return result


def _is_readable(name: str, value: str | None) -> bool:
    if value is None or not value.strip():
        return False
    if name == "document.date":
        return parse_date(value) is not None
    if name.endswith((".quantity", ".unit_price")):
        number = parse_decimal(value)
        return number is not None and number > 0
    return True


def _amount_checks(
    content: DraftContent, totals: Totals, rules: ControlRules
) -> list[tuple[str, str | None, str]]:
    result: list[tuple[str, str | None, str]] = []
    if content.declared_net is not None and content.declared_net != totals.net_total:
        result.append(
            (
                "AMOUNT_MISMATCH",
                "totals.net",
                f"HT lu {content.declared_net}, HT recalculé {totals.net_total}",
            )
        )
    if content.declared_gross is not None and content.declared_gross != totals.gross_total:
        result.append(
            (
                "AMOUNT_MISMATCH",
                "totals.gross",
                f"TTC lu {content.declared_gross}, TTC recalculé {totals.gross_total}",
            )
        )
    if totals.gross_total > rules.high_amount_gross:
        result.append(
            (
                "HIGH_AMOUNT",
                None,
                f"TTC {totals.gross_total} au-delà du seuil de revue {rules.high_amount_gross}",
            )
        )
    return result


def _deviation(price: Decimal, reference: Decimal) -> Decimal:
    return abs(price - reference) / reference * HUNDRED
