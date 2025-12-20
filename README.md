# Art Virtuoso SSG

Générateur de site statique pour le projet Art Virtuoso "Codex".

## Installation

1.  Python 3.8+ requis.
2.  Installer dépendances : `pip install jinja2`

## Structure

*   `data/entities.json` : Source de vérité.
*   `templates/` : Gabarits Jinja2 (Atomic Design).
*   `assets/` : CSS, JS, et images sources.
*   `generate.py` : Script principal de build.

## Commandes

### 1. Valider les données
```bash
python scripts/validate_data.py
```

### 2. Lister les images manquantes
```bash
python scripts/list_all_images.py
# Crée docs/IMAGES_NEEDED.txt
```

### 3. Générer le site
```bash
python generate.py
# Output dans dossier output/
```

### 4. Voir le résultat
```bash
cd output
python -m http.server
```
