"""Adaptateur de rejeu de réponses d'extraction réelles enregistrées (ADR 0001).

Les réponses sont indexées par l'empreinte SHA-256 du contenu de la pièce source.
Le nom de l'extracteur commence toujours par ``recorded:`` afin que l'interface
signale explicitement qu'il s'agit d'un rejeu enregistré.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from invoicing.application.ports import Extractor
from invoicing.domain.extraction import (
    ExtractedField,
    FieldStatus,
    RegionAnchor,
    SourceAnchor,
    TextAnchor,
)


class _SerializedAnchor(BaseModel):
    """Schéma Pydantic de sérialisation d'un ancrage aux frontières."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["text", "region"]
    start: int | None = None
    end: int | None = None
    page: int | None = None
    box: tuple[float, float, float, float] | None = None

    def to_domain(self) -> SourceAnchor:
        """Convertit l'ancrage sérialisé en objet immuable du domaine."""
        if self.kind == "text":
            return TextAnchor(start=self.start or 0, end=self.end or 0)
        return RegionAnchor(
            page=self.page or 1,
            box=self.box or (0.0, 0.0, 0.0, 0.0),
        )


class _SerializedField(BaseModel):
    """Schéma Pydantic d'un champ extrait enregistré sur disque."""

    model_config = ConfigDict(extra="forbid")

    name: str
    status: FieldStatus
    value: str | None = None
    raw_text: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    anchor: _SerializedAnchor | None = None

    def to_domain(self) -> ExtractedField:
        """Convertit l'entrée JSON validée en ``ExtractedField`` du domaine."""
        domain_anchor = self.anchor.to_domain() if self.anchor is not None else None
        return ExtractedField(
            name=self.name,
            status=self.status,
            value=self.value,
            raw_text=self.raw_text,
            confidence=self.confidence,
            anchor=domain_anchor,
        )


class _RecordedStoreModel(BaseModel):
    """Structure du fichier JSON de réponses enregistrées."""

    model_config = ConfigDict(extra="forbid")

    source_model: str
    records: dict[str, list[_SerializedField]]


def content_sha256(content: bytes) -> str:
    """Calcule l'empreinte SHA-256 hexadécimale d'une pièce source."""
    return hashlib.sha256(content).hexdigest()


def serialize_extracted_fields(fields: Sequence[ExtractedField]) -> list[dict[str, object]]:
    """Sérialise une séquence de ``ExtractedField`` en dictionnaires JSON."""
    output: list[dict[str, object]] = []
    for f in fields:
        anchor_dict: dict[str, object] | None = None
        if isinstance(f.anchor, TextAnchor):
            anchor_dict = {"kind": "text", "start": f.anchor.start, "end": f.anchor.end}
        elif isinstance(f.anchor, RegionAnchor):
            anchor_dict = {
                "kind": "region",
                "page": f.anchor.page,
                "box": list(f.anchor.box),
            }
        output.append(
            {
                "name": f.name,
                "status": f.status.value,
                "value": f.value,
                "raw_text": f.raw_text,
                "confidence": f.confidence,
                "anchor": anchor_dict,
            }
        )
    return output


class RecordedExtractor:
    """Rejoue des extractions enregistrées par SHA-256 avec repli optionnel."""

    def __init__(
        self,
        records: Mapping[str, Sequence[ExtractedField]],
        source_model: str = "gemini-2.5-flash",
        fallback: Extractor | None = None,
    ) -> None:
        self._records = {k: tuple(v) for k, v in records.items()}
        self._source_model = source_model
        self._fallback = fallback

    @classmethod
    def from_json_file(
        cls,
        path: Path,
        fallback: Extractor | None = None,
    ) -> "RecordedExtractor":
        """Charge un magasin d'extractions enregistrées depuis un fichier JSON."""
        raw_data = json.loads(path.read_text(encoding="utf-8"))
        validated = _RecordedStoreModel.model_validate(raw_data)
        domain_records = {
            sha: tuple(item.to_domain() for item in items)
            for sha, items in validated.records.items()
        }
        return cls(
            records=domain_records,
            source_model=validated.source_model,
            fallback=fallback,
        )

    @property
    def name(self) -> str:
        """Nom explicite signalant un rejeu enregistré."""
        return f"recorded:{self._source_model}"

    def extract(self, content: bytes, media_type: str) -> Sequence[ExtractedField]:
        """Renvoie l'extraction enregistrée pour l'empreinte SHA-256 ou délègue au repli."""
        digest = content_sha256(content)
        recorded = self._records.get(digest)
        if recorded is not None:
            return recorded
        if self._fallback is not None:
            return self._fallback.extract(content, media_type)
        return ()
