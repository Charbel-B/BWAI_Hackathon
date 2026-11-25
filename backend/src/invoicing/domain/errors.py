"""Exceptions du cœur métier. Aucune ne porte de notion HTTP : l'API les traduit."""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from invoicing.domain.invoice import Anomaly


class DomainError(Exception):
    """Base de toutes les erreurs métier."""


class InvariantViolationError(DomainError):
    """Un objet métier serait créé dans un état interdit par les contrats."""


class InvalidTransitionError(DomainError):
    """Transition de statut interdite depuis le statut courant."""


class VersionConflictError(DomainError):
    """La version envoyée n'est plus la version courante : quelqu'un a modifié entre-temps."""


class SeparationOfDutiesError(DomainError):
    """Le validateur est l'auteur du brouillon alors que la séparation des tâches est active."""


class BusinessRuleError(DomainError):
    """Demande contraire à une règle métier (règlement supérieur au solde, avoir trop élevé)."""


class ValidationBlockedError(DomainError):
    """Des anomalies bloquantes sont encore ouvertes."""

    def __init__(self, anomalies: Sequence["Anomaly"]) -> None:
        super().__init__("anomalies bloquantes ouvertes")
        self.anomalies = tuple(anomalies)
