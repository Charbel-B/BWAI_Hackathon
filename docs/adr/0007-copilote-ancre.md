# ADR 0007 : Un copilote ancré dans les données

> Statut : accepté · Date : 2026-11-26 · Auteur : Ange-Marie

## Contexte

Un assistant conversationnel aide l'opérateur et le validateur : pourquoi une facture est
bloquée, d'où vient un total, quelles factures relancer. Un assistant qui affirme un chiffre faux
détruirait la confiance que le reste du produit construit (calcul exact, journal chaîné).

## Options envisagées

| Option | Avantages | Inconvénients |
| --- | --- | --- |
| A. Modèle de langage qui répond librement | Conversation fluide | Peut inventer un montant ou une règle ; dépend d'une clé et du réseau |
| B. Moteur local par intentions, réponses construites depuis l'API | Aucun chiffre inventé ; hors ligne ; testable | Questions comprises par mots-clés |
| C. B, puis un modèle qui reformule sans produire de valeur | Fluidité de A, sûreté de B | Reformulation à encadrer |

## Décision

Option B pour ce prototype, conçue pour évoluer vers C. `POST /api/v1/assistant/ask` reconnaît
cinq intentions (`pourquoi_bloquee`, `expliquer_total`, `factures_en_retard`,
`que_faire_ensuite`, `aide`) et construit la réponse à partir des cas d'usage existants. Chaque
réponse porte ses **sources** (anomalie, facture, règle) et des **actions** (lien vers l'écran),
et le champ `engine` (`local-intents-v1`) dit quel moteur a répondu ; l'interface l'affiche.

## Conséquences

- Les chiffres d'une réponse sont ceux du moteur de calcul et de l'échéancier, jamais recalculés.
- Une question hors des cinq intentions reçoit l'aide, pas une réponse approximative.
- Brancher un modèle plus tard ne touchera que la mise en mots, derrière le même contrat.
