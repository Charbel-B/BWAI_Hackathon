# Contrat d'API

> Statut : en vigueur · Mis à jour : 2026-11-26 · Responsable : Ange-Marie

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
| `POST /source-documents` | OPERATOR | Envoi d'une pièce (multipart, champ `file`, 2 Mo au plus) ; extraction, puis brouillon créé dans la même transaction ; renvoie la pièce et le brouillon |
| `GET /source-documents/{id}` | OPERATOR | Pièce, résultat d'extraction et champs |
| `GET /source-documents/{id}/file` | OPERATOR | Fichier original, pour l'affichage côte à côte |
| `POST /source-documents/{id}/fields/{name}/review` | OPERATOR | Confirmer ou corriger un champ : `{"action": "confirm"}` ou `{"action": "correct", "value": "..."}`. Un champ absent peut être saisi par `correct`. Les brouillons de la pièce sont recalculés (version + 1) |
| `POST /invoices` | OPERATOR | Nouveau brouillon depuis une pièce déjà importée (par exemple après un avoir total) : `{"source_document_id": "..."}` |
| `GET /invoices` | OPERATOR | Liste filtrable par statut |
| `GET /invoices/{id}` | OPERATOR | Facture, totaux, anomalies, statut de paiement, `verification_code` (code du QR, une fois validée) |
| `POST /invoices/{id}/anomalies/{anomaly_id}/resolve` | OPERATOR | Résoudre avec justification |
| `POST /invoices/{id}/validate` | VALIDATOR | Valider et numéroter |
| `POST /invoices/{id}/discard` | OPERATOR | Abandonner un brouillon |
| `POST /invoices/{id}/dispatch` | OPERATOR | Émettre sur un canal : `{"channel": "whatsapp"}` |
| `GET /invoices/{id}/pdf` | OPERATOR | Brouillon ou facture en PDF ; mention BROUILLON sur un brouillon, code et lien de vérification d'authenticité sur une facture validée |
| `POST /invoices/{id}/payments` | OPERATOR | Enregistrer un règlement simulé : `{"amount": "5000", "method": "mobile_money"}` |
| `POST /invoices/{id}/credit-notes` | VALIDATOR | Créer un avoir en brouillon : `{"reason": "..."}` pour un avoir total, ou avec `"lines": [{"line_index": 0, "quantity": "2"}]` |
| `POST /credit-notes/{id}/validate` | VALIDATOR | Valider et numéroter l'avoir |
| `GET /issuer` | OPERATOR | Identité de l'émetteur (`config/emetteur.yaml`), pour l'en-tête des factures |
| `GET /audit-log` | VALIDATOR | Journal filtrable par entité |
| `GET /audit-log/verify` | VALIDATOR | Vérifie la chaîne d'empreintes du journal |
| `POST /assistant/ask` | OPERATOR | Nera, l'assistant ([ADR 0007](../adr/0007-copilote-ancre.md)) : `{"question", "invoice_id"?}` ; rend `intent`, `answer`, `sources`, `actions`, `engine` |
| `GET /receivables` | OPERATOR | Échéancier des factures validées non soldées : situation (`OVERDUE`, `DUE_SOON`, `NOT_DUE`, `NO_DUE_DATE`), jours de retard, prochaine relance, relances envoyées, totaux et étapes configurées |
| `POST /invoices/{id}/reminders` | OPERATOR | Envoie la relance due aujourd'hui sur le canal préféré du client (simulé) ; 422 si aucune n'est due |
| `GET /public/verify/{invoice_id}?code=...` | aucun | Vérification publique d'une facture validée ([ADR 0006](../adr/0006-verification-publique.md)) : `AUTHENTIC`, `CANCELLED`, `ALTERED` ou `UNKNOWN` |
| `POST /admin/reset` | ADMIN | Réinitialise les données de démonstration ; désactivé hors mode démonstration |

Une correction de brouillon passe toujours par la revue d'un champ de la pièce : la pièce reste
la source unique du contenu, et le brouillon en est recalculé.

## Codes d'erreur

| HTTP | `code` | Cas |
| --- | --- | --- |
| 401 | `UNAUTHENTICATED` | Jeton absent ou invalide |
| 403 | `FORBIDDEN` | Rôle insuffisant, ou validateur auteur du brouillon |
| 404 | `NOT_FOUND` | Ressource inconnue |
| 428 | `PRECONDITION_REQUIRED` | En-tête `If-Match` absent sur une modification |
| 409 | `VERSION_CONFLICT` | `If-Match` différent de la version courante |
| 409 | `IDEMPOTENCY_KEY_REUSED` | Même clé, contenu différent |
| 409 | `INVALID_TRANSITION` | Transition interdite depuis le statut courant |
| 422 | `VALIDATION_BLOCKED` | Anomalies bloquantes ouvertes ; la liste est dans la réponse |
| 422 | `INVALID_INPUT` | Corps de requête invalide, `Idempotency-Key` absent, ou règle métier enfreinte (règlement supérieur au solde, avoir trop élevé) |
