"""Paramètres techniques, lus depuis l'environnement (préfixe INVOICING_)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/invoicing/settings.py -> racine du dépôt
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Seule classe qui lit les variables d'environnement."""

    model_config = SettingsConfigDict(env_prefix="INVOICING_", env_file=".env", extra="ignore")

    config_dir: Path = REPO_ROOT / "config"
    data_dir: Path = REPO_ROOT / "data"
    log_level: str = "INFO"
