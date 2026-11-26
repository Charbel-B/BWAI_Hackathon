"""Construction de l'application FastAPI. Les dépendances arrivent déjà assemblées."""

from dataclasses import dataclass

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from invoicing.api import routes_documents, routes_invoices, routes_public, routes_system
from invoicing.api.errors import install_error_handlers
from invoicing.api.idempotency import IdempotencyMiddleware
from invoicing.application.context import Context
from invoicing.application.ports import IdempotencyStore, UserDirectory

API_PREFIX = "/api/v1"


@dataclass(frozen=True, slots=True)
class AppInfo:
    """Informations exposées par l'état de santé."""

    version: str
    config_sha256: str


@dataclass(frozen=True, slots=True)
class Services:
    """Ce que le bootstrap branche derrière l'API."""

    context: Context
    users: UserDirectory
    idempotency: IdempotencyStore


class HealthResponse(BaseModel):
    """Réponse de GET /api/v1/health. `simulated` liste ce qui est simulé, sans détour."""

    status: str
    version: str
    config_sha256: str
    demo_mode: bool
    extractor: str
    simulated: list[str]


SIMULATED = ["canaux d'émission (WhatsApp, SMS, courriel)", "règlements mobile money"]


def create_api(info: AppInfo, services: Services) -> FastAPI:
    """Application HTTP."""
    app = FastAPI(title="Facturation assistée", version=info.version)
    router = APIRouter(prefix=API_PREFIX)

    @router.get("/health")
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=info.version,
            config_sha256=info.config_sha256,
            demo_mode=services.context.demo_mode,
            extractor=services.context.extractor.name,
            simulated=SIMULATED,
        )

    app.state.context = services.context
    app.state.users = services.users
    app.add_middleware(IdempotencyMiddleware, store=services.idempotency)
    install_error_handlers(app)
    router.include_router(routes_system.router)
    router.include_router(routes_documents.router)
    router.include_router(routes_invoices.router)
    router.include_router(routes_public.router)
    app.include_router(router)
    return app
