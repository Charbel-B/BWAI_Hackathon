"""Champ extrait d'une pièce source, selon docs/contrats/champ-extrait.md."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from invoicing.domain.errors import InvariantViolationError


class FieldStatus(StrEnum):
    """Ce que l'extracteur a trouvé dans la pièce."""

    FOUND = "FOUND"
    MISSING = "MISSING"
    AMBIGUOUS = "AMBIGUOUS"


class ReviewState(StrEnum):
    """Décision humaine sur un champ."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CORRECTED = "CORRECTED"


@dataclass(frozen=True, slots=True)
class TextAnchor:
    """Passage d'une pièce texte, en positions de caractères [start, end)."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if not 0 <= self.start <= self.end:
            raise InvariantViolationError("ancrage texte : il faut 0 <= start <= end")


@dataclass(frozen=True, slots=True)
class RegionAnchor:
    """Zone d'une page d'image ou de PDF, coordonnées normalisées entre 0 et 1."""

    page: int
    box: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        x0, y0, x1, y1 = self.box
        if self.page < 1:
            raise InvariantViolationError("ancrage zone : les pages commencent à 1")
        if not (0 <= x0 <= x1 <= 1 and 0 <= y0 <= y1 <= 1):
            raise InvariantViolationError("ancrage zone : coordonnées hors de [0, 1] ou inversées")


type SourceAnchor = TextAnchor | RegionAnchor


@dataclass(frozen=True, slots=True)
class Review:
    """Décision humaine. Une correction porte toujours sa nouvelle valeur."""

    state: ReviewState = ReviewState.PENDING
    value: str | None = None
    by: str | None = None
    at: datetime | None = None

    def __post_init__(self) -> None:
        if self.state is ReviewState.CORRECTED and self.value is None:
            raise InvariantViolationError("une correction doit porter une valeur")
        if self.state is not ReviewState.PENDING and (self.by is None or self.at is None):
            raise InvariantViolationError("une décision humaine a un auteur et une date")


@dataclass(frozen=True, slots=True)
class ExtractedField:
    """Valeur lue dans une pièce, avec son origine et sa confiance.

    Un champ MISSING n'a ni valeur, ni confiance, ni ancrage : aucune donnée n'est inventée.
    """

    name: str
    status: FieldStatus
    value: str | None
    raw_text: str | None
    confidence: float | None
    anchor: SourceAnchor | None
    review: Review = Review()

    def __post_init__(self) -> None:
        has_content = any(v is not None for v in (self.value, self.confidence, self.anchor))
        if self.status is FieldStatus.MISSING and has_content:
            raise InvariantViolationError(f"{self.name} : un champ absent reste vide")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise InvariantViolationError(f"{self.name} : confiance hors de [0, 1]")

    @property
    def effective_value(self) -> str | None:
        """Valeur à utiliser : celle de l'humain si elle a corrigé l'extraction."""
        if self.review.state is ReviewState.CORRECTED:
            return self.review.value
        return self.value
