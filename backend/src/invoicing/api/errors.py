"""Traduction des erreurs métier en réponses application/problem+json (RFC 9457)."""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from invoicing.application.context import NotFoundError
from invoicing.domain.errors import (
    BusinessRuleError,
    DomainError,
    InvalidTransitionError,
    SeparationOfDutiesError,
    ValidationBlockedError,
    VersionConflictError,
)

PROBLEM = "application/problem+json"


class ApiError(Exception):
    """Erreur propre à la couche HTTP (authentification, en-tête manquant)."""

    def __init__(self, status: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status, self.code, self.detail = status, code, detail


def problem(status: int, code: str, detail: str, **extra: object) -> JSONResponse:
    """Corps d'erreur au format du contrat."""
    body = {"type": "about:blank", "title": code, "status": status, "code": code, "detail": detail}
    return JSONResponse({**body, **extra}, status_code=status, media_type=PROBLEM)


_DOMAIN_MAP: list[tuple[type[Exception], int, str]] = [
    (NotFoundError, 404, "NOT_FOUND"),
    (VersionConflictError, 409, "VERSION_CONFLICT"),
    (InvalidTransitionError, 409, "INVALID_TRANSITION"),
    (SeparationOfDutiesError, 403, "FORBIDDEN"),
    (BusinessRuleError, 422, "INVALID_INPUT"),
    (DomainError, 422, "INVALID_INPUT"),
]


def install_error_handlers(app: FastAPI) -> None:
    """Branche les traductions sur l'application."""

    @app.exception_handler(ApiError)
    async def _api(_: Request, error: ApiError) -> JSONResponse:
        return problem(error.status, error.code, error.detail)

    @app.exception_handler(ValidationBlockedError)
    async def _blocked(_: Request, error: ValidationBlockedError) -> JSONResponse:
        anomalies = [{"id": a.id, "code": a.code, "message": a.message} for a in error.anomalies]
        return problem(422, "VALIDATION_BLOCKED", str(error), anomalies=anomalies)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, error: RequestValidationError) -> JSONResponse:
        errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in error.errors()]
        return problem(422, "INVALID_INPUT", "requête invalide", errors=errors)

    for kind, status, code in _DOMAIN_MAP:
        app.add_exception_handler(kind, _handler(status, code))


def _handler(
    status: int, code: str
) -> Callable[[Request, Exception], Coroutine[Any, Any, JSONResponse]]:
    async def handle(_: Request, error: Exception) -> JSONResponse:
        return problem(status, code, str(error))

    return handle
