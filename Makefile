# Point d'entrée unique des commandes du projet (ADR 0002).
BACKEND := backend
FRONTEND := frontend
RUN := cd $(BACKEND) && uv run
NPM := cd $(FRONTEND) && npm
OPENAPI_JSON := $(FRONTEND)/src/api/openapi.json
OPENAPI_TS := $(FRONTEND)/src/api/schema.ts
OPENAPI_GEN := $(FRONTEND)/tools/openapi/node_modules/.bin/openapi-typescript

.DEFAULT_GOAL := help
.PHONY: help install dev dev-api dev-front api-types format check check-api test

help: ## Afficher les commandes disponibles
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-11s %s\n", $$1, $$2}'

install: ## Installer Python, Node et toutes les dépendances verrouillées
	cd $(BACKEND) && uv python install
	cd $(BACKEND) && uv sync --locked
	$(NPM) ci
	$(NPM) ci --prefix tools/openapi

dev: ## Lancer l'API (port 8000) et l'interface (port 5173) ensemble
	$(MAKE) -j2 dev-api dev-front

dev-api: ## Lancer l'API seule, avec rechargement automatique
	$(RUN) uvicorn --factory invoicing.bootstrap:create_app --reload --port 8000

dev-front: ## Lancer l'interface seule, avec rechargement automatique
	$(NPM) run dev

api-types: ## Régénérer les types du frontend depuis le contrat OpenAPI du backend
	$(RUN) python -c "import json; from invoicing.bootstrap import create_app; print(json.dumps(create_app().openapi(), indent=2, ensure_ascii=False))" > ../$(OPENAPI_JSON)
	$(OPENAPI_GEN) $(OPENAPI_JSON) -o $(OPENAPI_TS)

format: ## Formater le code et corriger ce qui peut l'être automatiquement
	$(RUN) ruff format
	$(RUN) ruff check --fix
	$(NPM) run format

check: check-api ## Vérifier format, analyse statique, types, dépendances et contrat d'API
	$(RUN) ruff format --check
	$(RUN) ruff check
	$(RUN) mypy
	$(RUN) lint-imports
	$(NPM) run format:check
	$(NPM) run lint
	$(NPM) run typecheck

check-api: api-types ## Échouer si les types du frontend ne correspondent plus au backend
	git diff --exit-code -- $(OPENAPI_JSON) $(OPENAPI_TS)

test: ## Lancer tous les tests (backend avec couverture, puis frontend)
	$(RUN) pytest
	$(NPM) test
