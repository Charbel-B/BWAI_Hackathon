# Conventions de tests

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Ange-Marie

La grille d'évaluation réserve 20 points aux tests automatisés et à la reproductibilité, et
25 points à l'exactitude des calculs, des statuts et de l'idempotence. Les tests sont la preuve
de ces deux critères.

## Niveaux de tests

| Niveau | Ce qui est testé | Outils | Où |
| --- | --- | --- | --- |
| Unitaire | Une fonction ou une classe du cœur métier, isolée | pytest | `tests/unit/` |
| Propriétés | Des invariants du calcul vérifiés sur des milliers d'entrées générées | Hypothesis | `tests/unit/` |
| Intégration | API + base de données + métier ensemble, sur une base jetable | pytest, client de test FastAPI | `tests/integration/` |
| Scénarios | Les parcours de démonstration de bout en bout, dont la reprise après interruption | **[À COMPLÉTER]** selon le choix du frontend | `tests/e2e/` |

L'**évaluation de l'IA** n'est pas un test : c'est une mesure (précision par champ, erreurs
observées), lancée par une commande séparée et publiée dans la fiche IA. Les tests, eux, ne
dépendent jamais d'un modèle réel.

## Règles

- **Déterministes** : horloge figée, graines aléatoires fixées, aucun appel réseau. Le modèle
  d'IA est remplacé par une réponse enregistrée.
- **Indépendants** : chaque test prépare ses données et ne dépend d'aucun autre ni de leur ordre.
- **Lisibles** : structure *préparer, agir, vérifier*. Nom qui décrit le comportement attendu :
  `test_validated_invoice_cannot_be_modified`.
- **Un défaut corrigé = un test** qui échouait avant la correction et passe après.
- Les jeux de données de test viennent du dossier de données du projet, jamais de valeurs
  recopiées dans plusieurs tests.

## Ce qui doit être couvert

| Exigence | Exemples de tests attendus |
| --- | --- |
| Calcul exact | Remises, taxes, arrondis, totaux ; invariants : total = somme des lignes, avoir total = facture annulée |
| Contrôles | Client inconnu, doublon, prix inhabituel, incohérence entre pièces, écart commandé et livré |
| Données absentes | Un champ absent n'est jamais rempli par une valeur inventée |
| Cycle de vie | Transitions autorisées et interdites ; facture validée non modifiable ; anomalie non résolue bloquante |
| Idempotence | Double validation, double émission, rejeu après coupure : un seul effet |
| Concurrence | Deux validations simultanées : une seule réussit, numérotation sans trou ni doublon |
| Sécurité | Chaque rôle n'accède qu'à ses actions |

## Seuils de couverture

| Zone | Couverture minimale des lignes |
| --- | --- |
| Cœur métier (calcul, contrôles, cycle de vie) | 95 % |
| Ensemble du backend | 80 % |

Les seuils sont vérifiés en CI. Une PR qui les fait baisser ne passe pas.

## Commandes

| Commande | Effet |
| --- | --- |
| `make test` | Tous les tests, avec couverture ; échoue sous 80 % |
| `cd backend && uv run pytest tests/unit` | Tests unitaires seuls |
| `cd backend && uv run pytest tests/integration` | Tests d'intégration seuls |

Commande d'évaluation de l'IA : **[À COMPLÉTER]** par Charbel.
