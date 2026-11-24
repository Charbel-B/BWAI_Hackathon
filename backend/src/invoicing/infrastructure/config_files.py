"""Lecture des fichiers de configuration métier et calcul de leur empreinte."""

import hashlib
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATTERN = "*.yaml"


def config_files(config_dir: Path) -> list[Path]:
    """Fichiers de configuration, dans un ordre stable."""
    return sorted(config_dir.glob(CONFIG_PATTERN))


def config_sha256(config_dir: Path) -> str:
    """Empreinte de l'ensemble de la configuration, enregistrée sur chaque facture validée.

    Le nom de chaque fichier entre dans l'empreinte : renommer un fichier la change aussi.
    """
    digest = hashlib.sha256()
    for path in config_files(config_dir):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def load_config(config_dir: Path) -> dict[str, Any]:
    """Contenu brut de chaque fichier, indexé par son nom sans extension.

    La validation par fichier est ajoutée par le responsable de chaque fichier.
    """
    loaded: dict[str, Any] = {}
    for path in config_files(config_dir):
        with path.open(encoding="utf-8") as handle:
            loaded[path.stem] = yaml.safe_load(handle)
    return loaded
