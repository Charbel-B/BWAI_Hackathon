"""Calibration déterministe de la confiance, filtrage du contrat et validation financière."""

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

from invoicing.domain.errors import InvariantViolationError
from invoicing.domain.extraction import ExtractedField, FieldStatus
from invoicing.extraction.anchoring import find_text_anchor, is_value_grounded_in_raw_text
from invoicing.extraction.normalization import normalize_field_value

_STATIC_ALLOWED_FIELDS = frozenset(
    {
        "customer.name",
        "customer.tax_id",
        "document.reference",
        "document.date",
        "discount.global_rate",
        "payment.terms_days",
        "payment.due_date",
        "totals.net",
        "totals.vat",
        "totals.gross",
    }
)
_RE_ALLOWED_LINE_FIELD = re.compile(
    r"^lines\[(?P<idx>\d+)\]\.(?P<attr>label|quantity|unit|unit_price|discount_rate)$"
)
_REQUIRED_LINE_ATTRS = ("label", "quantity", "unit_price")
_DISCOUNT_FIELDS = ("discount.global_rate",)


@dataclass(frozen=True, slots=True)
class CalibrationPolicy:
    """Seuil de revue et plafonds de confiance. Chaque plafond doit rester sous le seuil.

    Un plafond égal ou supérieur au seuil ne forcerait plus la revue humaine : la
    construction est refusée plutôt que de produire une validation silencieuse.
    """

    review_threshold: float = 0.85
    ambiguous_cap: float = 0.50
    ungrounded_cap: float = 0.40
    invalid_format_cap: float = 0.35
    catalog_partial_cap: float = 0.75
    catalog_unknown_cap: float = 0.70
    price_deviation_cap: float = 0.75
    total_mismatch_cap: float = 0.70
    default_model_confidence: float = 0.70
    price_deviation_limit: Decimal = Decimal("0.20")
    catalog_high_similarity: float = 0.88
    catalog_low_similarity: float = 0.68

    def __post_init__(self) -> None:
        caps = {
            "ambiguous_cap": self.ambiguous_cap,
            "ungrounded_cap": self.ungrounded_cap,
            "invalid_format_cap": self.invalid_format_cap,
            "catalog_partial_cap": self.catalog_partial_cap,
            "catalog_unknown_cap": self.catalog_unknown_cap,
            "price_deviation_cap": self.price_deviation_cap,
            "total_mismatch_cap": self.total_mismatch_cap,
            "default_model_confidence": self.default_model_confidence,
        }
        for name, value in caps.items():
            if not 0 <= value < self.review_threshold:
                msg = f"{name}={value} doit être dans [0, seuil={self.review_threshold}["
                raise InvariantViolationError(msg)
        if not Decimal(0) < self.price_deviation_limit < Decimal(1):
            raise InvariantViolationError("price_deviation_limit doit être dans ]0, 1[")


DEFAULT_POLICY = CalibrationPolicy()


@dataclass(frozen=True, slots=True)
class CatalogHint:
    """Référentiels connus (clients, IFU, articles et tarifs HT) pour la validation croisée."""

    customer_names: tuple[str, ...] = ()
    tax_ids: tuple[str, ...] = ()
    item_labels: tuple[str, ...] = ()
    item_prices: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class RawFieldCandidate:
    """Proposition brute d'un extracteur avant vérification et ancrage."""

    name: str
    status: FieldStatus
    raw_value: str | None = None
    raw_text: str | None = None
    base_confidence: float | None = None
    hint_start: int = 0


def is_contract_field_name(name: str) -> bool:
    """Vérifie que ``name`` appartient à la liste fermée de ``champ-extrait.md``."""
    return name in _STATIC_ALLOWED_FIELDS or bool(_RE_ALLOWED_LINE_FIELD.match(name))


def is_local_extraction_sufficient(fields: Sequence[ExtractedField]) -> bool:
    """Vrai si tous les champs obligatoires de toutes les lignes sont trouvés et non ambigus.

    Une ambiguïté sur une remise est une décision humaine, elle ne déclenche pas l'escalade.
    """
    by_name = {f.name: f for f in fields}
    required = ["customer.name", "document.date"]
    for idx in _collect_line_indices(fields) or [0]:
        required.extend(f"lines[{idx}].{attr}" for attr in _REQUIRED_LINE_ATTRS)
    for name in required:
        field = by_name.get(name)
        if field is None or field.status is not FieldStatus.FOUND or field.value is None:
            return False
    return not any(
        f.status is FieldStatus.AMBIGUOUS and f.name.startswith("lines[") for f in fields
    )


