"""Extracteur local déterministe par règles (référence sans IA et repli hors-ligne)."""

import re
from collections.abc import Sequence

from invoicing.domain.extraction import ExtractedField, FieldStatus
from invoicing.extraction.confidence import (
    DEFAULT_POLICY,
    CalibrationPolicy,
    CatalogHint,
    RawFieldCandidate,
    finalize_extracted_fields,
    verify_and_build_field,
)

_UNITS = (
    r"sacs?|barres?|camions?|m3|m2|m|unit[eé]s?|feuilles?|seaux?|pots?|"
    r"rouleaux?|cartons?|lots?|citernes?|voyages?|heures?|jours?|forfaits?"
)
_AMOUNT = r"(?P<amount>\d[\d\s.\u00a0]*?)\s*(?:fcfa|f\b|$)"
_FLAGS = re.IGNORECASE | re.MULTILINE

_RE_CUSTOMER = re.compile(
    r"(?:client|entreprise|soci[eé]t[eé]|destinataire|de la part de|ici|c'est)\s*[:=-]?\s*"
    r"(?P<name>[A-ZÀ-Ÿ][A-Za-zÀ-ÿ0-9 '&.-]{2,60})",
    re.IGNORECASE,
)
_RE_TAX_ID = re.compile(r"(?:ifu|n[°o]?\s*ifu)\s*[:=-]?\s*(?P<ifu>(?<!\d)\d{13}(?!\d))", re.I)
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
_RE_DISCOUNT_CONTEXT = re.compile(
    r"remise|r[eé]duction|rabais|fid[eé]lit[eé]|escompte|ristourne|comptant|\bcash\b",
    re.IGNORECASE,
)
_RE_PERCENT = re.compile(r"\d+(?:[.,]\d+)?\s*%")
_RE_TERMS_DAYS = re.compile(
    r"(?:d[eé]lai(?:\s+de\s+paiement)?|paiement(?:\s+[aà])?|r[eè]glement(?:\s+[aà])?)\s*[:=-]?\s*"
    r"(?P<days>\d{1,3})\s*jours?",
    re.IGNORECASE,
)
_RE_TOTAL_NET = re.compile(r"total\s+ht\s*[:=-]?\s*" + _AMOUNT, _FLAGS)
_RE_TOTAL_VAT = re.compile(r"(?:montant\s+)?tva(?:\s+18\s*%)?\s*[:=-]?\s*" + _AMOUNT, _FLAGS)
_RE_TOTAL_GROSS = re.compile(r"total(?:\s+ttc)?\s*[:=-]?\s*" + _AMOUNT, _FLAGS)
_RE_STRUCTURED_LINE = re.compile(
    r"^\s*[-*•]?\s*(?P<qty>\d+(?:[.,]\d+)?)\s+"
    r"(?:(?P<unit>" + _UNITS + r")\s+"
    r"(?:de\s+|d')?)?"
    r"(?P<label>[A-Za-zÀ-ÿ0-9 ()/.,'-]{3,70})\s+"
    r"(?:[à@]|au\s+prix\s+de|pu(?:\s*ht)?\s*[:=]?|prix\s*[:=]?)\s+"
    r"(?P<price>\d[\d\s.\u00a0]*)\s*(?:fcfa|f\b)?\s*$",
    _FLAGS,
)
_RE_QTY_UNIT = re.compile(r"\b\d+(?:[.,]\d+)?\s+(?:" + _UNITS + r")\b", re.IGNORECASE)
_REQUIRED_WHEN_UNSUPPORTED = (
    "customer.name",
    "document.date",
    "lines[0].label",
    "lines[0].quantity",
    "lines[0].unit_price",
)


