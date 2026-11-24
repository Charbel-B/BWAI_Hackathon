# Point d'entrée unique des commandes du projet (ADR 0002).
BACKEND := backend
RUN := cd $(BACKEND) && uv run

.DEFAULT_GOAL := help
.PHONY: help install dev format check test

help: ## Afficher les commandes disponibles
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

install: ## Installer Python et les dépendances verrouillées
	cd $(BACKEND) && uv python install
	cd $(BACKEND) && uv sync --locked

dev: ## Lancer l'API en local sur http://localhost:8000 (rechargement automatique)
	$(RUN) uvicorn --factory invoicing.bootstrap:create_app --reload --port 8000

format: ## Formater le code et corriger ce qui peut l'être automatiquement
	$(RUN) ruff format
	$(RUN) ruff check --fix

check: ## Vérifier format, analyse statique, types et sens des dépendances
	$(RUN) ruff format --check
	$(RUN) ruff check
	$(RUN) mypy
	$(RUN) lint-imports

test: ## Lancer tous les tests avec la couverture
	$(RUN) pytest
