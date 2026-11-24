"""Exceptions du cœur métier."""


class DomainError(Exception):
    """Base de toutes les erreurs métier. Ne porte jamais de notion HTTP."""


class InvariantViolationError(DomainError):
    """Un objet métier serait créé dans un état interdit par les contrats."""
