"""Utilisateurs et rôles."""

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    """Rôles, du moins au plus étendu. Un rôle couvre les droits des rôles précédents."""

    OPERATOR = "OPERATOR"
    VALIDATOR = "VALIDATOR"
    ADMIN = "ADMIN"


_RANK = {Role.OPERATOR: 0, Role.VALIDATOR: 1, Role.ADMIN: 2}


@dataclass(frozen=True, slots=True)
class User:
    """Compte authentifié."""

    id: str
    username: str
    display_name: str
    role: Role

    def has_role(self, minimal: Role) -> bool:
        """Vrai si le rôle de l'utilisateur couvre le rôle minimal demandé."""
        return _RANK[self.role] >= _RANK[minimal]
