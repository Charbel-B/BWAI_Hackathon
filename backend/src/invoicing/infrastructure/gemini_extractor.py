"""Adaptateur d'extraction en ligne via Google AI Studio (Gemini) avec cascade Local-First."""

import http.client
import json
import logging
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from invoicing.application.ports import Extractor
from invoicing.domain.extraction import ExtractedField, FieldStatus
from invoicing.extraction.confidence import (
    DEFAULT_POLICY,
    CalibrationPolicy,
    CatalogHint,
    RawFieldCandidate,
    finalize_extracted_fields,
    is_local_extraction_sufficient,
    verify_and_build_field,
)
from invoicing.extraction.rules_extractor import RuleBasedExtractor

logger = logging.getLogger(__name__)

GEMINI_API_HOST = "generativelanguage.googleapis.com"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 0.5
HTTP_OK = 200
_NON_RETRYABLE_STATUSES = frozenset({400, 401, 403})

_RE_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)

RESPONSE_JSON_SCHEMA: dict[str, object] = {
    "type": "OBJECT",
    "required": ["fields"],
    "properties": {
        "fields": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "required": ["name", "status"],
                "properties": {
                    "name": {"type": "STRING"},
                    "status": {
                        "type": "STRING",
                        "enum": ["FOUND", "MISSING", "AMBIGUOUS"],
                    },
                    "value": {"type": "STRING", "nullable": True},
                    "raw_text": {"type": "STRING", "nullable": True},
                    "confidence": {"type": "NUMBER", "nullable": True},
                },
            },
        }
    },
}

SYSTEM_INSTRUCTION = (
    "Tu es un extracteur strict de pièces commerciales (messages WhatsApp, bons de commande, "
    "devis) pour la facturation au Bénin (FCFA). "
    "Extrais UNIQUEMENT ce qui est écrit littéralement dans la pièce. "
    "RÈGLES ABSOLUES : "
    "1. Ne calcule jamais rien (pas de multiplication, pas d'addition de remises). "
    "2. N'invente jamais une valeur absente : utilise status=MISSING avec value=null. "
    "3. Si une information est floue, contradictoire ou comporte plusieurs remises à cumuler, "
    "utilise status=AMBIGUOUS avec value=null. "
    "4. Pour chaque champ FOUND ou AMBIGUOUS, copie dans raw_text la sous-chaîne EXACTE "
    "mot pour mot depuis la pièce source. "
    "5. Noms de champs autorisés : customer.name, customer.tax_id, document.reference, "
    "document.date, lines[i].label, lines[i].quantity, lines[i].delivered_quantity, "
    "lines[i].unit, lines[i].unit_price, lines[i].discount_rate, discount.global_rate, "
    "payment.terms_days, payment.due_date, totals.net, totals.vat, totals.gross."
)


class _NonRetryableApiError(ValueError):
    """Erreur HTTP définitive (400, 401, 403) qu'il est inutile de retenter."""


class _LlmFieldItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    status: FieldStatus
    value: str | None = None
    raw_text: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    def to_candidate(self) -> RawFieldCandidate:
        return RawFieldCandidate(
            name=self.name,
            status=self.status,
            raw_value=self.value,
            raw_text=self.raw_text,
            base_confidence=self.confidence,
        )


class _LlmExtractionPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    fields: list[_LlmFieldItem]


@dataclass(frozen=True, slots=True)
class GeminiConfig:
    """Paramètres d'appel au modèle Gemini et de routage Local-First."""

    api_key: str
    model: str = DEFAULT_GEMINI_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    catalog: CatalogHint | None = None
    policy: CalibrationPolicy = DEFAULT_POLICY
    local_first: bool = True


