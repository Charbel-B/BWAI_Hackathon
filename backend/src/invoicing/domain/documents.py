"""Pièce source et résultat de son extraction."""

from dataclasses import dataclass, replace
from datetime import datetime

from invoicing.domain.errors import InvariantViolationError
from invoicing.domain.extraction import ExtractedField, Review, ReviewState


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """Pièce reçue (devis, bon de commande, message) et ses champs extraits."""

    id: str
    filename: str
    media_type: str
    file_sha256: str
    received_at: datetime
    uploaded_by: str
    extractor: str
    fields: tuple[ExtractedField, ...]

    def field(self, name: str) -> ExtractedField:
        """Champ par son nom ; une erreur si le nom est inconnu."""
        for f in self.fields:
            if f.name == name:
                return f
        raise InvariantViolationError(f"champ inconnu : {name}")


def review_field(
    document: SourceDocument,
    name: str,
    *,
    corrected_value: str | None,
    by: str,
    at: datetime,
) -> SourceDocument:
    """Confirme (sans valeur) ou corrige (avec valeur) un champ. Un humain peut aussi
    saisir un champ que l'extraction n'a pas trouvé : c'est une correction."""
    document.field(name)
    state = ReviewState.CONFIRMED if corrected_value is None else ReviewState.CORRECTED
    if state is ReviewState.CONFIRMED and document.field(name).value is None:
        raise InvariantViolationError(f"{name} : impossible de confirmer un champ vide")
    review = Review(state=state, value=corrected_value, by=by, at=at)
    fields = tuple(replace(f, review=review) if f.name == name else f for f in document.fields)
    return replace(document, fields=fields)


def add_field(document: SourceDocument, field: ExtractedField) -> SourceDocument:
    """Ajoute un champ absent de l'extraction (par exemple une ligne oubliée)."""
    if any(f.name == field.name for f in document.fields):
        raise InvariantViolationError(f"champ déjà présent : {field.name}")
    return replace(document, fields=(*document.fields, field))
