"""Normalisation déterministe des valeurs extraites d'une pièce source.

Toutes les valeurs normalisées sont des chaînes de caractères conformes à
``docs/contrats/champ-extrait.md``. Aucun ``float`` n'est utilisé pour les
montants, quantités ou taux : seule ``decimal.Decimal`` est employée.
"""

import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

_FRENCH_MONTHS: dict[str, int] = {
    "janvier": 1,
    "fevrier": 2,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
    "décembre": 12,
}

_RE_ISO_DATE = re.compile(r"\b(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})\b")
_RE_DMY_DATE = re.compile(r"\b(?P<d>\d{1,2})[/-](?P<m>\d{1,2})[/-](?P<y>\d{4})\b")
_RE_TEXT_DATE = re.compile(
    r"\b(?P<d>\d{1,2})\s+(?P<month>[a-zéû]+)\s+(?P<y>\d{4})\b",
    re.IGNORECASE,
)
_RE_TAX_ID = re.compile(r"(?<!\d)(\d{13})(?!\d)")
_RE_THOUSANDS_DOT = re.compile(r"^[+-]?\d{1,3}(?:\.\d{3})+$")
_RE_THOUSANDS_COMMA = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})+$")
_RE_NUMERIC_TOKEN = re.compile(r"[+-]?\d+(?:[.,\s\u00a0\u202f]\d+)*")
_RE_INT_TOKEN = re.compile(r"\b(\d+)\b")

_DATE_FIELDS = frozenset({"document.date", "payment.due_date"})
_RATE_SUFFIXES = (".discount_rate", "discount.global_rate")
_DECIMAL_SUFFIXES = (".quantity", ".unit_price", "totals.net", "totals.vat", "totals.gross")


def normalize_text(raw: str) -> str | None:
    """Nettoie une chaîne texte en supprimant les espaces superflus."""
    cleaned = " ".join(raw.strip().split())
    return cleaned if cleaned else None


def normalize_tax_id(raw: str) -> str | None:
    """Extrait et valide un IFU de 13 chiffres exacts."""
    compact = re.sub(r"[\s.-]", "", raw.strip())
    match = _RE_TAX_ID.search(compact)
    return match.group(1) if match else None


def normalize_date(raw: str) -> str | None:
    """Normalise une date en format ISO ``AAAA-MM-JJ`` si elle est valide au calendrier."""
    text = raw.strip()
    iso_match = _RE_ISO_DATE.search(text)
    if iso_match:
        return _build_iso_date(
            int(iso_match.group("y")),
            int(iso_match.group("m")),
            int(iso_match.group("d")),
        )
    dmy_match = _RE_DMY_DATE.search(text)
    if dmy_match:
        return _build_iso_date(
            int(dmy_match.group("y")),
            int(dmy_match.group("m")),
            int(dmy_match.group("d")),
        )
    text_match = _RE_TEXT_DATE.search(text)
    if text_match:
        month = _FRENCH_MONTHS.get(text_match.group("month").lower())
        if month is not None:
            return _build_iso_date(
                int(text_match.group("y")),
                month,
                int(text_match.group("d")),
            )
    return None


def _build_iso_date(year: int, month: int, day: int) -> str | None:
    """Vérifie l'existence calendaire d'une date et la formate en ISO 8601."""
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def normalize_decimal(raw: str) -> str | None:
    """Normalise un montant FCFA ou une quantité en chaîne décimale avec point."""
    cleaned = raw.strip()
    for space in ("\u00a0", "\u202f", "\u2009"):
        cleaned = cleaned.replace(space, " ")
    match = _RE_NUMERIC_TOKEN.search(cleaned)
    if not match:
        return None
    token = match.group(0).replace(" ", "")
    if _RE_THOUSANDS_DOT.match(token):
        token = token.replace(".", "")
    elif _RE_THOUSANDS_COMMA.match(token):
        token = token.replace(",", "")
    else:
        token = token.replace(",", ".")
    try:
        value = Decimal(token)
    except InvalidOperation:
        return None
    if value < 0 or not value.is_finite():
        return None
    return _format_decimal(value)


def normalize_rate(raw: str) -> str | None:
    """Normalise un taux de remise en décimal entre 0 et 1 (ex. ``5 %`` -> ``0.05``)."""
    has_percent = "%" in raw
    decimal_str = normalize_decimal(raw)
    if decimal_str is None:
        return None
    value = Decimal(decimal_str)
    if has_percent or value > Decimal(1):
        value = value / Decimal(100)
    if not (Decimal(0) <= value <= Decimal(1)):
        return None
    return _format_decimal(value)


def normalize_int(raw: str) -> str | None:
    """Normalise un entier positif (ex. délai de paiement en jours)."""
    match = _RE_INT_TOKEN.search(raw.strip())
    if not match:
        return None
    return str(int(match.group(1)))


def normalize_field_value(field_name: str, raw: str | None) -> str | None:
    """Normalise la valeur brute d'un champ selon son nom dans le contrat."""
    if raw is None:
        return None
    normalizer = _select_normalizer(field_name)
    return normalizer(raw)


def _select_normalizer(field_name: str) -> Callable[[str], str | None]:
    """Sélectionne la fonction de normalisation adaptée au nom du champ."""
    normalizer: Callable[[str], str | None] = normalize_text
    if field_name == "customer.tax_id":
        normalizer = normalize_tax_id
    elif field_name in _DATE_FIELDS:
        normalizer = normalize_date
    elif field_name == "payment.terms_days":
        normalizer = normalize_int
    elif field_name.endswith(_RATE_SUFFIXES):
        normalizer = normalize_rate
    elif field_name.endswith(_DECIMAL_SUFFIXES):
        normalizer = normalize_decimal
    return normalizer


def _format_decimal(value: Decimal) -> str:
    """Formate un Decimal sans exposant ni zéros décimaux inutiles."""
    normalized = value.normalize()
    if normalized == normalized.to_integral_value():
        return str(int(normalized))
    return format(normalized, "f").rstrip("0").rstrip(".")
