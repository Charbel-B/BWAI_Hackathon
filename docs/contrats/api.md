# Contrat d'API

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Promis

Préfixe : `/api/v1`. JSON en entrée et en sortie, sauf envoi de fichier et PDF. Le schéma
OpenAPI généré par FastAPI fait foi une fois le code écrit ; ce document en est la référence de
départ et reste à jour avec lui.

## Règles communes

| Règle | Détail |
| --- | --- |
| Authentification | Jeton porteur (`Authorization: Bearer ...`) obtenu par `POST /auth/login` |
| Montants | Chaînes décimales : `"12500"`. Jamais de nombre JSON pour un montant |
| Dates | ISO 8601, UTC pour les horodatages |
| Idempotence | En-tête `Idempotency-Key` obligatoire sur tout `POST` qui produit un effet |
| Concurrence | En-tête `If-Match: <version>` obligatoire sur toute modification de facture ou d'avoir |
| Erreurs | Format `application/problem+json` (RFC 9457) avec un champ `code` stable |

## Points d'accès

| Méthode et chemin | Rôle minimal | Effet |
| --- | --- | --- |
| `POST /auth/login` | aucun | Renvoie un jeton |
| `GET /auth/me` | tous | Utilisateur courant et rôle |
| `POST /source-documents` | OPERATOR | Envoi d'une pièce (multipart), extraction lancée, résultat renvoyé |
| `GET /source-documents/{id}` | OPERATOR | Pièce, résultat d'extraction et champs |
| `GET /source-documents/{id}/file` | OPERATOR | Fichier original, pour l'affichage côte à côte |
| `POST /source-documents/{id}/fields/{name}/review` | OPERATOR | Confirmer ou corriger un champ : `{"action": "confirm"}` ou `{"action": "correct", "value": "..."}` |
| `POST /invoices` | OPERATOR | Créer un brouillon depuis une pièce : `{"source_document_id": "..."}` |
| `GET /invoices` | OPERATOR | Liste filtrable par statut |
| `GET /invoices/{id}` | OPERATOR | Facture, totaux, anomalies, statut de paiement |
| `PATCH /invoices/{id}` | OPERATOR | Corriger un brouillon |
| `POST /invoices/{id}/anomalies/{anomaly_id}/resolve` | OPERATOR | Résoudre avec justification |
| `POST /invoices/{id}/validate` | VALIDATOR | Valider et numéroter |
| `POST /invoices/{id}/discard` | OPERATOR | Abandonner un brouillon |
| `POST /invoices/{id}/dispatch` | OPERATOR | Émettre sur un canal : `{"channel": "whatsapp"}` |
| `GET /invoices/{id}/pdf` | OPERATOR | Brouillon ou facture en PDF ; un brouillon porte la mention BROUILLON |
| `POST /invoices/{id}/payments` | OPERATOR | Enregistrer un règlement simulé |
| `POST /invoices/{id}/credit-notes` | VALIDATOR | Créer un avoir en brouillon |
| `POST /credit-notes/{id}/validate` | VALIDATOR | Valider et numéroter l'avoir |
| `GET /audit-log` | VALIDATOR | Journal filtrable par entité |
| `GET /audit-log/verify` | VALIDATOR | Vérifie la chaîne d'empreintes du journal |
| `POST /admin/reset` | ADMIN | Réinitialise les données de démonstration ; désactivé hors mode démonstration |

## Codes d'erreur

| HTTP | `code` | Cas |
| --- | --- | --- |
| 401 | `UNAUTHENTICATED` | Jeton absent ou invalide |
| 403 | `FORBIDDEN` | Rôle insuffisant, ou validateur auteur du brouillon |
| 404 | `NOT_FOUND` | Ressource inconnue |
| 409 | `VERSION_CONFLICT` | `If-Match` différent de la version courante |
| 409 | `IDEMPOTENCY_KEY_REUSED` | Même clé, contenu différent |
| 409 | `INVALID_TRANSITION` | Transition interdite depuis le statut courant |
| 422 | `VALIDATION_BLOCKED` | Anomalies bloquantes ouvertes ; la liste est dans la réponse |
| 422 | `INVALID_INPUT` | Corps de requête invalide |
