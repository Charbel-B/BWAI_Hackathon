# ADR 0001 : Architecture générale

> Statut : accepté · Date : 2026-11-24 · Auteur : Ange-Marie

## Contexte

- Le sujet exige un parcours complet et vérifiable : extraction d'une pièce, contrôles,
  recalcul déterministe, brouillon, validation humaine, numérotation, émission simulée, suivi des
  règlements, avoirs et piste d'audit.
- La grille attribue 60 points sur 100 à des propriétés déterministes (fiabilité 25,
  technique 20, sécurité 15) et 15 points à l'apport mesuré de l'IA.
- Le prototype doit s'installer et se rejouer à l'identique chez le jury, et supporter une
  connectivité faible.
- Quatre personnes travaillent en parallèle pendant moins de trois jours : les frontières entre
  périmètres doivent être nettes pour éviter les conflits.
- Aucune donnée n'est fournie : référentiels et règles doivent pouvoir être remplacés sans
  toucher au code.

## Options envisagées

| Option | Avantages | Inconvénients |
| --- | --- | --- |
| A. Application en couches simples (routes, services, modèles) | Rapide à démarrer | Le métier finit mêlé à la base et à FastAPI ; tests lents ; idempotence et IA dispersées |
| B. Ports et adaptateurs (hexagonale allégée), cœur métier pur | Métier testable sans base ni réseau ; IA, canaux, PDF et stockage remplaçables ; frontières de périmètres nettes | Un peu plus de structure à poser au départ |
| C. Microservices | Isolation maximale | Hors de proportion pour un prototype de trois jours ; installation plus fragile |

## Décision

**Option B : un dépôt unique, un backend Python en ports et adaptateurs avec un cœur métier
pur, un frontend séparé qui consomme le contrat OpenAPI.**

Le critère qui tranche : la fiabilité et la reproductibilité se prouvent par des tests rapides
sur un cœur sans dépendance externe, ce que seule l'option B garantit par construction.

| Sujet | Décision |
| --- | --- |
| Langage et cadriciel du backend | Python, FastAPI, Pydantic aux frontières |
| Persistance | SQLite en mode WAL, SQLAlchemy 2, migrations Alembic réversibles |
| Configuration métier | Fichiers YAML dans `config/`, validés au démarrage ; référentiels en CSV dans `data/` |
| Contrat d'API | REST JSON, schéma OpenAPI généré par FastAPI, client du frontend généré |
| Extraction IA | Un port `Extractor` ; un modèle réel en ligne ; un repli local réel hors ligne (lecture du texte et règles, ou petit modèle local), évalué séparément ; des réponses réelles enregistrées, réservées aux tests et à la sécurité de la démo, toujours signalées comme telles à l'écran. Aucune extraction simulée |
| Documents | Gabarit HTML rendu en PDF par le backend |
| Installation de référence | Docker Compose, une commande ; installation locale par uv pour le développement |
| Frontend | Choisi par un ADR dédié après matrice de décision |

Le détail de la structure, des couches et des flux est dans
[la vue d'ensemble de l'architecture](../architecture/vue-ensemble.md).

## Conséquences

- Le cœur métier (calcul, contrôles, règles du cycle de vie) se teste en millisecondes, sans
  base ni réseau. Les seuils de couverture de [tests.md](../conventions/tests.md) deviennent
  tenables.
- Le sens des dépendances est vérifié en CI par import-linter : une violation bloque la PR.
- SQLite sérialise les écritures : la numérotation sans trou et le refus des validations
  concurrentes s'obtiennent par transaction, sans serveur à installer. Le passage à PostgreSQL
  resterait possible par SQLAlchemy, hors périmètre du hackathon.
- Changer de modèle d'IA, de canal ou de gabarit revient à changer un adaptateur ou un fichier
  de configuration.
- Décisions qui restent à prendre, chacune par un ADR : choix du frontend, cycle de vie de la
  facture (statuts et transitions), format d'un champ extrait, authentification et rôles,
  modèle d'IA et sa version.
