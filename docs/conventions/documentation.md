# Doctrine de documentation

> Statut : en vigueur · Mis à jour : 2026-11-24 · Responsable : Ange-Marie

## 1. Règle d'or

Un changement n'est pas terminé tant que la documentation qu'il touche n'est pas à jour, **dans
la même PR**. Une documentation obsolète est un défaut au même titre qu'un test qui échoue.

## 2. Organisation

- Toute la documentation est dans `docs/`, un sous-dossier par sujet, rien en vrac.
- Chaque dossier a un `README.md` qui sert d'index : à quoi sert le dossier, liste de ses
  documents avec une ligne de description.
- Noms de dossiers et de fichiers explicites, en minuscules, mots séparés par des tirets :
  `cycle-de-vie-facture.md`.
- Le `README.md` à la racine du dépôt reste court : présentation, installation, lancement,
  liens vers `docs/`.

## 3. En-tête de chaque document

Chaque document commence par son titre puis cette ligne :

```markdown
> Statut : brouillon | en vigueur | partiel | remplacé · Mis à jour : AAAA-MM-JJ · Responsable : Prénom
```

| Statut | Signification |
| --- | --- |
| brouillon | En cours de rédaction, ne fait pas encore référence |
| en vigueur | Fait référence et doit être respecté |
| partiel | Fait référence pour ce qui est écrit ; une partie est marquée **[À COMPLÉTER]** |
| remplacé | Conservé pour l'historique, avec un lien vers le document qui le remplace |

## 4. Écriture

- Français, ton factuel, phrases courtes. On décrit ce que l'équipe a fait et décidé.
- Chaque terme métier suit le [glossaire](../domaine/glossaire.md). Un terme nouveau y est
  ajouté dans la même PR.
- Pas de formule vague (« rapide », « robuste », « plusieurs ») là où un chiffre ou une liste est
  possible.
- Une information manquante s'écrit **[À COMPLÉTER]**. On n'invente jamais.
- Les dates sont absolues, au format AAAA-MM-JJ.
- Mise en valeur par titres, gras, tableaux et encadrés (`> [!NOTE]`, `> [!WARNING]`).
  Pas d'emoji.

## 5. Schémas

Dès qu'un flux, un cycle de vie ou une relation se comprend mieux dessiné que décrit, on le
dessine en [Mermaid](https://mermaid.js.org/) directement dans le Markdown. GitHub l'affiche, et
le schéma se modifie dans la même PR que le code qu'il décrit.

## 6. Décisions d'architecture (ADR)

- Toute décision structurante (choix d'une technologie, d'un découpage, d'un format, d'une règle
  qui engage plusieurs périmètres) fait l'objet d'un ADR dans `docs/adr/`.
- Format : [modèle d'ADR](../adr/0000-modele.md). Numérotation continue sur 4 chiffres.
- Un ADR accepté n'est jamais réécrit. S'il est remis en cause, un nouvel ADR le remplace et
  l'ancien passe au statut « remplacé ».

## 7. Documentation du code

Les règles propres au code (docstrings, commentaires) sont dans les conventions de chaque
langage : [Python](code-python.md), [frontend](code-frontend.md).
