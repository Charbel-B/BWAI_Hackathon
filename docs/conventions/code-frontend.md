# Conventions de code frontend

> Statut : partiel · Mis à jour : 2026-11-24 · Responsable : Ange-Marie

Le cadriciel du frontend n'est pas encore choisi. Il sera fixé par un ADR après la matrice de
décision. Les règles ci-dessous valent quel que soit ce choix ; les règles propres au cadriciel
seront ajoutées à la section dédiée.

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

**[À COMPLÉTER]** après l'ADR de choix du frontend : structure des dossiers, gestion d'état,
routage, outils de test.
