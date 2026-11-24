# Principes d'ingénierie

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Ange-Marie

Ces principes s'appliquent à tout le dépôt, quel que soit le langage. Les conventions par
langage ([Python](code-python.md), [frontend](code-frontend.md)) en sont la déclinaison.
En cas de doute sur une décision, on revient ici.

## 1. Source unique de vérité

Chaque information existe à un seul endroit. Tout le reste la lit ou en est généré.

| Information | Source unique | Lue ou générée par |
| --- | --- | --- |
| Règles métier chiffrées (taux, seuils, arrondis) | Fichiers de configuration du dossier `config/` | Moteur de calcul, contrôles, documentation |
| Contrat d'API | Schémas du backend (OpenAPI généré) | Types du frontend, générés, jamais écrits à la main |
| Vocabulaire métier | [Glossaire](../domaine/glossaire.md) | Noms dans le code, l'interface et la documentation |
| Périmètres et responsables | [Périmètres](../equipe/perimetres.md) | Portées des commits, revues, répartition |
| Décisions d'architecture | [ADR](../adr/README.md) | Code et documentation |

Une même valeur écrite à deux endroits est un défaut, même si les deux valeurs sont égales
aujourd'hui.

## 2. Configuration plutôt que code

Un changement de règle métier (taux de taxe, seuil de revue, modèle de numérotation, canal
d'émission) se fait en modifiant **un fichier de configuration**, jamais le code. La
configuration est validée au démarrage : une valeur invalide empêche l'application de démarrer
plutôt que de produire une facture fausse.

## 3. Cœur déterministe, IA en périphérie

- Le calcul, les contrôles, les statuts et la numérotation sont **déterministes** : même entrée,
  même sortie, toujours. Ils ne dépendent ni de l'heure système, ni du réseau, ni d'un modèle
  d'IA.
- L'IA **propose** (extraction de champs avec source et confiance) ; un humain **décide**
  (correction, confirmation, validation). Aucun montant n'est accepté sur la seule foi de l'IA :
  il est toujours recalculé par le moteur.
- Une donnée absente reste absente. Elle n'est jamais devinée.

## 4. Immuabilité et traçabilité

- Une facture validée ne change plus. Toute correction passe par un **avoir** lié, puis si
  besoin une nouvelle facture.
- Toute action qui change un état (import, correction, validation, émission, avoir) laisse une
  entrée dans le **journal d'audit** : qui, quoi, quand, sur quel document, avec quelles valeurs
  avant et après.

## 5. Idempotence par défaut

Toute opération qui produit un effet (créer, valider, émettre, enregistrer un paiement) peut être
rejouée sans produire un second effet : double clic, reprise après coupure, requête répétée,
validations simultanées. C'est une exigence de conception, pas un correctif ajouté après coup.

## 6. Réversibilité

- Chaque changement de schéma de base de données passe par une migration **réversible**.
- Chaque fonctionnalité se retire en annulant sa PR, sans effet de bord ailleurs.
- Les données de démonstration se réinitialisent en une commande.

## 7. Modularité

- Un module a une seule responsabilité et une interface publique explicite.
- Les dépendances vont toujours de l'extérieur vers le cœur : l'API dépend du métier, jamais
  l'inverse. Cette règle est vérifiée automatiquement (voir [Python](code-python.md#architecture-et-imports)).
- Un changement, petit ou gros, doit toucher le moins d'endroits possible. Si une modification
  simple exige de toucher cinq fichiers, c'est le découpage qui est à revoir.

## 8. Explicite plutôt qu'implicite

Pas de valeur magique, pas d'effet de bord caché, pas d'état global. Les dépendances (horloge,
stockage, modèle d'IA, canal d'émission) sont injectées, ce qui les rend remplaçables en test.

## 9. Le juste nécessaire

On construit ce que le sujet et la grille d'évaluation demandent, plus les bonus décidés en
équipe. On ne construit pas d'abstraction pour un besoin hypothétique.
