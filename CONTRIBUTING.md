# Contribuer

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Ange-Marie

## Prérequis

Développement sous Linux uniquement ([ADR 0002](docs/adr/0002-plateforme-linux.md)).

**Sous Windows** : ouvrir PowerShell en administrateur, lancer `wsl --install -d Ubuntu`,
redémarrer, ouvrir « Ubuntu » depuis le menu Démarrer. Toutes les commandes ci-dessous se
tapent ensuite dans ce terminal Ubuntu, et le dépôt se clone dans `~/`, jamais dans `C:\`.
Docker : installer Docker Desktop et activer « Use the WSL 2 based engine ».

| Outil | Installation | Vérification |
| --- | --- | --- |
| Git | `sudo apt install git` (Ubuntu, Debian) ou `sudo dnf install git` (Fedora) | `git --version` |
| GNU Make | `sudo apt install make` ou `sudo dnf install make` | `make --version` |
| uv (installe aussi Python) | `curl -LsSf https://astral.sh/uv/install.sh \| sh`, puis rouvrir le terminal | `uv --version` |
| Docker | [Docker Engine](https://docs.docker.com/engine/install/) | `docker compose version` |
| Node.js 24 | [nvm](https://github.com/nvm-sh/nvm) puis `nvm install 24`, ou le gestionnaire de paquets de la distribution | `node --version` |

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
5. Vérifier en local que tout passe : `make format check test`.
6. Ouvrir la PR en remplissant le modèle, avec Ange-Marie comme relecteur.
7. Corriger si Ange-Marie le demande. C'est lui qui fusionne en *Squash and merge*.
