# Facturation assistée : de la pièce commerciale à la facture validée

> Statut : en construction · Mis à jour : 2026-11-25

Prototype réalisé pour le hackathon BWAI 2026, cas pratique 2 « Automatisation de la
facturation ». Il transforme une pièce commerciale (devis, bon de commande ou message) en
projet de facture vérifiable, contrôlé contre les référentiels, recalculé par un moteur
déterministe, validé par un humain, puis émis sur un canal simulé, avec un journal d'audit
complet.

## Installation et lancement

Prérequis : voir [CONTRIBUTING.md](CONTRIBUTING.md#prérequis).

```bash
make install   # installe Python 3.13 et les dépendances verrouillées
make dev       # interface sur http://localhost:5173, API sur http://localhost:8000 (documentation : /docs)
make check     # format, analyse statique, types, sens des dépendances
make test      # tests et couverture
make help      # liste des commandes
```

### Installation pour le jury (Docker)

Prérequis : Docker avec Docker Compose. Aucune autre installation.

```bash
docker compose up --build    # puis http://localhost:8080
docker compose down          # arrêt ; les données restent dans le volume « donnees »
```

L'API (Python) et l'interface (servie par nginx, qui relaie `/api` vers l'API) tournent dans
deux conteneurs. Déroulé de démonstration : [docs/demo/script.md](docs/demo/script.md).

## Comptes de démonstration

| Identifiant | Mot de passe | Rôle | Peut |
| --- | --- | --- | --- |
| `operateur` | `demo-operateur` | OPERATOR | Importer, revoir les champs, résoudre une anomalie, émettre, enregistrer un règlement |
| `validateur` | `demo-validateur` | VALIDATOR | Tout ce que fait l'opérateur, plus valider, créer et valider un avoir, lire le journal |
| `admin` | `demo-admin` | ADMIN | Tout, plus réinitialiser les données de démonstration |

La séparation des tâches est active (`config/securite.yaml`) : le validateur ne peut pas valider
un brouillon qu'il a lui-même créé.

## Ce qui est simulé

Les services extérieurs (WhatsApp, SMS, courriel, mobile money) sont simulés et signalés comme
tels ; l'extraction, le calcul, les contrôles, la numérotation et l'audit sont réels. Détail et
points de branchement : [ADR 0005](docs/adr/0005-simulation-des-integrations.md).

## Documentation

- [Documentation du projet](docs/README.md)
- [Contribuer](CONTRIBUTING.md)

## Équipe

Ange-Marie, Promis, Charbel, Grâce. Rôles et périmètres : [docs/equipe/perimetres.md](docs/equipe/perimetres.md).
