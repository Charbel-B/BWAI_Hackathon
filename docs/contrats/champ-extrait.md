# Format d'un champ extrait

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Ange-Marie

Contrat entre le pipeline d'extraction (Charbel), le backend (Promis) et l'écran de revue
(Ange-Marie). Tout extracteur, en ligne, local ou rejoué, produit exactement ce format.

## Exemple

```json
{
  "name": "lines[0].quantity",
  "status": "FOUND",
  "value": "20",
  "raw_text": "20 sacs",
  "confidence": 0.93,
  "anchor": { "kind": "text", "start": 41, "end": 48 },
  "review": { "state": "PENDING", "value": null, "by": null, "at": null }
}
```

## Champs

| Champ | Type | Règle |
| --- | --- | --- |
| `name` | chaîne | Chemin du champ, parmi la liste ci-dessous |
| `status` | `FOUND`, `MISSING`, `AMBIGUOUS` | `MISSING` : rien dans la pièce. `AMBIGUOUS` : plusieurs valeurs possibles |
| `value` | chaîne ou `null` | Valeur normalisée. **Toujours une chaîne**, jamais un nombre JSON : `"5500"`, `"0.05"`, `"2026-11-20"`. `null` si `MISSING` |
| `raw_text` | chaîne ou `null` | Texte tel qu'il apparaît dans la pièce |
| `confidence` | nombre entre 0 et 1, ou `null` | `null` si `MISSING`. Sous le seuil de `config/extraction.yaml`, revue humaine obligatoire |
| `anchor` | objet ou `null` | Texte : `{"kind": "text", "start", "end"}` en positions de caractères. Image ou PDF : `{"kind": "region", "page", "box": [x0, y0, x1, y1]}`, coordonnées entre 0 et 1 |
| `review.state` | `PENDING`, `CONFIRMED`, `CORRECTED` | Décision humaine. `CORRECTED` : `review.value` remplace `value` |
| `review.by`, `review.at` | chaîne, date ISO 8601 | Auteur et moment de la décision |

## Champs attendus

| Nom | Obligatoire | Normalisation |
| --- | --- | --- |
| `customer.name` | oui | Texte |
| `customer.tax_id` | non | 13 chiffres |
| `document.reference` | non | Texte (numéro de devis ou de commande) |
| `document.date` | oui | `AAAA-MM-JJ` |
| `lines[i].label` | oui | Texte |
| `lines[i].quantity` | oui | Décimal, point comme séparateur |
| `lines[i].unit` | non | Texte |
| `lines[i].unit_price` | oui | Décimal en FCFA |
| `lines[i].discount_rate` | non | Décimal entre 0 et 1 |
| `discount.global_rate` | non | Décimal entre 0 et 1 |
| `payment.terms_days` ou `payment.due_date` | non | Entier, ou `AAAA-MM-JJ` |
| `totals.net`, `totals.vat`, `totals.gross` | non | Décimal ; comparés aux montants recalculés |

Un champ obligatoire absent reste `MISSING` et crée l'anomalie `MISSING_REQUIRED_FIELD`
jusqu'à sa saisie par un humain. **Aucun extracteur ne complète une valeur absente.**
