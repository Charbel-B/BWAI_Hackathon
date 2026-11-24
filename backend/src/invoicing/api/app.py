"""Construction de l'application FastAPI. Les dépendances arrivent déjà assemblées."""

from dataclasses import dataclass

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

API_PREFIX = "/api/v1"


@dataclass(frozen=True, slots=True)
class AppInfo:
    """Informations exposées par l'état de santé."""

    version: str
    config_sha256: str


class HealthResponse(BaseModel):
    """Réponse de GET /api/v1/health."""

    status: str
    version: str
    config_sha256: str


def create_api(info: AppInfo) -> FastAPI:
    """Application HTTP. Chaque responsable ajoute son routeur ici."""
    app = FastAPI(title="Facturation assistée", version=info.version)
    router = APIRouter(prefix=API_PREFIX)

    @router.get("/health")
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=info.version, config_sha256=info.config_sha256)

    app.include_router(router)
    return app
