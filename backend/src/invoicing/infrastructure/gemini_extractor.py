"""Adaptateur d'extraction en ligne via l'API Google AI Studio (Gemini).

Conformément aux conventions :
- Pydantic valide la sortie JSON brute à la frontière du modèle ;
- le modèle ne calcule jamais d'ancrage ni de montant ;
- en cas de JSON invalide ou d'erreur réseau, une seconde tentative est lancée ;
- si l'échec persiste ou si la clé API est absente, l'extracteur se replie
  proprement sur ``RuleBasedExtractor`` sans interrompre le service.
"""

import http.client
import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from invoicing.application.ports import Extractor
from invoicing.domain.extraction import ExtractedField, FieldStatus
from invoicing.extraction.confidence import (
    CatalogHint,
    RawFieldCandidate,
    verify_and_build_field,
)
from invoicing.extraction.rules_extractor import RuleBasedExtractor

logger = logging.getLogger(__name__)

GEMINI_API_HOST = "generativelanguage.googleapis.com"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_ATTEMPTS = 2
HTTP_OK = 200

SYSTEM_INSTRUCTION = (
    "Tu es un extracteur strict de pièces commerciales (messages WhatsApp, bons de commande, "
    "devis) pour la facturation au Bénin (FCFA). "
    "Extrais UNIQUEMENT ce qui est écrit littéralement dans la pièce. "
    "RÈGLES ABSOLUES : "
    "1. Ne calcule jamais rien (pas de multiplication, pas d'addition de remises). "
    "2. N'invente jamais une valeur absente : utilise le statut MISSING avec value=null. "
    "3. Si une information est floue, contradictoire ou comporte plusieurs remises à cumuler, "
    "utilise le statut AMBIGUOUS. "
    "4. Pour chaque champ FOUND ou AMBIGUOUS, fournis dans raw_text la sous-chaîne EXACTE "
    "copiée mot pour mot depuis la pièce source. "
    "5. Noms de champs autorisés : customer.name, customer.tax_id, document.reference, "
    "document.date, lines[i].label, lines[i].quantity, lines[i].unit, lines[i].unit_price, "
    "lines[i].discount_rate, discount.global_rate, payment.terms_days, payment.due_date, "
    "totals.net, totals.vat, totals.gross."
)


class _LlmFieldItem(BaseModel):
    """Champ unitaire renvoyé par le modèle de langage à la frontière JSON."""

    model_config = ConfigDict(extra="ignore")

    name: str
    status: FieldStatus
    value: str | None = None
    raw_text: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    def to_candidate(self) -> RawFieldCandidate:
        """Transforme l'objet Pydantic en candidat pour le vérificateur déterministe."""
        return RawFieldCandidate(
            name=self.name,
            status=self.status,
            raw_value=self.value,
            raw_text=self.raw_text,
            base_confidence=self.confidence,
        )


class _LlmExtractionPayload(BaseModel):
    """Enveloppe JSON structurée attendue en sortie du modèle Gemini."""

    model_config = ConfigDict(extra="ignore")

    fields: list[_LlmFieldItem]


@dataclass(frozen=True, slots=True)
class GeminiConfig:
    """Paramètres d'appel au modèle Gemini."""

    api_key: str
    model: str = DEFAULT_GEMINI_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    catalog: CatalogHint | None = None


class GeminiExtractor:
    """Extracteur en ligne Google AI Studio avec validation Pydantic, 1 relance et repli."""

    def __init__(
        self,
        config: GeminiConfig,
        fallback: Extractor | None = None,
        transport: Callable[[str], str] | None = None,
    ) -> None:
        self._config = config
        self._fallback = fallback or RuleBasedExtractor(catalog=config.catalog)
        self._transport = transport or self._call_gemini_https

    @property
    def name(self) -> str:
        """Nom et version du modèle Gemini configuré."""
        return f"gemini:{self._config.model}"

    def extract(self, content: bytes, media_type: str) -> Sequence[ExtractedField]:
        """Extrait les champs via Gemini ou se replie sur l'extracteur local en cas d'échec."""
        if not media_type.startswith("text/"):
            return self._fallback.extract(content, media_type)
        if not self._config.api_key and self._transport == self._call_gemini_https:
            logger.warning("Clé API Gemini absente : repli sur l'extracteur local.")
            return self._fallback.extract(content, media_type)

        text = content.decode("utf-8", errors="replace").replace("\r\n", "\n")
        payload = self._fetch_validated_payload(text)
        if payload is None:
            return self._fallback.extract(content, media_type)

        return [
            verify_and_build_field(item.to_candidate(), text, self._config.catalog)
            for item in payload.fields
        ]

    def _fetch_validated_payload(self, text: str) -> _LlmExtractionPayload | None:
        """Exécute jusqu'à deux tentatives d'appel et de validation Pydantic."""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                raw_json = self._transport(text)
                return _LlmExtractionPayload.model_validate_json(raw_json)
            except (ValidationError, OSError, ValueError, http.client.HTTPException) as err:
                logger.warning(
                    "Échec extraction Gemini (tentative %d/%d) : %s",
                    attempt,
                    MAX_ATTEMPTS,
                    err,
                )
        return None

    def _call_gemini_https(self, text: str) -> str:
        """Appelle l'endpoint REST generateContent de Google AI Studio en HTTPS."""
        body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                "contents": [{"role": "user", "parts": [{"text": text}]}],
                "generationConfig": {
                    "temperature": 0.0,
                    "responseMimeType": "application/json",
                },
            }
        ).encode("utf-8")
        path = f"/v1beta/models/{self._config.model}:generateContent?key={self._config.api_key}"
        conn = http.client.HTTPSConnection(
            GEMINI_API_HOST,
            timeout=self._config.timeout_seconds,
        )
        try:
            conn.request(
                "POST",
                path,
                body=body,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            response = conn.getresponse()
            raw_body = response.read().decode("utf-8", errors="replace")
        finally:
            conn.close()

        if response.status != HTTP_OK:
            msg = f"HTTP {response.status} depuis Gemini API"
            raise ValueError(msg)
        return _extract_candidate_json(raw_body)


def _extract_candidate_json(api_response_text: str) -> str:
    """Extrait le texte JSON du premier candidat de la réponse REST Gemini."""
    parsed = json.loads(api_response_text)
    try:
        candidates = parsed["candidates"]
        first_part = candidates[0]["content"]["parts"][0]
        text_content = first_part["text"]
    except (KeyError, IndexError, TypeError) as err:
        msg = "Réponse Gemini sans contenu candidat exploitable"
        raise ValueError(msg) from err
    if not isinstance(text_content, str):
        msg = "Le contenu candidat Gemini n'est pas une chaîne JSON"
        raise TypeError(msg)
    return text_content
