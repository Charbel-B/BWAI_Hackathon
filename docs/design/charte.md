# Charte graphique

> Statut : en vigueur · Mis à jour : 2026-11-26 · Responsable : Ange-Marie

Les valeurs vivent à un seul endroit : les jetons de `frontend/src/index.css` (bloc `@theme`).
Ce document dit à quoi sert chaque jeton et quand l'employer.

## Intention

Un ciel net, du verre et un accent vif rare. Le mécanisme du produit est montré dès l'écran de
connexion : une pièce au centre, annotée par ses champs extraits. Le ciel et le verre habillent
le cadre (en-têtes, menu, connexion, récapitulatifs) ; les données reposent sur du blanc opaque
pour rester lisibles.

Références interprétées : Oravieo (objet central annoté par des cartes en verre), Stride (menu en
pilule de verre, titres mêlant graisse fine et grasse), Catalis / Aeline (ciel franc, accent
citron, libellés à chasse fixe en capitales, cartes en bento).

## Couleurs et rôles

| Jeton | Valeur | Rôle |
| --- | --- | --- |
| `sky-deep`, `sky-strong` | `#0A3E8C`, `#0B53C2` | Haut du ciel, en-têtes |
| `sky` | `#2F8CFF` | Sélection, valeur sûre, focus |
| `sky-soft`, `sky-wash`, `ice` | `#BFDDFF`, `#EAF3FF`, `#F4F8FF` | Bas du ciel, fonds légers, fond de l'application |
| `ink`, `ink-soft` | `#0B1B33`, `#5A6B85` | Texte, bouton secondaire plein ; texte secondaire |
| `lime` | `#D4F25A` | Action principale, correction humaine, filets et soulignements. **Jamais une section entière** |
| `night`, `night-deep` | `#0A2A5E`, `#071D45` | Le haut du ciel au crépuscule : totaux, section incertitude, journal, mode démonstration. Remplace le noir, qui cassait la continuité du ciel (décision du 26/11/2026) |
| `amber` | `#F2A524` | Valeur incertaine |
| `coral` | `#E5484D` | Champ obligatoire absent, anomalie bloquante |

## Typographies

| Usage | Police | Règle |
| --- | --- | --- |
| Titres | Geist | Graisse 300 suivie d'une partie en 600, approche −3 % |
| Interface et texte | Geist | 14 à 17 px |
| Libellés | Geist Mono | Capitales, espacement 0,12 em, 11 px |
| Montants et numéros | Geist Mono | Chiffres à largeur fixe, toujours |

Les deux polices sont servies par l'application (licence OFL), sans appel à un service externe.

## Matières et formes

- Rayons : 28 px (cartes), 16 px (blocs), 14 px (champs), pilule (boutons, menu, statuts).
- Verre : blanc à 55 %, flou de 22 px, filet blanc. Réservé au cadre, jamais sous des données.
- Ombres teintées de bleu, décalées vers le bas.
- Icônes : Lucide, trait de 1,5 à 2,6 px selon la taille.
- Mouvement de l'interface : 200 à 300 ms, courbe `--ease-out` ; mouvement réduit respecté.

## Mouvement

Une seule chorégraphie, définie dans `frontend/src/styles/motion.css`.

| Moment | Effet | Pourquoi |
| --- | --- | --- |
| Arrivée sur la landing | Titre, texte, boutons puis visuel entrent en cascade (90 ms d'écart) ; « facture juste » se souligne d'un trait citron tracé à la main | Guider le regard dans l'ordre de lecture |
| Héros | Les annotations apparaissent après la pièce puis flottent chacune à son rythme ; un balayage de lecture parcourt la facture | Montrer l'extraction au travail |
| Revue jouable | Les champs s'allument tour à tour et pointent leur passage ; le survol reprend la main | Démontrer le mécanisme au lieu de le décrire |
| Défilement | Sections et cartes apparaissent à l'entrée dans l'écran, décalées de 70 ms | Rythme sans tout montrer d'un coup |
| Chiffres | Les compteurs défilent jusqu'à leur valeur à l'entrée dans l'écran | Donner du poids aux mesures |
| Survol des cartes | Légère élévation, souris uniquement | Retour d'interaction |

Avec `prefers-reduced-motion`, les déplacements sont retirés et seuls des fondus courts restent ;
tout le contenu est visible par défaut.

## États d'un champ extrait

Chaque état a une forme, un mot et une couleur : on les distingue sans voir les couleurs.

| État | Forme | Mot | Origine |
| --- | --- | --- | --- |
| Sûr | Jauge bleue | « Sûr · 95 % » | Champ trouvé, aucune anomalie |
| À confirmer | Contour ambre en pointillés, jauge ambre | « À confirmer · 72 % » | Anomalie `LOW_CONFIDENCE` du backend |
| Absent | Hachures corail, croix | « Absent de la pièce » | Anomalie `MISSING_REQUIRED_FIELD` |
| Non indiqué | Fond glace, tiret | « Non indiqué » | Champ facultatif absent |
| Corrigé | Pastille citron, ancienne valeur barrée | « Corrigé » | Revue humaine avec nouvelle valeur |
| Confirmé | Pastille encre, coche | « Confirmé » | Revue humaine sans changement |

Le seuil de confiance et la liste des champs obligatoires ne sont jamais recopiés dans
l'interface : elle lit les anomalies calculées par le backend.

## Écrans

| Écran | Route | Rôle |
| --- | --- | --- |
| Accueil | `/` | Landing publique : héros (rendu 3D annoté), parcours en quatre gestes, incertitude, garanties, mesures de l'IA, ce qui est simulé, appel final |
| Connexion | `/connexion` | Page à part : formulaire et comptes de démonstration à gauche, visuel à droite |
| Tableau | `/tableau` | Bento des compteurs, liste des factures |
| Import | `/importer` | Fichier déposé ou message collé |
| Revue | `/factures/:id` (brouillon) | Pièce à gauche, champs à droite, reliés au survol ; anomalies ; totaux ; validation |
| Facture | `/factures/:id` (validée) | Lignes, totaux et solde, émission simulée, règlements, avoirs |
| Journal | `/journal` | Entrées chaînées et vérification de la chaîne |
| Paramètres | `/parametres` | Profil et droits du rôle, mot de passe (simulé, signalé), canal d'émission préféré (enregistré sur l'appareil), informations système réelles, réinitialisation de la démo (administrateur) |

## Assets

| Fichier | Origine |
| --- | --- |
| `frontend/src/assets/hero-facture-verre.webp` | Rendu 3D généré pour le projet le 26/11/2026, converti en WebP |
| `frontend/src/assets/depot-pieces-verre.webp` | Objet 3D (dépôt de pièces), fond transparent, même date |
| `frontend/src/assets/message-valide-verre.webp` | Objet 3D (message validé), fond transparent, même date |