def verify_and_build_field(
    candidate: RawFieldCandidate,
    source_text: str,
    catalog: CatalogHint | None = None,
    policy: CalibrationPolicy = DEFAULT_POLICY,
) -> ExtractedField:
    """Vérifie l'ancrage, normalise la valeur et calibre la confiance d'un champ."""
    if candidate.status is FieldStatus.MISSING:
        return _build_missing_field(candidate.name)

    base = _clamp_confidence(candidate.base_confidence, policy)
    anchor = find_text_anchor(source_text, candidate.raw_text, candidate.hint_start)

    if candidate.status is FieldStatus.AMBIGUOUS:
        raw_slice = source_text[anchor.start : anchor.end] if anchor else candidate.raw_text
        return ExtractedField(
            name=candidate.name,
            status=FieldStatus.AMBIGUOUS,
            value=normalize_field_value(candidate.name, candidate.raw_value),
            raw_text=raw_slice,
            confidence=round(min(base, policy.ambiguous_cap), 4),
            anchor=anchor,
        )

    if anchor is None:
        return _build_missing_field(candidate.name)

    exact_raw = source_text[anchor.start : anchor.end]
    normalized = normalize_field_value(candidate.name, candidate.raw_value or exact_raw)
    if normalized is None:
        return ExtractedField(
            name=candidate.name,
            status=FieldStatus.AMBIGUOUS,
            value=None,
            raw_text=exact_raw,
            confidence=round(min(base, policy.invalid_format_cap), 4),
            anchor=anchor,
        )

    grounded = is_value_grounded_in_raw_text(candidate.name, normalized, exact_raw)
    grounding_cap = 1.0 if grounded else policy.ungrounded_cap
    catalog_cap = _compute_catalog_ceiling(candidate.name, normalized, catalog, policy)
    return ExtractedField(
        name=candidate.name,
        status=FieldStatus.FOUND,
        value=normalized,
        raw_text=exact_raw,
        confidence=round(min(base, grounding_cap, catalog_cap), 4),
        anchor=anchor,
    )


def finalize_extracted_fields(
    fields: Sequence[ExtractedField],
    catalog: CatalogHint | None = None,
    policy: CalibrationPolicy = DEFAULT_POLICY,
) -> list[ExtractedField]:
    """Filtre le hors-contrat, fusionne les doublons, complète les obligatoires, croise les prix."""
    deduped: dict[str, ExtractedField] = {}
    for f in fields:
        if is_contract_field_name(f.name):
            deduped[f.name] = _merge_duplicate(deduped.get(f.name), f, policy)

    for req in ("customer.name", "document.date"):
        deduped.setdefault(req, _build_missing_field(req))

    for idx in _collect_line_indices(tuple(deduped.values())) or [0]:
        for attr in _REQUIRED_LINE_ATTRS:
            key = f"lines[{idx}].{attr}"
            deduped.setdefault(key, _build_missing_field(key))

    return apply_financial_cross_validation(tuple(deduped.values()), catalog, policy)


def _merge_duplicate(
    existing: ExtractedField | None,
    new: ExtractedField,
    policy: CalibrationPolicy,
) -> ExtractedField:
    """Deux valeurs différentes pour un même champ : ambiguïté, jamais un choix silencieux."""
    if existing is None or existing.status is FieldStatus.MISSING:
        return new
    if new.status is FieldStatus.MISSING:
        return existing
    if existing.value == new.value and existing.status is new.status:
        return existing
    confidence = min(existing.confidence or 1.0, new.confidence or 1.0, policy.ambiguous_cap)
    return ExtractedField(
        existing.name,
        FieldStatus.AMBIGUOUS,
        None,
        existing.raw_text,
        round(confidence, 4),
        existing.anchor,
    )


