"""Ports : interfaces que l'infrastructure implémente. Chaque responsable ajoute les siens."""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from invoicing.domain.extraction import ExtractedField


class Clock(Protocol):
    """Source unique de l'heure. Le cœur métier n'appelle jamais datetime.now()."""

    def now(self) -> datetime:
        """Instant courant, conscient du fuseau, en UTC."""
        ...


class Extractor(Protocol):
    """Lit une pièce source et rend ses champs au format du contrat."""

    @property
    def name(self) -> str:
        """Nom et version de l'extracteur, enregistrés avec chaque résultat."""
        ...

    def extract(self, content: bytes, media_type: str) -> Sequence[ExtractedField]:
        """Extrait les champs d'une pièce ; un champ introuvable est rendu MISSING."""
        ...
