# ADR 0002 : Support de Linux et de Windows

> Statut : accepté · Date : 2026-11-24 · Auteur : Ange-Marie

## Contexte

- Les membres de l'équipe développent sous Linux et sous Windows. Le jury peut utiliser l'un ou
  l'autre.
- `make` et les scripts shell (`.sh`) ne fonctionnent pas nativement sous Windows.
- Certaines bibliothèques Python exigent un logiciel système installé à part, simple sous Linux
  et fragile sous Windows : WeasyPrint (PDF, dépend de Pango) et Tesseract (lecture de texte
  dans une image, binaire à installer).

## Options envisagées

| Option | Avantages | Inconvénients |
| --- | --- | --- |
| A. Linux uniquement, Windows par WSL ou Docker | Aucune contrainte sur les outils | Les membres sous Windows dépendent de WSL ou de Docker pour chaque commande ; risque de blocage le jour du rendu |
| B. Support natif des deux systèmes | Chacun travaille sur sa machine sans couche intermédiaire ; le jury reproduit sur l'un ou l'autre | Interdit les dépendances à logiciel système ; impose un lanceur de tâches multiplateforme |

## Décision

**Option B : tout fonctionne nativement sous Linux et sous Windows.** Docker Compose reste
l'installation de référence pour le jury (ADR 0001), en plus de l'installation native.

| Règle | Application |
| --- | --- |
| Prérequis communs | Git et uv. uv installe lui-même la bonne version de Python. Node.js pour le frontend uniquement |
| Lanceur de tâches | [Poe the Poet](https://poethepoet.natn.io/), tâches déclarées dans `backend/pyproject.toml`, lancées par `uv run poe <tâche>`. Aucun `Makefile`, aucun script `.sh` ou `.ps1` comme point d'entrée |
| Dépendances Python | Uniquement des paquets installables par uv sur les deux systèmes, sans logiciel système à installer à part. WeasyPrint et Tesseract sont exclus |
| Chemins de fichiers | `pathlib.Path` uniquement, jamais de chemin écrit avec `/` ou `\` en dur |
| Noms de fichiers | Minuscules, chiffres et tirets, sans accent ni espace |
| Fins de ligne | Forcées à LF par `.gitattributes`, quel que soit le système |
| Encodage | UTF-8 explicite à chaque ouverture de fichier : `open(path, encoding="utf-8")` |

## Conséquences

- La ligne « Documents » de l'ADR 0001 reste valable (gabarit HTML rendu en PDF), mais le moteur
  de rendu doit respecter la règle des dépendances. Choix à faire par Grâce parmi les moteurs
  sans dépendance système, et à consigner dans la PR qui l'introduit.
- Le repli local de l'extraction ne peut pas utiliser Tesseract. Choix à faire par Charbel parmi
  les solutions installables par uv sur les deux systèmes.
- La CI exécute les tests sous Linux et sous Windows.