def apply_financial_cross_validation(
    fields: Sequence[ExtractedField],
    catalog: CatalogHint | None = None,
    policy: CalibrationPolicy = DEFAULT_POLICY,
) -> list[ExtractedField]:
    """Plafonne la confiance des prix hors tarif et des totaux incohérents avec les lignes.

    Le contrôle du total est ignoré dès qu'une remise figure sur la pièce : le recalcul
    complet (remises comprises) appartient au moteur métier.
    """
    by_name = {f.name: f for f in fields}
    line_indices = _collect_line_indices(fields)
    capped: dict[str, float] = {}
    expected_net_sum = Decimal(0)
    has_all_lines = bool(line_indices)

    for idx in line_indices:
        label_field = by_name.get(f"lines[{idx}].label")
        qty_field = by_name.get(f"lines[{idx}].quantity")
        price_field = by_name.get(f"lines[{idx}].unit_price")

        if price_field and price_field.status is FieldStatus.FOUND and price_field.value:
            price_cap = _price_ceiling(
                label_field.value if label_field else None, price_field.value, catalog, policy
            )
            if price_field.confidence is not None and price_cap < price_field.confidence:
                capped[price_field.name] = round(price_cap, 4)

        line_total = _compute_line_product(qty_field, price_field)
        if line_total is None:
            has_all_lines = False
        else:
            expected_net_sum += line_total

    has_discount = any(
        name in by_name and by_name[name].status is not FieldStatus.MISSING
        for name in _DISCOUNT_FIELDS
    ) or any(f.name.endswith(".discount_rate") for f in fields)
    net_field = by_name.get("totals.net")
    if (
        has_all_lines
        and not has_discount
        and net_field
        and net_field.status is FieldStatus.FOUND
        and net_field.value
        and net_field.confidence is not None
    ):
        net_val = _safe_decimal(net_field.value)
        if net_val is not None and net_val != expected_net_sum:
            capped["totals.net"] = round(min(net_field.confidence, policy.total_mismatch_cap), 4)

    return [replace(f, confidence=capped[f.name]) if f.name in capped else f for f in fields]


def _collect_line_indices(fields: Sequence[ExtractedField]) -> list[int]:
    indices: set[int] = set()
    for f in fields:
        match = _RE_ALLOWED_LINE_FIELD.match(f.name)
        if match:
            indices.add(int(match.group("idx")))
    return sorted(indices)


def _price_ceiling(
    label_value: str | None,
    price_value: str,
    catalog: CatalogHint | None,
    policy: CalibrationPolicy,
) -> float:
    if catalog is None or not catalog.item_prices or not label_value:
        return 1.0
    ref_price = _find_reference_price(label_value, catalog.item_prices, policy)
    extracted_dec = _safe_decimal(price_value)
    ref_dec = _safe_decimal(ref_price) if ref_price is not None else None
    if extracted_dec is None or ref_dec is None or ref_dec <= 0:
        return policy.price_deviation_cap
    if abs(extracted_dec - ref_dec) / ref_dec > policy.price_deviation_limit:
        return policy.price_deviation_cap
    return 1.0


def _find_reference_price(
    label_value: str,
    item_prices: tuple[tuple[str, str], ...],
    policy: CalibrationPolicy,
) -> str | None:
    target_low = label_value.lower()
    best_ratio = 0.0
    best_price: str | None = None
    for ref_label, ref_price in item_prices:
        ratio = SequenceMatcher(None, target_low, ref_label.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_price = ref_price
    return best_price if best_ratio >= policy.catalog_high_similarity else None


def _compute_line_product(
    qty_field: ExtractedField | None,
    price_field: ExtractedField | None,
) -> Decimal | None:
    if (
        qty_field is None
        or price_field is None
        or qty_field.status is not FieldStatus.FOUND
        or price_field.status is not FieldStatus.FOUND
        or qty_field.value is None
        or price_field.value is None
    ):
        return None
    qty = _safe_decimal(qty_field.value)
    price = _safe_decimal(price_field.value)
    if qty is None or price is None:
        return None
    return qty * price


def _safe_decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _build_missing_field(name: str) -> ExtractedField:
    return ExtractedField(name, FieldStatus.MISSING, None, None, None, None)


def _clamp_confidence(value: float | None, policy: CalibrationPolicy) -> float:
    if value is None:
        return policy.default_model_confidence
    return max(0.0, min(1.0, value))


def _compute_catalog_ceiling(
    field_name: str,
    normalized_value: str,
    catalog: CatalogHint | None,
    policy: CalibrationPolicy,
) -> float:
    if catalog is None:
        return 1.0
    if field_name == "customer.tax_id" and catalog.tax_ids:
        return 1.0 if normalized_value in catalog.tax_ids else policy.catalog_unknown_cap
    if field_name == "customer.name" and catalog.customer_names:
        return _similarity_ceiling(normalized_value, catalog.customer_names, policy)
    if field_name.endswith(".label") and catalog.item_labels:
        return _similarity_ceiling(normalized_value, catalog.item_labels, policy)
    return 1.0


def _similarity_ceiling(
    target: str,
    references: tuple[str, ...],
    policy: CalibrationPolicy,
) -> float:
    target_low = target.lower()
    best = max(SequenceMatcher(None, target_low, ref.lower()).ratio() for ref in references)
    if best >= policy.catalog_high_similarity:
        return 1.0
    if best >= policy.catalog_low_similarity:
        return policy.catalog_partial_cap
    return policy.catalog_unknown_cap
