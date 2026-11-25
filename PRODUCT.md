# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Opérateur de saisie** d'une PME béninoise : reçoit des devis, bons de commande et messages
  clients, et doit en tirer des factures justes sans tout ressaisir.
- **Responsable de validation** : vérifie, valide et numérote les factures, suit les
  règlements et émet les avoirs.
- **Jury du hackathon BWAI 2026** : évalue la fiabilité, la qualité technique, la sécurité et
  l'apport mesuré de l'IA lors d'une démonstration en direct.

## Product Purpose

Transformer une pièce commerciale en facture vérifiable : extraction des champs, revue humaine
de ce qui est incertain, contrôles contre les référentiels, recalcul déterministe, validation
avec numéro unique, émission et suivi des règlements. Réussir, c'est qu'aucune facture validée
ne contienne une donnée inventée ou un montant faux.

## Positioning

L'IA propose, l'humain décide, le moteur calcule. Chaque valeur extraite montre d'où elle vient
dans la pièce et à quel point elle est sûre ; ce qui est absent reste visiblement absent.

## Operating Context

Pièces texte (devis, commandes, messages WhatsApp recopiés), montants en FCFA, TVA à 18 %,
clients avec IFU. Démonstration en direct sur un ordinateur portable, en français.

## Capabilities and Constraints

- Parcours complet exposé par l'API `/api/v1` (voir `docs/contrats/api.md`).
- Rôles : OPERATOR, VALIDATOR, ADMIN ; séparation des tâches active.
- Le frontend n'effectue aucun calcul métier ; il affiche ce que renvoie l'API.
- Canaux d'émission et règlements mobile money simulés, affichés comme tels (ADR 0005).
- Nom commercial du produit : **[À COMPLÉTER]**.

## Brand Commitments

Références de direction artistique fournies le 26/11/2026 : Oravieo (site dentaire), Stride
(application sportive), Catalis / Aeline (gabarit Webflow). À interpréter, jamais copier.

## Evidence on Hand

- 16 pièces fictives et leurs valeurs attendues : `data/pieces/`.
- Évaluation chiffrée de l'extraction : `docs/ia/fiche-ia.md`.
- Aucun client réel, aucun témoignage : rien de tel ne doit être inventé.

## Product Principles

1. L'incertitude se voit : absent, incertain, corrigé par un humain et confirmé ont chacun un
   rendu distinct.
2. La source d'abord : toute valeur renvoie à son passage dans la pièce.
3. Rien d'irréversible sans un humain : la validation et l'avoir sont des gestes explicites.
4. Ce qui est simulé le dit.

## Accessibility & Inclusion

Contraste AA, navigation complète au clavier, états jamais portés par la couleur seule.
