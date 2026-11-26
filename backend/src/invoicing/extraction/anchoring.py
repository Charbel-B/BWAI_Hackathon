"""Ancrage déterministe d'un champ extrait dans le texte de la pièce source.

Les positions de caractères ``[start, end)`` sont toujours calculées en Python
à partir de ``raw_text``, jamais déléguées à un modèle de langage.
"""

import re
from decimal import Decimal, InvalidOperation

from invoicing.domain.extraction import TextAnchor

_RE_DIGITS = re.compile(r"\d+")
_RE_WORDS = re.compile(r"[a-zA-ZÀ-ÿ0-9]{2,}")
_ISO_DATE_PARTS_COUNT = 3


def find_text_anchor(
    source_text: str,
    raw_text: str | None,
    start_from: int = 0,
) -> TextAnchor | None:
    """Localise ``raw_text`` dans ``source_text`` et renvoie son ``TextAnchor``."""
    if not raw_text or not source_text:
        return None
    needle = raw_text.strip()
    if not needle:
        return None

    offset = max(0, start_from)
    exact_pos = source_text.find(needle, offset)
    if exact_pos == -1 and offset > 0:
        exact_pos = source_text.find(needle)
    if exact_pos != -1:
        return TextAnchor(start=exact_pos, end=exact_pos + len(needle))

    lower_source = source_text.lower()
    lower_needle = needle.lower()
    ci_pos = lower_source.find(lower_needle, offset)
    if ci_pos == -1 and offset > 0:
        ci_pos = lower_source.find(lower_needle)
    if ci_pos != -1:
        return TextAnchor(start=ci_pos, end=ci_pos + len(needle))

    return _find_whitespace_tolerant_anchor(source_text, needle)


def _find_whitespace_tolerant_anchor(source_text: str, needle: str) -> TextAnchor | None:
    """Recherche ``needle`` dans ``source_text`` en tolérant les variations d'espaces."""
    parts = [re.escape(part) for part in needle.split() if part]
    if not parts:
        return None
    pattern = re.compile(r"\s+".join(parts), re.IGNORECASE)
    match = pattern.search(source_text)
    if not match:
        return None
    return TextAnchor(start=match.start(), end=match.end())


def is_value_grounded_in_raw_text(
    field_name: str,
    normalized_value: str | None,
    raw_text: str | None,
) -> bool:
    """Vérifie que ``normalized_value`` est bien ancrée dans ``raw_text`` sans calcul inventé."""
    if normalized_value is None or raw_text is None:
        return False
    if field_name in {"document.date", "payment.due_date"}:
        return _is_date_grounded(normalized_value, raw_text)
    if field_name.endswith((".discount_rate", "discount.global_rate")):
        return _is_rate_grounded(normalized_value, raw_text)
    if field_name.endswith(
        (
            ".quantity",
            ".delivered_quantity",
            ".unit_price",
            "totals.net",
            "totals.vat",
            "totals.gross",
        )
    ) or field_name in {"customer.tax_id", "payment.terms_days"}:
        return _is_number_grounded(normalized_value, raw_text)
    return _is_text_grounded(normalized_value, raw_text)


def _is_date_grounded(iso_date: str, raw_text: str) -> bool:
    """Vérifie que l'année et le jour de la date ISO figurent dans ``raw_text``."""
    parts = iso_date.split("-")
    if len(parts) != _ISO_DATE_PARTS_COUNT:
        return False
    year, _month, day = parts
    raw_digits = _RE_DIGITS.findall(raw_text)
    day_int = str(int(day))
    return year in raw_digits and (day in raw_digits or day_int in raw_digits)


def _is_rate_grounded(rate_value: str, raw_text: str) -> bool:
    """Vérifie qu'un taux normalisé (ex. ``0.05``) correspond à ``5%`` dans la source."""
    compact_raw = raw_text.replace(" ", "").replace(",", ".")
    if rate_value in compact_raw:
        return True
    try:
        pct = Decimal(rate_value) * Decimal(100)
    except InvalidOperation:
        return False
    pct_str = str(int(pct)) if pct == pct.to_integral_value() else format(pct.normalize(), "f")
    return pct_str in compact_raw


def _is_number_grounded(number_value: str, raw_text: str) -> bool:
    """Vérifie que les chiffres significatifs du nombre figurent littéralement dans ``raw_text``."""
    value_digits = "".join(_RE_DIGITS.findall(number_value))
    raw_digits = "".join(_RE_DIGITS.findall(raw_text))
    if not value_digits or not raw_digits:
        return False
    return value_digits in raw_digits


def _is_text_grounded(text_value: str, raw_text: str) -> bool:
    """Vérifie qu'au moins un mot significatif de ``text_value`` apparaît dans ``raw_text``."""
    raw_lower = raw_text.lower()
    words = [w.lower() for w in _RE_WORDS.findall(text_value)]
    if not words:
        return text_value.strip().lower() in raw_lower
    return any(word in raw_lower for word in words)
