# Présentation

> Statut : en vigueur · Mis à jour : 2026-11-26 · Responsable : Ange-Marie

| Document | Contenu |
| --- | --- |
| [presentation.html](presentation.html) | Source des 12 diapositives (16:9) présentées au jury ; captures réelles de l'application dans `captures/` |

Produire le PDF :

```bash
google-chrome --headless=new --no-pdf-header-footer --virtual-time-budget=6000 \
  --print-to-pdf=presentation.pdf "file://$PWD/docs/presentation/presentation.html"
```
