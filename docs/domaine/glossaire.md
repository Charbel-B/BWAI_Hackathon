# Glossaire

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Ange-Marie

Vocabulaire unique du projet. La colonne **Code** donne le nom à utiliser dans les identifiants,
en Python comme en TypeScript. Un terme qui n'est pas ici est ajouté avant d'être utilisé.

## Pièces et référentiels

| Terme | Code | Définition |
| --- | --- | --- |
| Pièce source | `SourceDocument` | Document reçu à partir duquel on prépare une facture : devis PDF, photo de bon de commande ou message texte |
| Devis | `Quote` | Proposition commerciale chiffrée envoyée au client |
| Bon de commande | `PurchaseOrder` | Commande ferme émise par le client |
| Bon de livraison | `DeliveryNote` | Pièce qui atteste les quantités réellement livrées |
| Client | `Customer` | Entreprise ou personne facturée, enregistrée dans le référentiel clients |
| Article | `Item` | Produit ou service vendu, avec son prix de référence, enregistré dans le référentiel articles |
| Référentiel | `Catalog` | Liste de référence (clients ou articles) contre laquelle on contrôle une pièce |
| Règles de calcul | `PricingRules` | Paramètres du calcul : taux de taxe, mode d'arrondi, ordre d'application des remises |

## Facture

| Terme | Code | Définition |
| --- | --- | --- |
| Facture | `Invoice` | Document qui réclame un paiement au client |
| Ligne de facture | `InvoiceLine` | Un article facturé avec sa quantité, son prix unitaire et sa remise |
| Remise | `Discount` | Réduction de prix, par ligne ou sur le total |
| Taxe | `Tax` | Prélèvement calculé sur une base selon un taux paramétré |
| Montant hors taxes | `net_amount` | Montant après remises, avant taxes |
| Montant toutes taxes comprises | `gross_amount` | Montant hors taxes plus taxes |
| Règlement | `Payment` | Paiement simulé reçu pour une facture, total ou partiel, avec sa référence fictive (mobile money ou autre) |
| Numéro de facture | `invoice_number` | Identifiant unique, attribué uniquement à la validation, sans trou ni doublon |
| Avoir | `CreditNote` | Document lié à une facture validée qui l'annule en tout ou partie |
| Brouillon | `InvoiceStatus.DRAFT` | Facture en préparation, modifiable, sans numéro |
| Validée | `InvoiceStatus.VALIDATED` | Facture approuvée par un humain, numérotée, non modifiable |
| Émise | `InvoiceStatus.ISSUED` | Facture validée envoyée au client par un canal simulé |
| Abandonnée | `InvoiceStatus.DISCARDED` | Brouillon abandonné, sans numéro consommé |
| Annulée | `InvoiceStatus.CANCELLED` | Facture entièrement annulée par un ou plusieurs avoirs validés |
| Solde | `balance` | Montant TTC moins avoirs validés moins règlements ; calculé, jamais stocké |
| Statut de paiement | `PaymentStatus` | `UNPAID`, `PARTIALLY_PAID` ou `PAID`, dérivé du solde |

Statuts et transitions : [cycle de vie](../contrats/cycle-de-vie.md).

## Extraction et contrôles

| Terme | Code | Définition |
| --- | --- | --- |
| Champ extrait | `ExtractedField` | Valeur lue dans une pièce source, avec son ancrage et sa confiance |
| Ancrage | `SourceAnchor` | Endroit de la pièce d'où vient une valeur : zone d'une image ou passage d'un texte |
| Confiance | `confidence` | Score entre 0 et 1 attaché à un champ extrait ; sous le seuil configuré, revue humaine obligatoire |
| Champ absent | `FieldStatus.MISSING` | Valeur introuvable dans la pièce ; elle reste vide et n'est jamais devinée |
| Anomalie | `Anomaly` | Incohérence détectée qui exige une revue humaine ; non résolue, elle bloque la validation |
| Écart de montant | `AmountMismatch` | Différence entre un montant lu dans la pièce et le montant recalculé par le moteur |

## Traçabilité et fiabilité

| Terme | Code | Définition |
| --- | --- | --- |
| Journal d'audit | `AuditLog` | Historique non modifiable des actions métier : qui, quoi, quand, sur quel document, valeurs avant et après |
| Clé d'idempotence | `idempotency_key` | Identifiant d'une action qui permet de la rejouer sans produire un second effet |
| Date de référence | `reference_date` | Date fixée qui rend les calculs reproductibles |
| Canal | `Channel` | Moyen d'envoi simulé : WhatsApp, SMS ou courriel |
| Émission simulée | `Dispatch` | Envoi fictif d'une facture validée sur un canal |
| Opérateur | `Role.OPERATOR` | Personne qui importe les pièces, revoit les champs et prépare les brouillons |
| Validateur | `Role.VALIDATOR` | Personne habilitée à valider une facture |
| Administrateur | `Role.ADMIN` | Personne habilitée à réinitialiser les données de démonstration |
