# MCP-LOCAL-Reader

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.8%2B-green.svg)](https://github.com/jlowin/fastmcp)

**Convertisseur de Documents Prêt pour l'IA** - Transformez n'importe quel fichier local en format Markdown optimisé pour l'IA pour une intégration transparente avec Claude Desktop, Claude Code et d'autres clients MCP.

**Traitement Intelligent de Documents** - Extraction de contenu de fichiers locaux haute performance avec analyse avancée pour PDF, documents Office, images et plus. Convertit automatiquement des documents complexes en Markdown propre et structuré que les modèles d'IA peuvent facilement comprendre et traiter.

## Fonctionnalités

### 📄 **Traitement de Fichiers Optimisé pour l'IA**
- **Documents PDF** : Analyse avancée avec PyMuPDF4LLM → Sortie Markdown propre
- **Suite Office** : Word, Excel, PowerPoint → Tableaux et texte structurés
- **OpenDocument** : ODT, ODS, ODP → Format Markdown standardisé
- **Texte et Données** : Markdown, JSON, CSV, EPUB → Lisibilité IA améliorée
- **Images** : Reconnaissance de texte OCR → Contenu Markdown consultable
- **Archives** : Extraction intelligente → Collections de documents organisées

### 🚀 **Performance Intelligente**
- **Cache Intelligent** : Se souvient des fichiers traités pour un re-accès instantané
- **Chargement Paresseux** : Ne charge que les composants nécessaires - démarrage 80% plus rapide
- **Traitement Concurrent** : Gère plusieurs fichiers simultanément
- **Optimisation des Ressources** : Empêche la surcharge système avec des limites intelligentes

### 🔒 **Sécurité et Contrôle**
- **Permissions de Répertoire** : Restreint l'accès à des répertoires spécifiques
- **Validation de Chemin** : Accès sécurisé aux fichiers avec exigences de chemin absolu
- **Limites de Taille de Fichier** : Empêche DoS avec restrictions de taille configurables
- **Local d'Abord** : Aucune donnée ne quitte votre machine - confidentialité complète

## Démarrage Rapide

### Prérequis

- Python 3.11+
- [Gestionnaire de paquets uv](https://docs.astral.sh/uv/)

### Installation

#### Option 1 : Configuration en Une Commande (Recommandée)

```bash
# Cloner et auto-configurer
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
chmod +x install.sh && ./install.sh
```

L'installateur vous guidera à travers trois modes d'installation :

1. **Minimal** : PDF et fichiers texte de base uniquement (empreinte la plus petite)
2. **Standard** : Support des documents Office, sans OCR (recommandé)
3. **Complet** : Toutes les fonctionnalités incluant OCR et traitement d'archives

#### Option 2 : Installation Manuelle

```bash
# Installer le gestionnaire de paquets uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Configuration du projet
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
uv sync

# Configurer l'environnement
cp env.example .env
# Éditer .env avec vos paramètres

# Démarrer le serveur
uv run python run_mcp_server.py
```

### Configuration pour Claude Desktop

#### Configuration Automatique
```bash
chmod +x configure_claude.sh && ./configure_claude.sh
```

#### Configuration Manuelle
Éditer `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) ou équivalent :

```json
{
  "mcpServers": {
    "mcp-local-reader": {
      "command": "uv",
      "args": [
        "run", 
        "python", 
        "/absolute/path/to/mcp-local-reader/run_mcp_server.py"
      ],
      "env": {
        "LOCAL_FILE_ALLOWED_DIRECTORIES": "/Users/username/Documents,/Users/username/Downloads"
      }
    }
  }
}
```

### Configuration pour Claude Code

Ajouter à `.claude/claude_config.json` :
```json
{
  "mcpServers": {
    "mcp-local-reader": {
      "command": "uv",
      "args": [
        "run", 
        "python", 
        "/absolute/path/to/mcp-local-reader/run_mcp_server.py"
      ],
      "env": {
        "LOCAL_FILE_ALLOWED_DIRECTORIES": "/Users/username/Documents,/Users/username/Downloads"
      }
    }
  }
}
```

## Utilisation

Après la configuration, utilisez ces fonctionnalités directement dans les conversations :

### 📄 Lire et Convertir en Markdown Prêt pour l'IA

Transformez n'importe quel fichier en format Markdown optimisé pour l'IA :

```
Lire le contenu de /Users/username/Documents/report.pdf
→ Convertit en Markdown propre avec tableaux, en-têtes et structure

Analyser /Users/username/data.xlsx et montrer la structure des données  
→ Extrait les données de feuille de calcul comme tableaux Markdown

Extraire le texte de /Users/username/presentation.pptx
→ Organise les diapositives en sections Markdown structurées
```

### 🔄 Sauvegarder comme Fichiers Markdown

Convertir et sauvegarder des documents comme fichiers Markdown prêts pour l'IA :

```
Convertir /Users/username/contract.pdf en format Markdown
→ Crée contract.pdf.md avec contenu structuré

Sauvegarder /Users/username/analysis.xlsx comme Markdown dans /Users/username/output/
→ Sauvegarde les tableaux et données formatés comme Markdown
```

## Configuration

### Paramètres Essentiels (.env)

```bash
# Contrôle d'accès aux fichiers (REQUIS)
LOCAL_FILE_ALLOWED_DIRECTORIES=/Users/username/Documents,/Users/username/Downloads

# Optimisation des performances
TOTAL_CACHE_SIZE_MB=500          # Limite de cache unifié
CACHE_EXPIRE_DAYS=30             # Rétention du cache
FILE_READER_MAX_FILE_SIZE_MB=20  # Limite de taille de fichier

# Journalisation
LOG_LEVEL=INFO
```

### Paramètres OCR Optionnels

Pour la reconnaissance de texte d'image :

```bash
# Modèle de vision pour OCR
LLM_VISION_BASE_URL=https://api.openai.com/v1
LLM_VISION_API_KEY=sk-your-api-key-here
LLM_VISION_MODEL=gpt-4o  # ou qwen-vl-plus
```

## Variables d'Environnement

| Variable | Requis | Défaut | Description |
|----------|----------|---------|-------------|
| `LOCAL_FILE_ALLOWED_DIRECTORIES` | ✅ | `current_dir` | Répertoires autorisés séparés par des virgules |
| `TOTAL_CACHE_SIZE_MB` | ❌ | `500` | Limite de taille de cache unifié |
| `FILE_READER_MAX_FILE_SIZE_MB` | ❌ | `20` | Taille maximale de fichier |
| `LOG_LEVEL` | ❌ | `INFO` | Niveau de journalisation |
| `LLM_VISION_API_KEY` | ❌ | - | Clé API du modèle de vision OCR |

## Outils MCP

### `read_local_file`

Extraire le contenu des fichiers locaux et retourner comme Markdown optimisé pour l'IA.

| Paramètre | Type | Description |
|-----------|------|-------------|
| `file_path` | string | Chemin absolu vers le fichier |
| `max_size` | number | Limite de taille de fichier en MB (optionnel) |

### `convert_local_file`

Convertir les fichiers en Markdown prêt pour l'IA et sauvegarder sur le système de fichiers.

| Paramètre | Type | Description |
|-----------|------|-------------|
| `file_path` | string | Chemin absolu vers le fichier d'entrée |
| `output_path` | string | Chemin de sortie (optionnel, par défaut entrée+.md) |
| `max_size` | number | Limite de taille de fichier en MB (optionnel) |
| `overwrite` | boolean | Écraser les fichiers existants (défaut : false) |

## Types de Fichiers Pris en Charge

### Formats de Documents
- **PDF** : `.pdf`
- **Microsoft Office** : `.doc`, `.docx`, `.ppt`, `.pptx`, `.xls`, `.xlsx`
- **OpenDocument** : `.odt`, `.ods`, `.odp`
- **Texte** : `.txt`, `.md`, `.rtf`, `.csv`, `.json`, `.xml`

### Formats d'Images (avec OCR)
- **Communs** : `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`
- **Avancés** : `.webp`, `.svg`

### Formats d'Archives
- **Compressés** : `.zip`, `.tar`, `.tar.gz`, `.7z`
- **Office** : `.docx`, `.xlsx`, `.pptx` (basés sur zip en interne)

### Formats Spéciaux
- **E-books** : `.epub`
- **Données** : `.csv`, `.tsv`, `.json`

## Architecture

### Composants Principaux

- **FileReader** (`src/file_reader/core.py`) : Orchestrateur principal pour l'extraction de contenu de fichier
- **Serveur MCP** (`src/mcp_server.py`) : Serveur basé sur FastMCP fournissant des outils MCP
- **Système de Parseur** (`src/file_reader/parsers/`) : Parseurs spécialisés pour différents types de fichiers
- **Gestionnaire de Cache** (`src/file_reader/cache_manager.py`) : Système de cache unifié
- **Couche de Stockage** (`src/file_reader/storage/`) : Accès sécurisé aux fichiers locaux

### Optimisations de Performance

1. **Cache Unifié** : Instance de cache unique au lieu de multiples (réduit de ~6GB à 500MB par défaut)
2. **Chargement Paresseux** : Parseurs chargés à la demande, pas au démarrage
3. **Optimisation des Dépendances** : Dépendances optionnelles pour les fonctionnalités avancées
4. **Limites de Ressources** : Limites configurables de mémoire et de taille de fichier

## Développement

### Configuration de l'Environnement de Développement

```bash
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
uv sync
source .venv/bin/activate  # Sur Unix/macOS
```

### Exécution des Tests

```bash
# Exécuter tous les tests
uv run python tests/run_tests.py

# Catégories de tests spécifiques
uv run python tests/run_tests.py --models     # Modèles de données
uv run python tests/run_tests.py --parsers    # Parseurs de fichiers
uv run python tests/run_tests.py --core       # Fonctionnalité principale
uv run python tests/run_tests.py --server     # Serveur MCP

# Avec couverture
uv run python tests/run_tests.py -c

# Utilisation alternative de pytest
PYTHONPATH=src uv run pytest tests/ -v
```

### Ajout de Nouveaux Parseurs

1. Créer le parseur dans `src/file_reader/parsers/`
2. Hériter de `BaseParser`
3. Enregistrer dans `parser_loader.py`
4. Ajouter des tests dans `tests/test_parsers.py`

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour des directives de développement détaillées.

## Caractéristiques de Performance

- **Cache Intelligent** : Accès instantané aux fichiers précédemment traités sans re-conversion
- **Utilisation Mémoire Efficace** : Optimisé de 6GB+ à 500MB de taille de cache par défaut
- **Démarrage Éclair** : 80% plus rapide avec le chargement de composants à la demande
- **Traitement Parallèle** : Gère plusieurs conversions de documents simultanément

## Exigences Système

- **Python** : 3.11+
- **OS** : macOS, Linux, Windows
- **Mémoire** : 2GB+ recommandé pour les gros fichiers
- **Optionnel** : LibreOffice (fichiers Office legacy), Pandoc (conversions spéciales)

## FAQ

**Q : Les fichiers ne se lisent pas correctement ?**  
R : Assurez-vous que `LOCAL_FILE_ALLOWED_DIRECTORIES` inclut le répertoire de votre fichier.

**Q : L'OCR ne fonctionne pas pour les images ?**  
R : Configurez `LLM_VISION_API_KEY` avec une clé API de modèle de vision valide (OpenAI GPT-4o ou compatible).

**Q : Vous voulez améliorer la vitesse de traitement ?**  
R : Le cache intelligent se souvient automatiquement des fichiers traités. Effacez le répertoire de cache si vous voulez un traitement frais de tous les fichiers.

**Q : Les fichiers Office legacy (.doc/.ppt) échouent ?**  
R : Installez LibreOffice : `brew install --cask libreoffice` (macOS) ou équivalent pour votre OS.

**Q : Quels formats de fichiers sont pris en charge ?**  
R : PDF, Word, Excel, PowerPoint, OpenDocument, images (avec OCR), archives, fichiers texte, et plus.

## Contribution

Nous accueillons les contributions ! Veuillez voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les directives sur comment contribuer à ce projet.

## Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour les détails.

## Liens

- **Problèmes** : [Signaler des Problèmes](https://github.com/freefish1218/mcp-local-reader/issues)
- **Documentation** : [CLAUDE.md](CLAUDE.md) pour guide de développement détaillé
- **Protocole de Contexte de Modèle** : [Documentation MCP Officielle](https://modelcontextprotocol.io/)

## Remerciements

- Construit avec [FastMCP](https://github.com/jlowin/fastmcp)
- Analyse PDF alimentée par [PyMuPDF4LLM](https://github.com/pymupdf/PyMuPDF4LLM)
- Système de cache utilisant [DiskCache](https://github.com/grantjenks/python-diskcache)