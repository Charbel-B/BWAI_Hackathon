"""Calibration déterministe de la confiance et vérification des champs extraits.

La confiance finale applique la règle du veto (``min``) entre :
1. le score brut proposé par l'extracteur ;
2. le plafond d'ancrage littéral dans la pièce source ;
3. le plafond de validité du format après normalisation ;
4. le plafond de correspondance avec le référentiel (si fourni).
"""

from dataclasses import dataclass
from difflib import SequenceMatcher

from invoicing.domain.extraction import ExtractedField, FieldStatus
from invoicing.extraction.anchoring import find_text_anchor, is_value_grounded_in_raw_text
from invoicing.extraction.normalization import normalize_field_value

AMBIGUOUS_CONFIDENCE_CAP = 0.50
UNGROUNDED_VALUE_CAP = 0.40
INVALID_FORMAT_CAP = 0.35
CATALOG_PARTIAL_MATCH_CAP = 0.75
CATALOG_UNKNOWN_MATCH_CAP = 0.70
CATALOG_HIGH_SIMILARITY = 0.88
CATALOG_LOW_SIMILARITY = 0.68
DEFAULT_BASE_CONFIDENCE = 0.90


@dataclass(frozen=True, slots=True)
class CatalogHint:
    """Référentiels connus (noms de clients, IFU, désignations d'articles) pour calibrer."""

    customer_names: tuple[str, ...] = ()
    tax_ids: tuple[str, ...] = ()
    item_labels: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RawFieldCandidate:
    """Proposition brute d'un extracteur avant vérification et ancrage."""

    name: str
    status: FieldStatus
    raw_value: str | None = None
    raw_text: str | None = None
    base_confidence: float | None = None


def verify_and_build_field(
    candidate: RawFieldCandidate,
    source_text: str,
    catalog: CatalogHint | None = None,
) -> ExtractedField:
    """Vérifie l'ancrage, normalise la valeur et calibre la confiance d'un champ."""
    if candidate.status is FieldStatus.MISSING:
        return _build_missing_field(candidate.name)

    base = _clamp_confidence(candidate.base_confidence)
    anchor = find_text_anchor(source_text, candidate.raw_text)

    if candidate.status is FieldStatus.AMBIGUOUS:
        raw_slice = source_text[anchor.start : anchor.end] if anchor else candidate.raw_text
        norm_val = normalize_field_value(candidate.name, candidate.raw_value)
        return ExtractedField(
            name=candidate.name,
            status=FieldStatus.AMBIGUOUS,
            value=norm_val,
            raw_text=raw_slice,
            confidence=round(min(base, AMBIGUOUS_CONFIDENCE_CAP), 4),
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
            confidence=round(min(base, INVALID_FORMAT_CAP), 4),
            anchor=anchor,
        )

    grounding_cap = (
        1.0
        if is_value_grounded_in_raw_text(candidate.name, normalized, exact_raw)
        else UNGROUNDED_VALUE_CAP
    )
    catalog_cap = _compute_catalog_ceiling(candidate.name, normalized, catalog)
    final_confidence = round(min(base, grounding_cap, catalog_cap), 4)

    return ExtractedField(
        name=candidate.name,
        status=FieldStatus.FOUND,
        value=normalized,
        raw_text=exact_raw,
        confidence=final_confidence,
        anchor=anchor,
    )


def _build_missing_field(name: str) -> ExtractedField:
    """Construit un champ absent conforme à l'invariant du domaine."""
    return ExtractedField(
        name=name,
        status=FieldStatus.MISSING,
        value=None,
        raw_text=None,
        confidence=None,
        anchor=None,
    )


def _clamp_confidence(value: float | None) -> float:
    """Ramène un score brut dans l'intervalle ``[0.0, 1.0]``."""
    if value is None:
        return DEFAULT_BASE_CONFIDENCE
    return max(0.0, min(1.0, value))


def _compute_catalog_ceiling(
    field_name: str,
    normalized_value: str,
    catalog: CatalogHint | None,
) -> float:
    """Plafonne la confiance si une valeur diffère légèrement du référentiel."""
    if catalog is None:
        return 1.0
    if field_name == "customer.tax_id" and catalog.tax_ids:
        return 1.0 if normalized_value in catalog.tax_ids else CATALOG_UNKNOWN_MATCH_CAP
    if field_name == "customer.name" and catalog.customer_names:
        return _similarity_ceiling(normalized_value, catalog.customer_names)
    if field_name.endswith(".label") and catalog.item_labels:
        return _similarity_ceiling(normalized_value, catalog.item_labels)
    return 1.0


def _similarity_ceiling(target: str, references: tuple[str, ...]) -> float:
    """Évalue la meilleure similarité entre ``target`` et ``references``."""
    target_low = target.lower()
    best = max(SequenceMatcher(None, target_low, ref.lower()).ratio() for ref in references)
    if best >= CATALOG_HIGH_SIMILARITY:
        return 1.0
    if best >= CATALOG_LOW_SIMILARITY:
        return CATALOG_PARTIAL_MATCH_CAP
    return CATALOG_UNKNOWN_MATCH_CAP
