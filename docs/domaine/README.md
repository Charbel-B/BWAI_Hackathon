# Domaine métier

> Statut : en vigueur · Mis à jour : 2026-11-26 · Responsable : Ange-Marie

Description du métier de la facturation tel que le projet le modélise.

| Document | Contenu |
| --- | --- |
| [glossaire.md](glossaire.md) | Vocabulaire unique du projet et nom de chaque terme dans le code |

Modèle de domaine, cycle de vie et formats : [contrats partagés](../contrats/README.md).

Règles de calcul : `backend/src/invoicing/domain/calculation.py` et `config/calcul.yaml`.
Contrôles et anomalies : `backend/src/invoicing/domain/controls.py` et `config/controles.yaml`.
Relances : `backend/src/invoicing/domain/collection.py` et `config/relances.yaml`.
