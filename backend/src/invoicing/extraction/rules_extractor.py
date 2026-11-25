"""Extracteur local déterministe par règles (référence sans IA et repli hors-ligne).

Cet extracteur n'utilise aucun modèle de langage : il applique des expressions
régulières sur le texte de la pièce puis passe chaque candidat par le
vérificateur d'ancrage et de confiance.
"""

import re
from collections.abc import Sequence

from invoicing.domain.extraction import ExtractedField, FieldStatus
from invoicing.extraction.confidence import (
    CatalogHint,
    RawFieldCandidate,
    verify_and_build_field,
)

_RE_CUSTOMER = re.compile(
    r"(?:client|entreprise|soci[eé]t[eé]|destinataire|de la part de|ici|c'est)\s*[:=-]?\s*"
    r"(?P<name>[A-ZÀ-Ÿ][A-Za-zÀ-ÿ0-9 '&.-]{2,60})",
    re.IGNORECASE,
)
_RE_TAX_ID = re.compile(r"(?:ifu|n[°o]?\s*ifu)?\s*[:=-]?\s*(?<!\d)(?P<ifu>\d{13})(?!\d)", re.I)
_RE_REFERENCE = re.compile(
    r"(?:devis|commande|bon de commande|r[eé]f(?:[eé]rence)?|bc|cmd|dev)\s*"
    r"(?:n[°o]?)?\s*[:#=-]?\s*(?P<ref>[A-Z0-9]{2,6}(?:-[A-Z0-9]{2,10})+)",
    re.IGNORECASE,
)
_RE_DATE = re.compile(
    r"(?P<date>\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b|"
    r"\b\d{1,2}\s+(?:janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|"
    r"septembre|octobre|novembre|d[eé]cembre)\s+\d{4}\b)",
    re.IGNORECASE,
)
_RE_GLOBAL_DISCOUNT = re.compile(
    r"remise(?:\s+globale|\s+fid[eé]lit[eé]|\s+commerciale|\s+cash)?\s*(?:de|:)?\s*"
    r"(?P<rate>\d+(?:[.,]\d+)?\s*%)",
    re.IGNORECASE,
)
_RE_TERMS_DAYS = re.compile(
    r"(?:d[eé]lai(?:\s+de\s+paiement)?|paiement(?:\s+[aà])?|r[eè]glement(?:\s+[aà])?)\s*[:=-]?\s*"
    r"(?P<days>\d{1,3})\s*jours?",
    re.IGNORECASE,
)
_RE_TOTAL_NET = re.compile(
    r"total\s+ht\s*[:=-]?\s*(?P<amount>\d[\d\s.\u00a0]*(?:fcfa|f\b)?)",
    re.IGNORECASE,
)
_RE_TOTAL_VAT = re.compile(
    r"(?:montant\s+)?tva(?:\s+18\s*%)?\s*[:=-]?\s*(?P<amount>\d[\d\s.\u00a0]*(?:fcfa|f\b)?)",
    re.IGNORECASE,
)
_RE_TOTAL_GROSS = re.compile(
    r"total(?:\s+ttc)?\s*[:=-]?\s*(?P<amount>\d[\d\s.\u00a0]*(?:fcfa|f\b)?)",
    re.IGNORECASE,
)
_RE_STRUCTURED_LINE = re.compile(
    r"^\s*[-*•]?\s*(?P<qty>\d+(?:[.,]\d+)?)\s+"
    r"(?:(?P<unit>sacs?|barres?|camions?|m3|m2|m|unit[eé]s?|feuilles?|seaux?|pots?|"
    r"rouleaux?|cartons?|lots?|citernes?|voyages?|heures?|jours?|forfaits?)\s+"
    r"(?:de\s+|d')?)?"
    r"(?P<label>[A-Za-zÀ-ÿ0-9 ()/.,'-]{3,70})\s+"
    r"(?:[à@]|au\s+prix\s+de|pu(?:\s*ht)?\s*[:=]?|prix\s*[:=]?)\s+"
    r"(?P<price>\d[\d\s.\u00a0]*)\s*(?:fcfa|f\b)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


class RuleBasedExtractor:
    """Extracteur déterministe hors-ligne par expressions régulières."""

    def __init__(self, catalog: CatalogHint | None = None) -> None:
        self._catalog = catalog

    @property
    def name(self) -> str:
        """Nom et version de l'extracteur local."""
        return "local-rules-v1"

    def extract(self, content: bytes, media_type: str) -> Sequence[ExtractedField]:
        """Extrait les champs depuis un contenu texte UTF-8."""
        if not media_type.startswith("text/"):
            return self._all_required_missing()
        text = content.decode("utf-8", errors="replace").replace("\r\n", "\n")
        candidates: list[RawFieldCandidate] = []
        candidates.extend(self._extract_header_candidates(text))
        candidates.extend(self._extract_line_candidates(text))
        candidates.extend(self._extract_footer_candidates(text))
        return [verify_and_build_field(c, text, self._catalog) for c in candidates]

    def _extract_header_candidates(self, text: str) -> list[RawFieldCandidate]:
        """Extrait client, IFU, référence et date du document."""
        result: list[RawFieldCandidate] = [
            self._match_customer(text),
            self._optional_regex("customer.tax_id", _RE_TAX_ID, "ifu", text, 0.95),
            self._optional_regex("document.reference", _RE_REFERENCE, "ref", text, 0.90),
        ]
        date_match = _RE_DATE.search(text)
        if date_match:
            raw = date_match.group("date")
            result.append(RawFieldCandidate("document.date", FieldStatus.FOUND, raw, raw, 0.92))
        else:
            result.append(RawFieldCandidate("document.date", FieldStatus.MISSING))
        return result

    def _match_customer(self, text: str) -> RawFieldCandidate:
        """Recherche le nom du client dans le catalogue ou via un motif textuel."""
        if self._catalog is not None:
            text_low = text.lower()
            for name in self._catalog.customer_names:
                if name.lower() in text_low:
                    return RawFieldCandidate("customer.name", FieldStatus.FOUND, name, name, 0.95)
        match = _RE_CUSTOMER.search(text)
        if match:
            raw = match.group("name").strip(" .,;:\n")
            return RawFieldCandidate("customer.name", FieldStatus.FOUND, raw, raw, 0.80)
        return RawFieldCandidate("customer.name", FieldStatus.MISSING)

    def _extract_line_candidates(self, text: str) -> list[RawFieldCandidate]:
        """Extrait les lignes d'articles structurées présentes dans le texte."""
        matches = list(_RE_STRUCTURED_LINE.finditer(text))
        if not matches:
            return [
                RawFieldCandidate("lines[0].label", FieldStatus.MISSING),
                RawFieldCandidate("lines[0].quantity", FieldStatus.MISSING),
                RawFieldCandidate("lines[0].unit_price", FieldStatus.MISSING),
            ]
        candidates: list[RawFieldCandidate] = []
        for idx, match in enumerate(matches):
            candidates.extend(self._build_single_line(idx, match))
        return candidates

    def _build_single_line(self, idx: int, match: re.Match[str]) -> list[RawFieldCandidate]:
        """Construit les candidats d'une ligne d'article à partir d'une correspondance regex."""
        prefix = f"lines[{idx}]"
        qty = match.group("qty").strip()
        label = match.group("label").strip(" -:")
        price = match.group("price").strip()
        items = [
            RawFieldCandidate(f"{prefix}.label", FieldStatus.FOUND, label, label, 0.88),
            RawFieldCandidate(f"{prefix}.quantity", FieldStatus.FOUND, qty, qty, 0.92),
            RawFieldCandidate(f"{prefix}.unit_price", FieldStatus.FOUND, price, price, 0.92),
        ]
        unit = match.group("unit")
        if unit:
            u_clean = unit.strip()
            items.append(
                RawFieldCandidate(f"{prefix}.unit", FieldStatus.FOUND, u_clean, u_clean, 0.90)
            )
        return items

    def _extract_footer_candidates(self, text: str) -> list[RawFieldCandidate]:
        """Extrait les remises globales, délais de paiement et totaux mentionnés."""
        result: list[RawFieldCandidate] = []
        discounts = list(_RE_GLOBAL_DISCOUNT.finditer(text))
        if len(discounts) == 1:
            raw = discounts[0].group("rate")
            result.append(
                RawFieldCandidate("discount.global_rate", FieldStatus.FOUND, raw, raw, 0.90)
            )
        elif len(discounts) > 1:
            raw = discounts[0].group(0)
            result.append(
                RawFieldCandidate("discount.global_rate", FieldStatus.AMBIGUOUS, None, raw, 0.40)
            )
        result.append(
            self._optional_regex("payment.terms_days", _RE_TERMS_DAYS, "days", text, 0.90)
        )
        result.append(self._optional_regex("totals.net", _RE_TOTAL_NET, "amount", text, 0.88))
        result.append(self._optional_regex("totals.vat", _RE_TOTAL_VAT, "amount", text, 0.88))
        result.append(self._optional_regex("totals.gross", _RE_TOTAL_GROSS, "amount", text, 0.88))
        return result

    def _optional_regex(
        self,
        field_name: str,
        pattern: re.Pattern[str],
        group: str,
        text: str,
        confidence: float,
    ) -> RawFieldCandidate:
        """Extrait un champ optionnel par regex ou le marque MISSING."""
        match = pattern.search(text)
        if not match:
            return RawFieldCandidate(field_name, FieldStatus.MISSING)
        raw = match.group(group).strip()
        return RawFieldCandidate(field_name, FieldStatus.FOUND, raw, raw, confidence)

    def _all_required_missing(self) -> list[ExtractedField]:
        """Renvoie les champs obligatoires en MISSING pour un média non supporté."""
        required = (
            "customer.name",
            "document.date",
            "lines[0].label",
            "lines[0].quantity",
            "lines[0].unit_price",
        )
        return [
            ExtractedField(name, FieldStatus.MISSING, None, None, None, None) for name in required
        ]
