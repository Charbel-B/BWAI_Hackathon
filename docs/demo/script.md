# Script de démonstration

> Statut : en vigueur · Mis à jour : 2026-11-26 · Responsable : Ange-Marie

Durée visée : 8 minutes. Pièces : `data/scenarios/` (fictives). Comptes : `operateur`,
`validateur`, `admin`, mot de passe `demo-<identifiant>`.

## Avant de commencer

```bash
docker compose up --build     # puis http://localhost:8080
```

1. Se connecter en `admin`, ouvrir **Paramètres**, cliquer **Réinitialiser la démonstration**.
2. Garder les trois fichiers `data/scenarios/*/piece.txt` ouverts dans un éditeur pour les coller.
3. Ouvrir un deuxième onglet en navigation privée : il servira au validateur.

## Déroulé

| Temps | Écran | Geste | Ce qu'on dit, ce que le jury voit |
| --- | --- | --- | --- |
| 0:00 | Accueil `/` | Laisser jouer le héros, survoler la section « Survolez un champ » | Le mécanisme : chaque valeur lue pointe vers son passage dans la pièce |
| 0:45 | Connexion | Cliquer `operateur`, se connecter | Le panneau de droite montre ce qui attend chaque rôle |
| 1:00 | Importer | Coller le scénario 1 (`01-propre`) | Extraction hors ligne, aucune anomalie, 153 000 HT, 27 540 de TVA, 180 540 TTC calculés par le moteur |
| 1:45 | Revue | Survoler les champs | Confiance par champ, source surlignée dans la pièce |
| 2:15 | Onglet validateur | Se connecter en `validateur`, ouvrir le brouillon, **Valider** | Numéro `FA-2026-00001` attribué dans la transaction ; empreinte des règles enregistrée |
| 2:45 | Facture | **WhatsApp**, puis règlement de 80 000 en mobile money | Message exact composé, marqué « simulé » ; statut « Partiellement réglée » calculé |
| 3:30 | Importer (opérateur) | Coller le scénario 2 (`02-a-corriger`) | Date absente : champ hachuré « Absent de la pièce », validation bloquée, rien n'est inventé |
| 4:00 | Revue | **Saisir** `2026-11-25` sur la date | Le brouillon se recalcule (version + 1), l'anomalie disparaît, 92 040 TTC |
| 4:30 | Importer | Coller le scénario 3 (`03-bloque`) | Client hors référentiel et total lu faux : le moteur impose 219 480 TTC, deux points bloquants |
| 5:15 | Onglet validateur | Tenter **Valider** sur le scénario 3 | Refus : « Des points bloquants restent à traiter » |
| 5:45 | Onglet validateur | Importer une pièce, puis tenter de la valider soi-même | Séparation des tâches : l'auteur d'un brouillon ne peut pas le valider |
| 6:15 | Facture `FA-2026-00001` | **Créer un avoir total** avec un motif | Avoir `AV-2026-00001` ; la facture passe « Annulée par avoir », elle n'est jamais modifiée |
| 7:00 | Journal | Ouvrir le journal | Chaque action est chaînée à la précédente ; badge « Chaîne intacte » |
| 7:30 | Paramètres | Montrer « Système » | Version, extracteur actif, empreinte des règles, et la liste de ce qui est simulé |

## Si quelque chose résiste

| Problème | Réponse |
| --- | --- |
| Session expirée après un redémarrage de l'API | Les jetons sont en mémoire : se reconnecter |
| Numéros déjà avancés | `admin` → Paramètres → Réinitialiser la démonstration |
| Port 8080 occupé | Modifier `ports` dans `compose.yaml` (par exemple `"8081:80"`) |
