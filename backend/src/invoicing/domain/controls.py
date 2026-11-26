"""Contrôles d'un brouillon contre la pièce, le dossier et les référentiels.

Couvre les 10 codes d'anomalie de ``docs/contrats/modele-de-domaine.md``.
Toutes les gravités et tous les seuils viennent de ``ControlRules`` (jamais en dur).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
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
from invoicing.domain.field_names import human_field
from invoicing.domain.invoice import Anomaly, DraftContent, Severity, Totals
from invoicing.domain.referentials import Item, Referentials

HUNDRED = Decimal(100)
_QUOTE_KINDS = frozenset({"devis", "quote"})
_DELIVERY_KINDS = frozenset({"bon de livraison", "bl", "livraison", "delivery_note"})


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
class RelatedDocument:
    """Autre pièce d'un même dossier (ex. bon de livraison, devis) comparée au brouillon."""

    kind: str
    customer_name: str | None = None
    reference: str | None = None
    issue_date: date | None = None


@dataclass(frozen=True, slots=True)
class DraftUnderReview:
    """Ce que les contrôles examinent : le brouillon calculé, les champs et les pièces liées."""

    content: DraftContent
    totals: Totals
    fields: Sequence[ExtractedField]
    duplicate_of: str | None = None
    delivered_quantities: Mapping[int, Decimal] = field(default_factory=dict)
    related_documents: Sequence[RelatedDocument] = ()


def check_draft(
    draft: DraftUnderReview, referentials: Referentials, rules: ControlRules
) -> tuple[Anomaly, ...]:
    """Liste les anomalies dédoublonnées par identifiant stable ``code:champ``."""
    found: list[tuple[str, str | None, str]] = [
        *_field_checks(draft.fields, rules),
        *_referential_checks(draft.content, referentials, rules),
        *_quantity_checks(draft.content, draft.delivered_quantities),
        *_dossier_checks(draft.content, draft.related_documents),
        *_amount_checks(draft.content, draft.totals, rules),
    ]
    if draft.duplicate_of:
        found.append(("DUPLICATE_DOCUMENT", None, f"Pièce déjà traitée : {draft.duplicate_of}"))

    unique: dict[str, Anomaly] = {}
    for code, field_name, message in found:
        anomaly_id = f"{code}:{field_name or '-'}"
        if anomaly_id not in unique:
            unique[anomaly_id] = Anomaly(
                id=anomaly_id,
                code=code,
                severity=rules.severity(code),
                field=field_name,
                message=message,
            )
    return tuple(unique.values())


def _referential_checks(
    content: DraftContent, referentials: Referentials, rules: ControlRules
) -> list[tuple[str, str | None, str]]:
    found: list[tuple[str, str | None, str]] = []
    if content.customer_id is None and content.customer_name:
        found.append(
            (
                "UNKNOWN_CUSTOMER",
                "customer.name",
                f"Client « {content.customer_name} » absent du référentiel",
            )
        )
    for idx, line in enumerate(content.lines):
        item = _resolve_item(referentials, line.item_id, line.label)
        if item is None:
            found.append(
                (
                    "UNKNOWN_ITEM",
                    f"lines[{idx}].label",
                    f"Article « {line.label} » absent du référentiel",
                )
            )
        elif (
            item.unit_price_net > 0
            and _deviation(line.unit_price_net, item.unit_price_net) > rules.unusual_price_percent
        ):
            found.append(
                (
                    "UNUSUAL_PRICE",
                    f"lines[{idx}].unit_price",
                    f"Prix {line.unit_price_net} loin du prix de référence {item.unit_price_net}",
                )
            )
    return found


def _resolve_item(referentials: Referentials, item_id: str | None, label: str) -> Item | None:
    if item_id:
        match = next((it for it in referentials.items if it.id == item_id), None)
        if match is not None:
            return match
    return referentials.find_item(label)


