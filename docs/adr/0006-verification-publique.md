# ADR 0006 : Vérification publique d'une facture par QR code

> Statut : accepté · Date : 2026-11-26 · Auteur : Ange-Marie

## Contexte

Une facture papier ou PDF se falsifie facilement : montant retouché, faux numéro. Le client qui
la reçoit n'a aujourd'hui aucun moyen de vérifier qu'elle est authentique. Le prototype tient déjà
un journal d'audit chaîné par empreintes ; il peut servir de preuve.

## Options envisagées

| Option | Avantages | Inconvénients |
| --- | --- | --- |
| A. Aucune vérification externe | Rien à exposer | Aucun moyen pour le client de détecter une fausse facture |
| B. Page publique protégée par un code tiré de l'empreinte du contenu | Le client vérifie sans compte ; sans le code, rien n'est révélé | Une route sans authentification à surveiller |
| C. Compte client obligatoire | Accès nominatif | Personne ne crée un compte pour vérifier une facture |

## Décision

Option B. À la validation, le domaine calcule l'empreinte SHA-256 du contenu de la facture
(numéro, client, dates, lignes, totaux, empreinte des règles) ; elle est stockée sur la facture et
inscrite dans l'entrée d'audit `invoice.validated`. Le QR code porte l'identifiant de la facture et
les 16 premiers caractères de cette empreinte.

`GET /api/v1/public/verify/{invoice_id}?code=...`, sans authentification, rend :

| Verdict | Condition |
| --- | --- |
| `AUTHENTIC` | Code juste ; empreinte recalculée = empreinte stockée = empreinte journalisée ; chaîne du journal intacte |
| `CANCELLED` | Comme ci-dessus, mais la facture est annulée par avoir |
| `ALTERED` | Code juste, mais une des trois empreintes ou la chaîne ne concorde plus |
| `UNKNOWN` | Facture absente, non validée ou code faux : aucune donnée n'est rendue |

## Conséquences

- Seuls le numéro, le client, la date, le montant TTC, la date de validation, l'empreinte et l'état
  du journal sont exposés, et seulement avec le bon code.
- Le statut de cycle de vie n'entre pas dans l'empreinte : émettre ou régler une facture ne la rend
  pas « altérée ».
- Une facture validée avant l'ajout de l'empreinte n'a pas de code de vérification.
