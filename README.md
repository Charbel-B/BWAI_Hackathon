# Facturation assistée : de la pièce commerciale à la facture validée

> Statut : en construction · Mis à jour : 2026-11-24

Prototype réalisé pour le hackathon BWAI 2026, cas pratique 2 « Automatisation de la
facturation ». Il transforme une pièce commerciale (devis, bon de commande ou message) en
projet de facture vérifiable, contrôlé contre les référentiels, recalculé par un moteur
déterministe, validé par un humain, puis émis sur un canal simulé, avec un journal d'audit
complet.

## Installation et lancement

Prérequis : voir [CONTRIBUTING.md](CONTRIBUTING.md#prérequis).

```bash
make install   # installe Python 3.13 et les dépendances verrouillées
make dev       # API sur http://localhost:8000, documentation interactive sur /docs
make check     # format, analyse statique, types, sens des dépendances
make test      # tests et couverture
make help      # liste des commandes
```

Installation par Docker pour le jury : **[À COMPLÉTER]**.

## Documentation

- [Documentation du projet](docs/README.md)
- [Contribuer](CONTRIBUTING.md)

## Équipe

Ange-Marie, Promis, Charbel, Grâce. Rôles et périmètres : [docs/equipe/perimetres.md](docs/equipe/perimetres.md).
