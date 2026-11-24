# ADR 0004 : Frontend en React

> Statut : accepté · Date : 2026-11-24 · Auteur : Ange-Marie

## Contexte

L'interface doit afficher la pièce source à côté des champs extraits en surlignant leur origine,
consommer l'API avec des types générés depuis le contrat OpenAPI, fonctionner avec une
connexion faible, et atteindre un niveau de finition visuelle élevé.

## Options envisagées

Notes de 1 à 5, sous-total hors maîtrise de l'équipe, sur 75 points.

| Critère (poids) | React + Vite | Vue 3 + Vite | SvelteKit | HTMX |
| --- | --- | --- | --- | --- |
| Composants pour la pièce côte à côte (20) | 5 | 4 | 3 | 2 |
| Composants d'interface accessibles (15) | 5 | 4 | 3 | 2 |
| Client d'API typé généré (15) | 5 | 5 | 5 | 1 |
| Hors connexion (10) | 5 | 5 | 4 | 2 |
| Documentation et aide disponible (10) | 5 | 4 | 3 | 3 |
| Tests de bout en bout (5) | 5 | 5 | 5 | 4 |
| **Total** | **75** | **66** | **55** | **31** |

## Décision

**React avec Vite et TypeScript strict.**

| Rôle | Outil |
| --- | --- |
| Base | Vite, React, TypeScript strict (`noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`) |
| Données serveur | TanStack Query |
| Client d'API | `openapi-fetch`, typé par `openapi-typescript` (`make api-types`) |
| Navigation | React Router |
| Styles | Tailwind CSS ; jetons de conception définis avec la direction artistique |
| Qualité | oxlint, Prettier |
| Tests | Vitest, Testing Library ; Playwright pour les scénarios |

## Conséquences

- Les types de l'API sont générés et versionnés dans `frontend/src/api/`. `make check` échoue si
  le backend change sans régénération : le frontend ne peut pas diverger du contrat.
- `openapi-typescript` exige TypeScript 5 alors que le frontend utilise TypeScript 7 : le
  générateur est isolé dans `frontend/tools/openapi/`, avec ses propres dépendances verrouillées.
- Bibliothèque de composants, lecteur de pièce et mode hors connexion : choisis avec la direction
  artistique, déclarés dans `THIRD_PARTY.md` à leur ajout.
