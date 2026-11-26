# Scénario de reprise après interruption

> Statut : en vigueur · Mis à jour : 2026-11-26 · Responsable : Ange-Marie

Objectif : montrer qu'une coupure (réseau ou serveur) ne perd aucune donnée et ne produit aucun
doublon. Tests automatiques correspondants : `backend/tests/integration/test_reprise.py`,
`test_invoice_flow.py` (idempotence, versions).

| Interruption | Mécanisme | Ce qu'on observe |
| --- | --- | --- |
| Réponse perdue pendant un règlement | Le formulaire garde la même `Idempotency-Key` tant que le règlement n'est pas confirmé et réessaie seul sur erreur réseau ; le serveur rejoue la réponse d'origine | Un seul règlement, solde juste ; en-tête `Idempotent-Replayed: true` |
| Double clic, deux onglets | Même mécanisme ; validations simultanées refusées par la version (`If-Match`) | Une seule action ; l'autre reçoit 409 |
| Arrêt brutal du serveur | Chaque action est une transaction SQLite ; le volume `donnees` conserve la base | Factures, règlements, compteurs et journal intacts ; la numérotation reprend sans trou |
| Session perdue au redémarrage | Les jetons sont en mémoire, par choix | Se reconnecter ; aucune donnée n'est perdue |

## Démonstration en direct (Docker)

1. Valider une facture, enregistrer un règlement partiel.
2. Simuler la coupure réseau : outils du navigateur, onglet Réseau, « Hors ligne », puis
   **Enregistrer un règlement** ; repasser en ligne : la retentative passe avec la même clé, un
   seul règlement apparaît.
3. Arrêter brutalement l'API : `docker compose kill api`, puis `docker compose up -d api`.
4. Se reconnecter : la facture, le règlement et le journal (« Chaîne intacte ») sont là ; valider
   une nouvelle facture donne le numéro suivant.

Rejeu par l'API, sans interface :

```bash
TOKEN=$(curl -s -X POST localhost:8080/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"operateur","password":"demo-operateur"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
for i in 1 2; do   # deux envois identiques, même clé
  curl -s -X POST localhost:8080/api/v1/invoices/<id>/payments -H "Authorization: Bearer $TOKEN" \
    -H 'Idempotency-Key: reprise-1' -H 'Content-Type: application/json' -d '{"amount":"1000"}' -D - -o /dev/null | grep -i replayed
done
```
