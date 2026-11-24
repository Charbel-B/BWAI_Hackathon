# ADR 0002 : Plateforme de développement Linux

> Statut : accepté · Date : 2026-11-24 · Auteur : Ange-Marie

## Contexte

- Deux membres développent sous Linux (Ange-Marie, Promis), deux sous Windows (Charbel, Grâce).
- Le jury peut utiliser n'importe quel système. L'ADR 0001 fixe Docker Compose comme
  installation de référence : elle fonctionne partout où Docker fonctionne.
- Il faut un point d'entrée unique pour les commandes courantes (installer, lancer, tester,
  vérifier, réinitialiser les données), qui couvre à la fois le backend, le frontend et Docker.

## Options envisagées

| Option | Avantages | Inconvénients |
| --- | --- | --- |
| A. Linux pour le développement (WSL 2 sous Windows), Docker Compose pour le jury | Outils Linux standard pour les quatre ; aucune contrainte sur les bibliothèques | Les membres sous Windows installent WSL 2 une fois |
| B. Support natif de Linux et de Windows | Aucune dépendance à WSL | Contraintes lourdes : pas de `make`, bibliothèques à logiciel système exclues |

## Décision

**Option A : développement sous Linux uniquement, WSL 2 pour les membres sous Windows ; Docker Compose pour le jury, quel que soit
son système.**

| Règle | Application |
| --- | --- |
| Prérequis de développement | Git, uv (installe lui-même Python), GNU Make, Docker. Node.js pour le frontend |
| Point d'entrée des commandes | Un `Makefile` à la racine. Chaque tâche courante est une cible : `make install`, `make dev`, `make test`, `make check`, `make reset`. Une cible appelle `uv`, `npm` ou `docker compose` ; elle ne contient pas de logique métier |
| Dépendances à logiciel système | Autorisées. Chacune est installée dans l'image Docker et listée dans les prérequis du README |
| Fins de ligne et encodage | LF (forcé par `.gitattributes`) et UTF-8 |

## Conséquences

- Les commandes sont les mêmes pour les quatre membres et pour la CI (Ubuntu).
- Le jury n'a besoin que de Docker pour reproduire le prototype ; l'installation native est
  documentée pour Linux uniquement.
- Les membres sous Windows travaillent dans WSL 2 (Ubuntu) : mêmes commandes, mêmes outils.
  Le dépôt est cloné dans le système de fichiers de WSL (`~/`), pas dans `C:\`, pour la vitesse
  et les droits sur les fichiers. Aucun support natif de Windows n'est prévu.