class GeminiExtractor:
    """Extracteur en cascade : moteur local d'abord, escalade Gemini si pièce complexe."""

    def __init__(
        self,
        config: GeminiConfig,
        fallback: Extractor | None = None,
        transport: Callable[[str], str] | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._fallback = fallback or RuleBasedExtractor(
            catalog=config.catalog, policy=config.policy
        )
        self._uses_default_transport = transport is None
        self._transport = transport or self._call_gemini_https
        self._sleep = sleep_fn
        self._last_source = self._default_name()

    @property
    def name(self) -> str:
        """Provenance réelle de la dernière extraction (ou nom par défaut)."""
        return self._last_source

    def _default_name(self) -> str:
        if self._config.local_first:
            return f"cascade:{self._fallback.name}+gemini:{self._config.model}"
        return f"gemini:{self._config.model}"

    def extract(self, content: bytes, media_type: str) -> Sequence[ExtractedField]:
        """Tente l'extraction locale, puis escalade vers Gemini uniquement si nécessaire."""
        if not media_type.startswith("text/"):
            self._last_source = self._fallback.name
            return self._fallback.extract(content, media_type)

        local_fields = self._fallback.extract(content, media_type)
        if self._config.local_first and is_local_extraction_sufficient(local_fields):
            self._last_source = f"cascade:{self._fallback.name}"
            return local_fields

        if self._uses_default_transport and not self._config.api_key:
            logger.warning("Clé API Gemini absente : conservation du résultat local.")
            self._last_source = f"fallback:{self._fallback.name}"
            return local_fields

        text = content.decode("utf-8", errors="replace").replace("\r\n", "\n")
        payload = self._fetch_validated_payload(text)
        if payload is None:
            self._last_source = f"fallback:{self._fallback.name}"
            return local_fields

        verified = [
            verify_and_build_field(
                item.to_candidate(), text, self._config.catalog, self._config.policy
            )
            for item in payload.fields
        ]
        self._last_source = f"gemini:{self._config.model}"
        return finalize_extracted_fields(verified, self._config.catalog, self._config.policy)

    def _fetch_validated_payload(self, text: str) -> _LlmExtractionPayload | None:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                raw_json = _strip_json_fences(self._transport(text))
                return _LlmExtractionPayload.model_validate_json(raw_json)
            except _NonRetryableApiError as err:
                logger.warning("Erreur API Gemini non retentable : %s", err)
                return None
            except (ValidationError, OSError, ValueError, http.client.HTTPException) as err:
                logger.warning(
                    "Échec extraction Gemini (tentative %d/%d) : %s",
                    attempt,
                    MAX_ATTEMPTS,
                    type(err).__name__,
                )
                if attempt < MAX_ATTEMPTS:
                    self._sleep(RETRY_BACKOFF_SECONDS)
        return None

    def _call_gemini_https(self, text: str) -> str:
        body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                "contents": [{"role": "user", "parts": [{"text": text}]}],
                "generationConfig": {
                    "temperature": 0.0,
                    "responseMimeType": "application/json",
                    "responseSchema": RESPONSE_JSON_SCHEMA,
                },
            }
        ).encode("utf-8")
        path = f"/v1beta/models/{self._config.model}:generateContent"
        conn = http.client.HTTPSConnection(GEMINI_API_HOST, timeout=self._config.timeout_seconds)
        try:
            conn.request(
                "POST",
                path,
                body=body,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "x-goog-api-key": self._config.api_key,
                },
            )
            response = conn.getresponse()
            raw_body = response.read().decode("utf-8", errors="replace")
        finally:
            conn.close()

        if response.status in _NON_RETRYABLE_STATUSES:
            msg = f"HTTP {response.status}"
            raise _NonRetryableApiError(msg)
        if response.status != HTTP_OK:
            msg = f"HTTP {response.status} depuis Gemini API"
            raise ValueError(msg)
        return _extract_candidate_json(raw_body)


def _strip_json_fences(raw_text: str) -> str:
    return _RE_CODE_FENCE.sub("", raw_text.strip()).strip()


def _extract_candidate_json(api_response_text: str) -> str:
    parsed = json.loads(api_response_text)
    try:
        text_content = parsed["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as err:
        msg = "Réponse Gemini sans contenu candidat exploitable"
        raise ValueError(msg) from err
    if not isinstance(text_content, str):
        msg = "Le contenu candidat Gemini n'est pas une chaîne JSON"
        raise ValueError(msg)
    return text_content
