# ADR 0005 : Simuler les intégrations externes, affichées comme telles

> Statut : accepté · Date : 2026-11-25 · Auteur : Ange-Marie

Complète l'[ADR 0001](0001-architecture-generale.md) sur un point : l'extracteur actif par
défaut et le traitement des services extérieurs pendant la démonstration.

## Contexte

- Le rendu est avancé au 26/11/2026 au matin et l'équipe passe de quatre à deux personnes.
- La démonstration doit dérouler tout le parcours sans aucune panne : pas de clé d'API absente,
  pas de quota atteint, pas de réseau coupé.
- Les services extérieurs (modèle en ligne, WhatsApp, SMS, courriel, mobile money) demandent
  chacun des comptes, des clés et une configuration propres, sans valeur ajoutée pour la grille
  au-delà de la preuve que le branchement est prévu.

## Options envisagées

| Option | Avantages | Inconvénients |
| --- | --- | --- |
| A. Brancher les vrais services | Réalisme | Clés, comptes, quotas ; une panne pendant la démo coûte tout le parcours |
| B. Simuler les services extérieurs derrière leur port, et le dire à l'écran | Démo sans panne ; le point de branchement réel est visible dans le code | Aucune preuve d'envoi réel |
| C. Simuler aussi l'extraction | Résultats parfaits | Mensonger : l'apport de l'IA ne serait plus mesurable |

## Décision

Option B. Tout service extérieur est simulé derrière son port et signalé comme simulé dans l'API
et dans l'interface. L'extraction, elle, reste **réelle** : l'extracteur local par règles
(`local-rules-v1`) tourne hors ligne, sans clé, et son évaluation est chiffrée
(`docs/ia/fiche-ia.md`). Le modèle en ligne reste disponible mais n'est utilisé que si
`config/extraction.yaml` le demande **et** qu'une clé est fournie.

| Élément | Traitement | Où se fait le branchement réel |
| --- | --- | --- |
| Extraction | Réelle, locale par règles | `config/extraction.yaml`, `extracteur_actif: gemini` et `INVOICING_GEMINI_API_KEY` |
| WhatsApp, SMS, courriel | Simulés : le message exact est composé et enregistré, pas envoyé | Adaptateur du port `Channel` (`infrastructure/simulated_channel.py`) |
| Règlements mobile money | Simulés : saisis à la main, référence fictive préfixée `SIMULE-` | Un adaptateur de rappel du prestataire appellerait le cas d'usage `record_payment` |
| Calcul, contrôles, numérotation, audit | Réels | Sans objet |

## Conséquences

- `GET /api/v1/health` renvoie `demo_mode`, l'extracteur actif et la liste de ce qui est simulé ;
  l'interface affiche un bandeau « Mode démonstration ».
- Chaque `Payment` et chaque `Dispatch` porte `is_simulated: true`.
- Remplacer une simulation par un vrai service ne touche qu'un adaptateur et le bootstrap.
