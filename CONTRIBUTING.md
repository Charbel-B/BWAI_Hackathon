# Contribuer

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Ange-Marie

## Prérequis

Le projet fonctionne nativement sous Linux et sous Windows ([ADR 0002](docs/adr/0002-support-linux-et-windows.md)).

| Outil | Linux | Windows (PowerShell) |
| --- | --- | --- |
| Git | Gestionnaire de paquets de la distribution, par exemple `sudo apt install git` ou `sudo dnf install git` | `winget install --id Git.Git -e` |
| uv (installe aussi Python) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `winget install --id astral-sh.uv -e` |
| Node.js (frontend uniquement) | **[À COMPLÉTER]** après l'ADR du frontend | **[À COMPLÉTER]** après l'ADR du frontend |
| Docker (facultatif, installation de référence du jury) | Docker Engine | Docker Desktop |

Après installation, fermer puis rouvrir le terminal, et vérifier : `git --version` puis `uv --version`.

## À lire avant le premier commit

1. [Principes d'ingénierie](docs/conventions/principes.md)
2. [Conventions Git](docs/conventions/git.md)
3. Les conventions de code de son langage : [Python](docs/conventions/code-python.md) ou
   [frontend](docs/conventions/code-frontend.md)
4. [Tests](docs/conventions/tests.md) et [documentation](docs/conventions/documentation.md)
5. Son périmètre dans [périmètres](docs/equipe/perimetres.md) et le [glossaire](docs/domaine/glossaire.md)

## Cycle d'une tâche

1. Prendre ou créer l'issue, s'y assigner.
2. Créer la branche depuis `main` à jour : `git switch main && git pull && git switch -c feat/<portée>-<sujet>`.
3. Coder par commits atomiques au format Conventional Commits, tests compris.
4. Mettre à jour la documentation touchée.
5. Vérifier en local que tout passe : **[À COMPLÉTER]** commande unique de vérification, livrée
   avec le squelette.
6. Ouvrir la PR en remplissant le modèle et demander la revue au membre dont le travail dépend le plus de la tâche.
7. Corriger jusqu'à l'approbation. Le relecteur fusionne en *Squash and merge* et supprime la branche.