class RuleBasedExtractor:
    """Extracteur déterministe hors-ligne par expressions régulières."""

    def __init__(
        self,
        catalog: CatalogHint | None = None,
        policy: CalibrationPolicy = DEFAULT_POLICY,
    ) -> None:
        self._catalog = catalog
        self._policy = policy

    @property
    def name(self) -> str:
        return "local-rules-v1"

    def extract(self, content: bytes, media_type: str) -> Sequence[ExtractedField]:
        """Extrait les champs d'un contenu texte UTF-8."""
        if not media_type.startswith("text/"):
            return [
                ExtractedField(name, FieldStatus.MISSING, None, None, None, None)
                for name in _REQUIRED_WHEN_UNSUPPORTED
            ]
        text = content.decode("utf-8", errors="replace").replace("\r\n", "\n")
        candidates = [
            *self._header_candidates(text),
            *self._line_candidates(text),
            *self._footer_candidates(text),
        ]
        verified = [
            verify_and_build_field(c, text, self._catalog, self._policy) for c in candidates
        ]
        return finalize_extracted_fields(verified, self._catalog, self._policy)

    def _header_candidates(self, text: str) -> list[RawFieldCandidate]:
        result = [
            self._match_customer(text),
            self._optional_regex("customer.tax_id", _RE_TAX_ID, "ifu", text, 0.95),
            self._optional_regex("document.reference", _RE_REFERENCE, "ref", text, 0.90),
        ]
        date_match = _RE_DATE.search(text)
        if date_match:
            raw = date_match.group("date")
            result.append(
                RawFieldCandidate(
                    "document.date", FieldStatus.FOUND, raw, raw, 0.92, date_match.start("date")
                )
            )
        else:
            result.append(RawFieldCandidate("document.date", FieldStatus.MISSING))
        return result

    def _match_customer(self, text: str) -> RawFieldCandidate:
        if self._catalog is not None:
            text_low = text.lower()
            for name in self._catalog.customer_names:
                pos = text_low.find(name.lower())
                if pos != -1:
                    return RawFieldCandidate(
                        "customer.name", FieldStatus.FOUND, name, name, 0.95, pos
                    )
        match = _RE_CUSTOMER.search(text)
        if match:
            raw = match.group("name").strip(" .,;:\n")
            return RawFieldCandidate(
                "customer.name", FieldStatus.FOUND, raw, raw, 0.80, match.start("name")
            )
        return RawFieldCandidate("customer.name", FieldStatus.MISSING)

    def _line_candidates(self, text: str) -> list[RawFieldCandidate]:
        """Lignes structurées, puis quantités avec unité non couvertes (lignes perdues)."""
        matches = list(_RE_STRUCTURED_LINE.finditer(text))
        candidates: list[RawFieldCandidate] = []
        for idx, match in enumerate(matches):
            candidates.extend(self._structured_line(idx, match))
        for offset, found in enumerate(self._uncovered_quantities(text, matches)):
            idx = len(matches) + offset
            candidates.append(
                RawFieldCandidate(
                    f"lines[{idx}].quantity",
                    FieldStatus.AMBIGUOUS,
                    None,
                    found.group(0),
                    0.40,
                    found.start(),
                )
            )
        return candidates

    @staticmethod
    def _uncovered_quantities(text: str, lines: list[re.Match[str]]) -> list[re.Match[str]]:
        """Quantités avec unité hors des lignes structurées et hors délais de paiement."""
        covered = [m.span() for m in lines] + [m.span() for m in _RE_TERMS_DAYS.finditer(text)]
        return [
            m
            for m in _RE_QTY_UNIT.finditer(text)
            if not any(start <= m.start() < end for start, end in covered)
        ]

    @staticmethod
    def _structured_line(idx: int, match: re.Match[str]) -> list[RawFieldCandidate]:
        prefix = f"lines[{idx}]"
        parts = [("label", 0.88), ("quantity", 0.92), ("unit_price", 0.92), ("unit", 0.90)]
        group_of = {"quantity": "qty", "unit_price": "price", "label": "label", "unit": "unit"}
        items: list[RawFieldCandidate] = []
        for attr, confidence in parts:
            group = group_of[attr]
            value = match.group(group)
            if value is None:
                continue
            raw = value.strip(" -:") if attr == "label" else value.strip()
            items.append(
                RawFieldCandidate(
                    f"{prefix}.{attr}", FieldStatus.FOUND, raw, raw, confidence, match.start(group)
                )
            )
        return items

    def _footer_candidates(self, text: str) -> list[RawFieldCandidate]:
        result: list[RawFieldCandidate] = []
        discount = self._discount_candidate(text)
        if discount is not None:
            result.append(discount)
        result.extend(
            [
                self._optional_regex("payment.terms_days", _RE_TERMS_DAYS, "days", text, 0.90),
                self._optional_regex("totals.net", _RE_TOTAL_NET, "amount", text, 0.88),
                self._optional_regex("totals.vat", _RE_TOTAL_VAT, "amount", text, 0.88),
                self._optional_regex("totals.gross", _RE_TOTAL_GROSS, "amount", text, 0.88),
            ]
        )
        return result

    @staticmethod
    def _discount_candidate(text: str) -> RawFieldCandidate | None:
        """Un seul pourcentage de remise : FOUND. Plusieurs : AMBIGUOUS, jamais cumulés."""
        hits: list[tuple[int, int, int, str]] = []
        line_start = 0
        for line in text.split("\n"):
            if _RE_DISCOUNT_CONTEXT.search(line):
                hits.extend(
                    (line_start, line_start + len(line), line_start + m.start(), m.group(0))
                    for m in _RE_PERCENT.finditer(line)
                )
            line_start += len(line) + 1
        if not hits:
            return None
        if len(hits) == 1:
            _, _, start, percent = hits[0]
            return RawFieldCandidate(
                "discount.global_rate", FieldStatus.FOUND, percent, percent, 0.90, start
            )
        first_start, last_end = hits[0][0], hits[-1][1]
        raw = text[first_start:last_end].strip()
        return RawFieldCandidate(
            "discount.global_rate", FieldStatus.AMBIGUOUS, None, raw, 0.40, first_start
        )

    @staticmethod
    def _optional_regex(
        field_name: str,
        pattern: re.Pattern[str],
        group: str,
        text: str,
        confidence: float,
    ) -> RawFieldCandidate:
        match = pattern.search(text)
        if not match:
            return RawFieldCandidate(field_name, FieldStatus.MISSING)
        raw = match.group(group).strip()
        return RawFieldCandidate(
            field_name, FieldStatus.FOUND, raw, raw, confidence, match.start(group)
        )
