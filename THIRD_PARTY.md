# Composants tiers

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Ange-Marie

Toute dépendance ajoutée est déclarée ici dans la même PR. Versions exactes : `backend/uv.lock`.

| Composant | Usage | Licence |
| --- | --- | --- |
| FastAPI | API HTTP | MIT |
| Uvicorn | Serveur HTTP | BSD-3-Clause |
| Pydantic, pydantic-settings | Validation aux frontières, paramètres | MIT |
| PyYAML | Lecture de la configuration | MIT |
| pytest, pytest-cov | Tests et couverture (développement) | MIT |
| Hypothesis | Tests de propriétés (développement) | MPL-2.0 |
| HTTPX | Client de test de l'API (développement) | BSD-3-Clause |
| Ruff | Formatage et analyse statique (développement) | MIT |
| mypy, types-PyYAML | Vérification des types (développement) | MIT, Apache-2.0 |
| import-linter | Vérification du sens des dépendances (développement) | BSD-2-Clause |
