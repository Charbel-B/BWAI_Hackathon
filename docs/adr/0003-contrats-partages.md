# ADR 0003 : Contrats partagés

> Statut : accepté · Date : 2026-11-24 · Auteur : Ange-Marie

## Contexte

Quatre périmètres développés en parallèle doivent s'emboîter sans renégociation : extraction,
moteur métier, cycle de vie et API, frontend. Le sujet exige des montants exacts, aucune donnée
inventée, une facture validée immuable, une numérotation unique, l'idempotence et la gestion
des validations concurrentes.

## Options envisagées

| Option | Avantages | Inconvénients |
| --- | --- | --- |
| A. Chaque périmètre définit son interface en codant | Démarrage immédiat | Incompatibilités découvertes à l'intégration, la veille du rendu |
| B. Contrats écrits avant le code, dans `docs/contrats/` | Travail parallèle sans blocage ; tests écrits contre le contrat | Une heure de rédaction avant le code |

## Décision

**Option B.** Les décisions qui engagent plusieurs périmètres :

| Décision | Raison |
| --- | --- |
| Deux axes de statut : cycle de vie stocké (DRAFT, VALIDATED, ISSUED, DISCARDED, CANCELLED) et statut de paiement **dérivé** du solde | Le solde a une seule source : montant, avoirs et règlements. Aucune incohérence possible entre un statut stocké et les montants |
| Numéro attribué dans la transaction de validation | Ni trou ni doublon, même en cas d'échec ou de validations simultanées |
| Version entière et en-tête `If-Match` sur toute modification | Deux validations simultanées : une seule réussit, l'autre reçoit un conflit explicite |
| En-tête `Idempotency-Key` sur tout `POST` | Double clic, rejeu et reprise après coupure ne produisent qu'un seul effet |
| Montants et valeurs extraites transmis en chaînes décimales | Aucune perte de précision par les nombres flottants de JSON |
| Format unique de champ extrait (statut, valeur, texte d'origine, confiance, ancrage, revue) | L'écran de revue, le backend et l'évaluation fonctionnent avec n'importe quel extracteur |
| Erreurs au format `problem+json` avec un `code` stable | Le frontend réagit à un code, pas à un message |
| Empreinte de la configuration enregistrée sur chaque facture validée | On sait avec quelles règles chaque facture a été calculée |

## Conséquences

- Promis, Grâce, Charbel et Ange-Marie codent contre `docs/contrats/` dès maintenant.
- Les tests d'intégration vérifient le respect du contrat d'API.
- Changer un contrat passe par une PR relue par chaque responsable concerné.