def _quantity_checks(
    content: DraftContent, delivered_quantities: Mapping[int, Decimal]
) -> list[tuple[str, str | None, str]]:
    found: list[tuple[str, str | None, str]] = []
    for idx, line in enumerate(content.lines):
        delivered = delivered_quantities.get(idx)
        if delivered is not None and delivered != line.quantity:
            found.append(
                (
                    "QUANTITY_MISMATCH",
                    f"lines[{idx}].quantity",
                    f"Quantité commandée {line.quantity} différente de la quantité livrée "
                    f"{delivered}",
                )
            )
    for idx, delivered in sorted(delivered_quantities.items()):
        if idx >= len(content.lines) and delivered > 0:
            found.append(
                (
                    "QUANTITY_MISMATCH",
                    f"lines[{idx}].quantity",
                    f"Quantité livrée {delivered} sans ligne commandée correspondante",
                )
            )
    return found


def _dossier_checks(
    content: DraftContent, related_documents: Sequence[RelatedDocument]
) -> list[tuple[str, str | None, str]]:
    found: list[tuple[str, str | None, str]] = []
    for doc in related_documents:
        found.extend(_check_related_document(content, doc))
    return found


def _check_related_document(
    content: DraftContent, doc: RelatedDocument
) -> list[tuple[str, str | None, str]]:
    found: list[tuple[str, str | None, str]] = []
    if (
        content.customer_name
        and doc.customer_name
        and _norm(content.customer_name) != _norm(doc.customer_name)
    ):
        found.append(
            (
                "DOCUMENT_INCONSISTENCY",
                "customer.name",
                f"Client contradictoire avec {doc.kind} : "
                f"« {content.customer_name} » vs « {doc.customer_name} »",
            )
        )
    if content.reference and doc.reference and _norm(content.reference) != _norm(doc.reference):
        found.append(
            (
                "DOCUMENT_INCONSISTENCY",
                "document.reference",
                f"Référence contradictoire avec {doc.kind} : "
                f"« {content.reference} » vs « {doc.reference} »",
            )
        )
    if content.issue_date and doc.issue_date:
        norm_kind = _norm(doc.kind)
        if norm_kind in _QUOTE_KINDS and doc.issue_date > content.issue_date:
            found.append(
                (
                    "DOCUMENT_INCONSISTENCY",
                    "document.date",
                    f"Date du {doc.kind} ({doc.issue_date}) postérieure à la pièce "
                    f"({content.issue_date})",
                )
            )
        elif norm_kind in _DELIVERY_KINDS and doc.issue_date < content.issue_date:
            found.append(
                (
                    "DOCUMENT_INCONSISTENCY",
                    "document.date",
                    f"Date de {doc.kind} ({doc.issue_date}) antérieure à la pièce "
                    f"({content.issue_date})",
                )
            )
    return found


def _field_checks(
    fields: Sequence[ExtractedField], rules: ControlRules
) -> list[tuple[str, str | None, str]]:
    values = effective_values(fields)
    indexes = line_indexes(fields)
    required = [*REQUIRED_HEADER_FIELDS]
    required += [f"lines[{i}].{attr}" for i in indexes for attr in REQUIRED_LINE_ATTRS]

    result: list[tuple[str, str | None, str]] = []
    missing_names: set[str] = set()
    if not indexes:
        result.append(
            ("MISSING_REQUIRED_FIELD", "lines", "Aucune ligne de facture trouvée dans la pièce")
        )
    for name in required:
        if not _is_readable(name, values.get(name)):
            missing_names.add(name)
            result.append(
                (
                    "MISSING_REQUIRED_FIELD",
                    name,
                    f"Champ obligatoire « {human_field(name)} » absent ou illisible",
                )
            )
    for f in fields:
        if f.name in missing_names or f.review.state is not ReviewState.PENDING:
            continue
        is_ambiguous = f.status is FieldStatus.AMBIGUOUS
        is_low_conf = (
            f.confidence is not None
            and f.confidence < rules.review_threshold
            and f.value is not None
        )
        if is_ambiguous or is_low_conf:
            result.append(
                (
                    "LOW_CONFIDENCE",
                    f.name,
                    f"Champ « {human_field(f.name)} » incertain : à confirmer ou corriger",
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


def _norm(value: str) -> str:
    return " ".join(value.strip().lower().split())
