# Conventions de code frontend

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Ange-Marie

Cadriciel : React ([ADR 0004](../adr/0004-frontend-react.md)).

## Règles indépendantes du cadriciel

### Langage et outillage

- TypeScript en mode `strict`. `any` interdit ; `unknown` puis validation aux frontières.
- Formatage et analyse statique automatiques, configurés une seule fois à la racine du
  frontend. Aucune règle désactivée localement sans commentaire qui dit pourquoi.
- Dépendances verrouillées par le fichier de verrouillage versionné. Toute nouvelle dépendance
  est justifiée dans la PR et déclarée avec sa licence dans `THIRD_PARTY.md`.

### Contrat avec le backend

- Les types et le client d'API sont **générés** depuis le schéma OpenAPI du backend. Ils ne sont
  jamais écrits ni modifiés à la main.
- Le frontend **n'effectue aucun calcul métier**. Il affiche les montants, statuts et anomalies
  renvoyés par le backend. Un total recalculé côté client est un défaut, même s'il est juste.
- Toute action qui produit un effet envoie une clé d'idempotence générée côté client (voir
  [principes](principes.md#5-idempotence-par-défaut)).

### Nommage

- Identifiants en anglais, selon le [glossaire](../domaine/glossaire.md).
- Composants en `PascalCase` ; fonctions, variables et hooks en `camelCase` ; constantes en
  `UPPER_SNAKE_CASE`.
- Textes affichés en français, regroupés dans un seul module de libellés. Aucun texte en dur
  dans les composants.

### Composants

- Un composant a une responsabilité. Repère : 150 lignes au plus.
- Séparer l'affichage (composants sans état) de l'accès aux données (hooks ou services).
- Les états de l'interface sont explicites : chargement, vide, erreur, succès. Aucun écran ne
  reste blanc.

### Interface et accessibilité

- Les jetons de conception (couleurs, espacements, typographie) sont définis à un seul endroit.
  Aucune couleur en dur dans un composant.
- Contraste suffisant, navigation au clavier, libellés sur tous les champs de formulaire.
- L'incertitude de l'IA est visible sans ambiguïté : champ absent, confiance faible et champ
  corrigé par un humain ont chacun un rendu distinct.

## Règles propres au cadriciel

| Sujet | Règle |
| --- | --- |
| Structure | `src/app/` (assemblage, routes), `src/features/<fonctionnalité>/` (composants, hooks, tests d'une fonctionnalité), `src/api/` (client et types générés), `src/i18n/` (textes), `src/components/` (composants partagés) |
| Noms de fichiers | Minuscules et tirets : `health-status.tsx`, `use-health.ts` ; test à côté du fichier : `health-status.test.tsx` |
| Imports | Alias `@/` pour `src/` ; jamais de chemin relatif qui remonte de plus d'un niveau |
| Données serveur | Uniquement par TanStack Query et le client `api`. Pas de `fetch` direct dans un composant |
| État local | `useState` ou `useReducer` ; aucune bibliothèque d'état global sans ADR |
| Types de l'API | `make api-types` après tout changement du backend ; ne jamais modifier `src/api/schema.ts` |
| Commandes | `npm run lint`, `npm run typecheck`, `npm run format`, `npm test` (ou `make check test` à la racine) |
