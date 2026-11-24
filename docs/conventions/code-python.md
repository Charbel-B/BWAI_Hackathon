# Conventions de code Python

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Ange-Marie

S'applique au backend, au moteur métier et au pipeline IA. Les principes généraux sont dans
[principes.md](principes.md).

## Environnement

| Outil | Rôle | Commande |
| --- | --- | --- |
| [uv](https://docs.astral.sh/uv/) | Version de Python, environnement, dépendances, verrouillage | `uv sync`, `uv run ...` |
| [Ruff](https://docs.astral.sh/ruff/) | Formatage et analyse statique | `uv run ruff format`, `uv run ruff check` |
| [mypy](https://mypy.readthedocs.io/) | Vérification des types, en mode strict | `uv run mypy` |
| [import-linter](https://import-linter.readthedocs.io/) | Respect du sens des dépendances entre couches | `uv run lint-imports` |
| [pytest](https://docs.pytest.org/) | Tests (voir [tests.md](tests.md)) | `uv run pytest` |

- La version de Python est fixée dans `.python-version`. Le fichier `uv.lock` est versionné :
  tout le monde, CI comprise, installe exactement les mêmes versions.
- Ajouter une dépendance : `uv add <paquet>`, justifier le besoin dans la PR et la déclarer avec
  sa licence dans `THIRD_PARTY.md`.
- La configuration de ces outils est centralisée dans `pyproject.toml`. Aucune règle n'est
  désactivée localement sans un commentaire qui dit pourquoi.

## Nommage

- Identifiants en **anglais**, selon la correspondance du [glossaire](../domaine/glossaire.md).
  Un terme métier a un seul nom dans tout le code.
- [PEP 8](https://peps.python.org/pep-0008/) : `snake_case` pour modules, fonctions et
  variables ; `PascalCase` pour les classes ; `UPPER_SNAKE_CASE` pour les constantes.
- Un nom dit ce que la chose est ou fait : `compute_line_total`, pas `process` ni `helper`.
- Booléens en question : `is_validated`, `has_anomalies`.
- Commentaires et docstrings en **français**.

## Architecture et imports

Le découpage en couches est fixé par l'ADR d'architecture. La règle qui ne change pas : **le
cœur métier n'importe rien de l'extérieur** (ni base de données, ni FastAPI, ni réseau, ni
modèle d'IA). Cette règle est vérifiée par `import-linter` en CI.

- Imports absolus uniquement.
- Pas d'import circulaire, pas d'import dans une fonction sauf justification écrite.

## Types

- Toute fonction est entièrement typée, paramètres et retour. `mypy --strict` passe.
- `Any` est interdit, sauf à une frontière (lecture de fichier, réponse de modèle) où la valeur
  est aussitôt validée.
- Objets du cœur métier : `@dataclass(frozen=True, slots=True)`, donc immuables.
- Pydantic aux **frontières** uniquement : API, configuration, sortie du modèle d'IA.
- Les états et catégories sont des `enum.StrEnum`, jamais des chaînes libres.

## Montants, dates, identifiants

- **Jamais de `float` pour un montant.** On utilise `decimal.Decimal`, encapsulé dans le type
  montant du cœur métier. L'arrondi n'a lieu qu'aux endroits fixés par les règles de calcul,
  avec le mode d'arrondi défini en configuration.
- **Jamais `datetime.now()` ni `date.today()` dans le cœur métier.** L'heure vient d'une horloge
  injectée. Les calculs se reproduisent à l'identique avec une date de référence.
- Les dates et heures stockées sont en UTC et conscientes du fuseau. La conversion vers l'heure
  locale (Africa/Porto-Novo) se fait à l'affichage.
- Les identifiants sont générés en un seul endroit et ne changent jamais.

## Configuration

- Toute valeur métier (taux, seuil, arrondi, format de numérotation) vient de `config/`.
  Aucun nombre magique dans le code.
- Les paramètres techniques (chemins, clés, niveau de journalisation) viennent de variables
  d'environnement, lues par une seule classe `pydantic-settings`.
- La configuration est validée au démarrage. Invalide, l'application refuse de démarrer.

## Fonctions et modules

- Une fonction fait une chose. Repère : 30 lignes au plus. Au-delà, on découpe ou on explique.
- Un module a une responsabilité. Repère : 300 lignes au plus.
- Au plus 4 paramètres. Au-delà, un objet de paramètres.
- Pas d'état global modifiable. Les dépendances sont passées en paramètre ou injectées par
  FastAPI (`Depends`).
- Retour anticipé plutôt qu'imbrication profonde.

## Erreurs

- Chaque couche a ses exceptions, qui héritent d'une base commune du projet. Le cœur métier ne
  lève jamais d'erreur HTTP.
- Jamais de `except:` nu, jamais de `except Exception: pass`. Une erreur attrapée est traitée,
  ou relancée avec son contexte (`raise ... from err`).
- L'API traduit les erreurs du métier en réponses HTTP en un seul endroit.

## Journalisation

- Module `logging` standard, sortie structurée en JSON. Jamais de `print`.
- Chaque requête porte un identifiant de corrélation repris dans tous ses journaux.
- Niveaux : `DEBUG` détail de mise au point ; `INFO` événement normal ; `WARNING` situation
  anormale gérée ; `ERROR` échec d'une opération.
- Jamais de secret, de jeton ou de pièce complète dans un journal.
- Le journal technique ne remplace pas le **journal d'audit** métier, qui est une donnée du
  produit.

## Documentation du code

- Docstring sur toute fonction, classe et module publics, au format Google, en français.
- Un commentaire dit **pourquoi**, jamais **quoi**. Un code qui a besoin d'un commentaire pour
  dire ce qu'il fait est à renommer ou à découper.
- Pas de code commenté laissé dans le dépôt : Git s'en souvient.
- Pas de `TODO` sans numéro d'issue : `# TODO(#14): gérer la remise globale`.
