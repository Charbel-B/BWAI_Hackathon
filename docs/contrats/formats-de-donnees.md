# Formats des données et de la configuration

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Grâce

Tous les fichiers sont en UTF-8. Noms en minuscules, chiffres et tirets, sans accent ni espace.

## Référentiels

`data/referentiels/clients.csv`, séparateur `,`, une ligne d'en-tête :

| Colonne | Type | Exemple |
| --- | --- | --- |
| `id` | `CLI-` + 3 chiffres | `CLI-003` |
| `raison_sociale` | texte | `Boutique Akpro SARL` |
| `ifu` | 13 chiffres fictifs (`^\d{13}$`) | `3999900000011` |
| `telephone` | format béninois à 10 chiffres avec indicatif (`+22901XXXXXXXX`, espaces tolérés) | `+2290199990001` |
| `email` | texte, domaine `example` | `contact@akpro.example` |
| `canal_prefere` | `whatsapp`, `sms`, `email` | `whatsapp` |
| `delai_paiement_jours` | entier | `30` |
| `assujetti_tva` | `oui`, `non` | `oui` |

`data/referentiels/articles.csv` :

| Colonne | Type | Exemple |
| --- | --- | --- |
| `id` | `ART-` + 3 chiffres | `ART-012` |
| `designation` | texte | `Sac de ciment 50 kg` |
| `unite` | texte | `sac` |
| `prix_unitaire_ht` | entier, FCFA | `5500` |
| `taux_tva` | décimal en pourcentage | `18` |

## Pièces sources et valeurs attendues

```text
data/pieces/
├── mise-au-point/        pièces pour régler l'extraction
│   ├── p001.txt
│   ├── p001.attendu.json
│   ├── p002.pdf
│   └── p002.attendu.json
└── test/                 pièces réservées à l'évaluation finale, jamais utilisées pour régler
```

`<id>.attendu.json` donne la valeur attendue de chaque champ du
[format de champ extrait](champ-extrait.md), `null` pour un champ absent de la pièce, et les
anomalies que la pièce doit déclencher :

```json
{
  "fields": {
    "customer.name": "Boutique Akpro SARL",
    "document.date": "2026-11-20",
    "lines[0].label": "Sac de ciment 50 kg",
    "lines[0].quantity": "20",
    "lines[0].unit_price": "5500",
    "payment.terms_days": null
  },
  "expected_anomalies": ["UNUSUAL_PRICE"]
}
```

## Configuration métier

| Fichier | Contenu | Responsable |
| --- | --- | --- |
| `config/calcul.yaml` | Devise, taxes (code, libellé, taux), ordre d'application des remises, mode et niveau d'arrondi | Grâce |
| `config/controles.yaml` | Seuil de prix inhabituel, seuil de gros montant, gravité de chaque code d'anomalie | Grâce |
| `config/numerotation.yaml` | Formats des numéros de facture et d'avoir | Promis |
| `config/extraction.yaml` | Extracteur actif, modèle et version, seuil de confiance | Charbel |
| `config/canaux.yaml` | Canaux activés et modèles de message (`{numero}`, `{montant}`, `{echeance}`, `{client}`) | Charbel |
| `config/emetteur.yaml` | Identité de l'entreprise émettrice (fictive) : nom, adresse, IFU, téléphone, courriel ; lue par le PDF de l'API et la facture imprimable | Ange-Marie |
| `config/relances.yaml` | Seuil « bientôt due » et étapes de relance (code, libellé, décalage en jours par rapport à l'échéance, modèle de message) | Ange-Marie |
| `config/utilisateurs.yaml` | Comptes de démonstration : identifiant, nom, rôle, empreinte scrypt du mot de passe | Ange-Marie |
| `config/securite.yaml` | `separation_des_taches`, durée de validité du jeton | Promis |

Règle d'arrondi par défaut, à confirmer par Grâce : calcul en précision complète, arrondi à
l'unité de FCFA, au demi supérieur, sur le montant HT de chaque ligne puis sur chaque total de
taxe par taux ; le total TTC est la somme des montants arrondis.
