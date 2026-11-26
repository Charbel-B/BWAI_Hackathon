# Scénarios de démonstration

> Statut : en vigueur · Mis à jour : 2026-11-26 · Responsable : Charbel

Comptes de démonstration (`config/utilisateurs.yaml`) : `operateur` (`demo-operateur`) pour importer et corriger, `validateur` (`demo-validateur`) pour valider. Toutes les pièces sont 100 % fictives.

## 1. Scénario propre (`01-propre/piece.txt`)

- **Pièce** : commande structurée de `Entreprise Kpadonou et Fils` (`CLI-001`, 20 sacs de ciment + 10 barres de fer, Total HT 153 000 FCFA).
- **À l'écran** : extraction complète sans aucune anomalie (`0 bloquante`), totaux recalculés à 153 000 FCFA HT, 27 540 FCFA de TVA et 180 540 FCFA TTC.
- **Suite** : le validateur approuve directement, le numéro unique `FA-2026-00001` est attribué et l'émission simulée (`is_simulated: true`) est disponible.

## 2. Scénario à corriger (`02-a-corriger/piece.txt`)

- **Pièce** : commande de `Quincaillerie Le Bon Choix` (`CLI-002`, 15 feuilles de tôle ondulée) dont la date du document a été oubliée.
- **À l'écran** : le champ `document.date` apparaît `MISSING` avec l'anomalie bloquante `MISSING_REQUIRED_FIELD`, et toute tentative de validation est refusée (`422 VALIDATION_BLOCKED`).
- **Suite** : l'opérateur saisit `2026-11-25` sur `document.date`, le brouillon se recalcule automatiquement sans anomalie (92 040 FCFA TTC) et le validateur peut valider.

## 3. Scénario bloqué (`03-bloque/piece.txt`)

- **Pièce** : commande du client hors référentiel `Bâtiment Moderne du Golfe SARL` (30 sacs de ciment CPA 42.5) affichant un Total HT erroné de 100 000 FCFA au lieu de 186 000 FCFA.
- **À l'écran** : deux anomalies bloquantes s'affichent (`UNKNOWN_CUSTOMER` et `AMOUNT_MISMATCH`) pendant que le moteur impose le montant recalculé (186 000 FCFA HT, 219 480 FCFA TTC).
- **Suite** : la validation est strictement refusée (`422 VALIDATION_BLOCKED`) tant que les anomalies ne sont pas résolues avec justification écrite ou que le brouillon n'est pas abandonné.
