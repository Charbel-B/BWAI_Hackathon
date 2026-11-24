# Périmètres et responsables

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Ange-Marie

Ce document est la source unique de la répartition du travail. La colonne **Portée** donne la
portée à utiliser dans les messages de commit et les noms de branche
(voir [conventions Git](../conventions/git.md)).

## Équipe

| Membre | Rôle |
| --- | --- |
| Ange-Marie | Lead : architecture, conventions, contrats partagés, frontend, intégration |
| Promis | Backend : API, persistance, cycle de vie, intégrité |
| Charbel | IA : extraction, évaluation, fiche IA |
| Grâce | Métier : moteur de calcul, contrôles, référentiels, documents et canaux |

## Périmètres

| Id | Périmètre | Portée | Contenu | Responsable | Critères de la grille |
| --- | --- | --- | --- | --- | --- |
| A1 | Pipeline d'extraction | `extraction` | Lecture de la pièce source, champs extraits avec ancrage et confiance, repli hors connexion | Charbel (socle : Ange-Marie) | Automatisation |
| A2 | Évaluation IA | `evaluation` | Mesure de précision par champ, calibrage des seuils, fiche IA | Charbel | Automatisation |
| A3 | Interface de l'incertitude | `front` | Pièce et champs côte à côte, source surlignée, confiance visible, correction et confirmation | Ange-Marie | Automatisation, usage |
| B | Moteur métier | `metier` | Calcul (bases, remises, taxes, arrondis, totaux), contrôles et anomalies | Grâce | Fiabilité |
| C | Cycle de vie et intégrité | `cycle-de-vie` | Statuts, numérotation, avoirs, suivi des règlements simulés, idempotence, validations concurrentes, reprise, journal d'audit | Promis | Fiabilité, sécurité |
| D | Backend et API | `api` | API, persistance, migrations, authentification, rôles, journalisation technique | Promis | Technique, sécurité |
| E | Frontend | `front` | Écrans d'import, de revue, d'anomalies, de validation, de journal, tableau de bord | Ange-Marie | Usage, utilité |
| F | Documents et canaux | `documents` | Brouillon et facture en PDF, émission simulée (WhatsApp, SMS, courriel), référence mobile money fictive | Grâce | Utilité |
| G1 | Données métier | `donnees` | Référentiels clients et articles, règles de calcul, scénarios métier | Grâce | Fiabilité |
| G2 | Données d'évaluation | `donnees` | Pièces sources fictives et vérité terrain, séparation des jeux | Charbel | Automatisation |
| H | Outillage | `outillage` | Installation, conteneurs, intégration continue, qualité automatique | Ange-Marie | Technique |
| I | Documentation et livrables | `docs` | README, ADR, rapport, vidéo, comparaison à la référence | Ange-Marie (assemblage), chacun pour son périmètre | Usage, toutes |

## Règles

- Le responsable d'un périmètre relit en priorité les PR qui le touchent.
- Une PR qui touche deux périmètres est découpée, sauf si le changement est indivisible.
- Toute modification de ce tableau passe par une PR relue par Ange-Marie.
