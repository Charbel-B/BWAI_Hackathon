# Contribuer

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Ange-Marie

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
