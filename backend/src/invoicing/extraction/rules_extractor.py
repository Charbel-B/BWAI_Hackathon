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
    r"(?:devis|commande|bon de commande|bon de livraison|r[eé]f(?:[eé]rence)?|bc|bl|cmd|dev)\s*"
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
_DELIVERED_TRAIL = (
    r"(?:\s*(?:\(|[-\u2013\u2014,;]\s*)"
    r"(?:(?:qt[eé]|quantit[eé])?\s*livr[eé]e?s?\s*[:=]?\s*(?P<deliv_a>\d+(?:[.,]\d+)?)"
    r"|(?P<deliv_b>\d+(?:[.,]\d+)?)\s*(?:(?:" + _UNITS + r")\s+)?livr[eé]e?s?)"
    r"[^)\n]*\)?)?"
)
_RE_STRUCTURED_LINE = re.compile(
    r"^\s*[-*•]?\s*(?P<qty>\d+(?:[.,]\d+)?)\s+"
    r"(?:(?P<unit>" + _UNITS + r")\s+"
    r"(?:de\s+|d')?)?"
    r"(?P<label>[A-Za-zÀ-ÿ0-9 ()/.,'-]{3,70})\s+"
    r"(?:[à@]|au\s+prix\s+de|pu(?:\s*ht)?\s*[:=]?|prix\s*[:=]?)\s+"
    r"(?P<price>\d[\d\s.\u00a0]*)\s*(?:fcfa|f\b)?" + _DELIVERED_TRAIL + r"\s*$",
    _FLAGS,
)
_RE_PARTIAL_DELIVERY = re.compile(
    r"(?:(?:qt[eé]|quantit[eé])\s+livr[eé]e?s?\s*[:=]?\s*|livr[eé]e?s?\s*[:=]?\s*)?"
    r"(?P<delivered>\d+(?:[.,]\d+)?)\s+"
    r"(?:(?P<unit>" + _UNITS + r")\s+)?"
    r"(?:livr[eé]e?s?\s+)?"
    r"sur\s+(?:les\s+)?(?P<ordered>\d+(?:[.,]\d+)?)\s+"
    r"(?:(?:" + _UNITS + r")\s+)?(?:command[eé]e?s?|pr[eé]vue?s?)",
    re.IGNORECASE,
)
_RE_INLINE_LABEL = re.compile(
    r"(?:re[çc]u|livr[eé]|command[eé])\s+(?P<label>(?:[^,;\n.]|\.(?!\s|$)){3,70})",
    re.IGNORECASE,
)
_RE_INLINE_PRICE = re.compile(
    r"(?:tarif(?:\s+convenu)?|prix(?:\s+unitaire)?|factur[eé]e?s?|"
    r"compt[eé]e?s?|pu(?:\s*ht)?|[à@])\s*[:=]?\s*"
    r"(?P<price>\d[\d\s.\u00a0]*)\s*(?:fcfa|f\b)",
    re.IGNORECASE,
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
        """Lignes structurées, livraisons partielles, puis quantités non couvertes."""
        matches = list(_RE_STRUCTURED_LINE.finditer(text))
        covered: list[tuple[int, int]] = [m.span() for m in matches]
        candidates: list[RawFieldCandidate] = []
        for idx, match in enumerate(matches):
            candidates.extend(self._structured_line(idx, match))

        next_idx = len(matches)
        partial_candidates, partial_spans, next_idx = self._partial_delivery_candidates(
            text, matches, covered, next_idx
        )
        candidates.extend(partial_candidates)
        covered.extend(partial_spans)

        for offset, found in enumerate(self._uncovered_quantities(text, covered)):
            idx = next_idx + offset
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

    def _partial_delivery_candidates(
        self,
        text: str,
        structured: list[re.Match[str]],
        covered: list[tuple[int, int]],
        next_idx: int,
    ) -> tuple[list[RawFieldCandidate], list[tuple[int, int]], int]:
        """Lit les mentions « X livrés sur Y commandés » (ex. p008) en ligne ou en complément."""
        candidates: list[RawFieldCandidate] = []
        spans: list[tuple[int, int]] = []
        attached_lines: set[int] = {
            idx for idx, m in enumerate(structured) if m.group("deliv_a") or m.group("deliv_b")
        }
        partials = [
            m
            for m in _RE_PARTIAL_DELIVERY.finditer(text)
            if not any(start <= m.start() < end for start, end in covered)
        ]
        for pos_idx, match in enumerate(partials):
            spans.append(match.span())
            target_idx = self._find_structured_target(structured, attached_lines, match)
            if target_idx is not None:
                attached_lines.add(target_idx)
                delivered = match.group("delivered").strip()
                candidates.append(
                    RawFieldCandidate(
                        f"lines[{target_idx}].delivered_quantity",
                        FieldStatus.FOUND,
                        delivered,
                        delivered,
                        0.92,
                        match.start("delivered"),
                    )
                )
                continue
            line_start = text.rfind("\n", 0, match.start()) + 1
            newline_after = text.find("\n", match.end())
            line_end = len(text) if newline_after == -1 else newline_after
            prev_end = partials[pos_idx - 1].end() if pos_idx > 0 else 0
            next_start = partials[pos_idx + 1].start() if pos_idx + 1 < len(partials) else len(text)
            window_start = max(line_start, prev_end)
            window_end = min(line_end, next_start)
            line_items, extra_spans = self._inline_partial_line(
                next_idx, text, match, (window_start, window_end)
            )
            candidates.extend(line_items)
            spans.extend(extra_spans)
            next_idx += 1
        return candidates, spans, next_idx

    @staticmethod
    def _find_structured_target(
        structured: list[re.Match[str]],
        attached: set[int],
        match: re.Match[str],
    ) -> int | None:
        ordered = match.group("ordered").strip().replace(",", ".")
        for idx, line_match in enumerate(structured):
            if idx in attached:
                continue
            if line_match.group("qty").strip().replace(",", ".") == ordered:
                return idx
        if len(structured) == 1 and 0 not in attached:
            return 0
        return None

    def _inline_partial_line(
        self,
        idx: int,
        text: str,
        match: re.Match[str],
        window: tuple[int, int],
    ) -> tuple[list[RawFieldCandidate], list[tuple[int, int]]]:
        prefix = f"lines[{idx}]"
        ordered = match.group("ordered").strip()
        delivered = match.group("delivered").strip()
        items: list[RawFieldCandidate] = [
            RawFieldCandidate(
                f"{prefix}.quantity",
                FieldStatus.FOUND,
                ordered,
                ordered,
                0.92,
                match.start("ordered"),
            ),
            RawFieldCandidate(
                f"{prefix}.delivered_quantity",
                FieldStatus.FOUND,
                delivered,
                delivered,
                0.92,
                match.start("delivered"),
            ),
        ]
        unit = match.group("unit")
        if unit:
            raw_unit = unit.strip()
            items.append(
                RawFieldCandidate(
                    f"{prefix}.unit",
                    FieldStatus.FOUND,
                    raw_unit,
                    raw_unit,
                    0.90,
                    match.start("unit"),
                )
            )
        window_start, window_end = window
        extra_spans: list[tuple[int, int]] = []
        label_candidate, label_span = self._match_inline_label(
            prefix, text, window_start, match.start()
        )
        if label_candidate is not None:
            items.append(label_candidate)
        if label_span is not None:
            extra_spans.append(label_span)
        price_match = _RE_INLINE_PRICE.search(text, match.end(), window_end) or (
            _RE_INLINE_PRICE.search(text, window_start, match.start())
        )
        if price_match:
            raw_price = price_match.group("price").strip()
            items.append(
                RawFieldCandidate(
                    f"{prefix}.unit_price",
                    FieldStatus.FOUND,
                    raw_price,
                    raw_price,
                    0.92,
                    price_match.start("price"),
                )
            )
        return items, extra_spans

    def _match_inline_label(
        self, prefix: str, text: str, start_pos: int, before_pos: int
    ) -> tuple[RawFieldCandidate | None, tuple[int, int] | None]:
        segment = text[start_pos:before_pos]
        if self._catalog is not None and self._catalog.item_labels:
            lower_segment = segment.lower()
            for label in sorted(self._catalog.item_labels, key=len, reverse=True):
                rel = lower_segment.rfind(label.lower())
                if rel != -1:
                    pos = start_pos + rel
                    raw = text[pos : pos + len(label)]
                    return (
                        RawFieldCandidate(
                            f"{prefix}.label", FieldStatus.FOUND, raw, raw, 0.92, pos
                        ),
                        (pos, pos + len(label)),
                    )
        label_matches = list(_RE_INLINE_LABEL.finditer(segment))
        if label_matches:
            last = label_matches[-1]
            raw = last.group("label").strip(" -:,.")
            if raw:
                pos = start_pos + last.start("label")
                return (
                    RawFieldCandidate(f"{prefix}.label", FieldStatus.FOUND, raw, raw, 0.88, pos),
                    (pos, pos + len(raw)),
                )
        return None, None

    @staticmethod
    def _uncovered_quantities(
        text: str, covered_spans: list[tuple[int, int]]
    ) -> list[re.Match[str]]:
        """Quantités avec unité hors des lignes reconnues et hors délais de paiement."""
        covered = [*covered_spans, *(m.span() for m in _RE_TERMS_DAYS.finditer(text))]
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
        deliv_group = "deliv_a" if match.group("deliv_a") else "deliv_b"
        deliv_val = match.group(deliv_group)
        if deliv_val is not None:
            raw_deliv = deliv_val.strip()
            items.append(
                RawFieldCandidate(
                    f"{prefix}.delivered_quantity",
                    FieldStatus.FOUND,
                    raw_deliv,
                    raw_deliv,
                    0.92,
                    match.start(deliv_group),
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
