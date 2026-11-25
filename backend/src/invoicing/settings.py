"""Paramètres techniques, lus depuis l'environnement (préfixe INVOICING_)."""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/invoicing/settings.py -> racine du dépôt
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Seule classe qui lit les variables d'environnement."""

    model_config = SettingsConfigDict(env_prefix="INVOICING_", env_file=".env", extra="ignore")

    config_dir: Path = REPO_ROOT / "config"
    data_dir: Path = REPO_ROOT / "data"
    database_path: Path = REPO_ROOT / "var" / "invoicing.sqlite3"
    demo_mode: bool = True
    gemini_api_key: SecretStr = SecretStr("")
    log_level: str = "INFO"
