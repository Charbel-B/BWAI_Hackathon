"""Seul endroit qui relie les ports à leurs adaptateurs selon la configuration."""

from importlib.metadata import version

from fastapi import FastAPI

from invoicing.api.app import AppInfo, create_api
from invoicing.infrastructure.config_files import config_sha256
from invoicing.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Point d'entrée de uvicorn : `uvicorn --factory invoicing.bootstrap:create_app`."""
    settings = settings or Settings()
    info = AppInfo(version=version("invoicing"), config_sha256=config_sha256(settings.config_dir))
    return create_api(info)
