"""Authentification par jeton porteur et contrôle des rôles."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, Request

from invoicing.api.errors import ApiError
from invoicing.application.ports import UserDirectory
from invoicing.domain.users import Role, User


def directory(request: Request) -> UserDirectory:
    """Annuaire branché par le bootstrap."""
    found: UserDirectory = request.app.state.users
    return found


def current_user(request: Request, authorization: Annotated[str | None, Header()] = None) -> User:
    """Utilisateur du jeton ; 401 si le jeton est absent, invalide ou expiré."""
    scheme, _, token = (authorization or "").partition(" ")
    user = directory(request).resolve_token(token) if scheme.lower() == "bearer" else None
    if user is None:
        raise ApiError(401, "UNAUTHENTICATED", "jeton absent ou invalide")
    return user


def require(role: Role) -> Callable[[User], User]:
    """Dépendance qui exige un rôle minimal ; 403 sinon."""

    def check(user: Annotated[User, Depends(current_user)]) -> User:
        if not user.has_role(role):
            raise ApiError(403, "FORBIDDEN", f"rôle {role} requis")
        return user

    return check


def if_match(if_match: Annotated[str | None, Header()] = None) -> int:
    """Version lue par le client, obligatoire sur toute modification."""
    try:
        return int((if_match or "").strip('"W/ '))
    except ValueError as error:
        raise ApiError(428, "PRECONDITION_REQUIRED", "en-tête If-Match obligatoire") from error


Operator = Annotated[User, Depends(require(Role.OPERATOR))]
Validator = Annotated[User, Depends(require(Role.VALIDATOR))]
Admin = Annotated[User, Depends(require(Role.ADMIN))]
Version = Annotated[int, Depends(if_match)]
