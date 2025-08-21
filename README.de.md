# MCP-LOCAL-Reader

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.8%2B-green.svg)](https://github.com/jlowin/fastmcp)

[English](README.md) | [中文版](README_zh.md) | [日本語](README_ja.md) | [Français](README_fr.md)

**KI-Ready Dokumentenkonverter** - Wandeln Sie jede lokale Datei in ein KI-optimiertes Markdown-Format um für nahtlose Integration mit Claude Desktop, Claude Code und anderen MCP-Clients.

**Intelligente Dokumentenverarbeitung** - Hochleistungs-Extraktion lokaler Dateiinhalte mit erweiterte Analyse für PDF, Office-Dokumente, Bilder und mehr. Konvertiert automatisch komplexe Dokumente in sauberes, strukturiertes Markdown, das KI-Modelle leicht verstehen und verarbeiten können.

## Funktionen

### 📄 **KI-Optimierte Dateiverarbeitung**
- **PDF-Dokumente**: Erweiterte Analyse mit PyMuPDF4LLM → Saubere Markdown-Ausgabe
- **Office-Suite**: Word, Excel, PowerPoint → Strukturierte Tabellen und Text
- **OpenDocument**: ODT, ODS, ODP → Standardisiertes Markdown-Format
- **Text & Daten**: Markdown, JSON, CSV, EPUB → Verbesserte KI-Lesbarkeit
- **Bilder**: OCR-Texterkennung → Durchsuchbarer Markdown-Inhalt
- **Archive**: Intelligente Extraktion → Organisierte Dokumentensammlungen

### 🚀 **Intelligente Leistung**
- **Smart-Caching**: Erinnert sich an verarbeitete Dateien für sofortigen Wiederzugriff
- **Lazy Loading**: Lädt nur benötigte Komponenten - 80% schnellerer Start
- **Nebenläufige Verarbeitung**: Verarbeitet mehrere Dateien gleichzeitig
- **Ressourcenoptimierung**: Verhindert Systemüberlastung mit intelligenten Grenzen

### 🔒 **Sicherheit & Kontrolle**
- **Verzeichnisberechtigungen**: Beschränkt Zugriff auf spezifische Verzeichnisse
- **Pfadvalidierung**: Sicherer Dateizugriff mit absoluten Pfadanforderungen
- **Dateigrößenbeschränkungen**: Verhindert DoS mit konfigurierbaren Größenbeschränkungen
- **Local-First**: Keine Daten verlassen Ihre Maschine - vollständige Privatsphäre

## Schnellstart

### Voraussetzungen

- Python 3.11+
- [uv Paketmanager](https://docs.astral.sh/uv/)

### Installation

#### Option 1: Ein-Befehl-Setup (Empfohlen)

```bash
# Klonen und automatisch konfigurieren
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
chmod +x install.sh && ./install.sh
```

Der Installer führt Sie durch drei Installationsmodi:

1. **Minimal**: Nur PDF und grundlegende Textdateien (kleinster Footprint)
2. **Standard**: Office-Dokumentsupport, kein OCR (empfohlen)
3. **Vollständig**: Alle Funktionen einschließlich OCR und Archivverarbeitung

#### Option 2: Manuelle Installation

```bash
# uv Paketmanager installieren
curl -LsSf https://astral.sh/uv/install.sh | sh

# Projekt einrichten
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
uv sync

# Umgebung konfigurieren
cp env.example .env
# .env mit Ihren Einstellungen bearbeiten

# Server starten
./start_mcp.sh
```

### Konfiguration für Claude Desktop

#### Automatische Konfiguration
```bash
chmod +x configure_claude.sh && ./configure_claude.sh
```

#### Manuelle Konfiguration
Bearbeiten Sie `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) oder Äquivalent:

```json
{
  "mcpServers": {
    "local-reader": {
      "command": "/absolute/path/to/mcp-local-reader/start_mcp.sh",
      "args": [],
      "env": {
        "LOCAL_FILE_ALLOWED_DIRECTORIES": "/Users/username/Documents,/Users/username/Downloads"
      }
    }
  }
}
```

### Konfiguration für Claude Code

Zu `.claude/claude_config.json` hinzufügen:
```json
{
  "mcpServers": {
    "local-reader": {
      "command": "/absolute/path/to/mcp-local-reader/start_mcp.sh",
      "args": [],
      "env": {
        "LOCAL_FILE_ALLOWED_DIRECTORIES": "/Users/username/Documents,/Users/username/Downloads"
      }
    }
  }
}
```

## Verwendung

Nach der Einrichtung verwenden Sie diese Funktionen direkt in Gesprächen:

### 📄 Lesen & Konvertieren zu KI-Ready Markdown

Wandeln Sie jede Datei in KI-optimiertes Markdown-Format um:

```
Lesen Sie den Inhalt von /Users/username/Documents/report.pdf
→ Konvertiert zu sauberem Markdown mit Tabellen, Überschriften und Struktur

Analysieren Sie /Users/username/data.xlsx und zeigen Sie mir die Datenstruktur  
→ Extrahiert Tabellenkalkulationsdaten als Markdown-Tabellen

Extrahieren Sie Text aus /Users/username/presentation.pptx
→ Organisiert Folien in strukturierte Markdown-Abschnitte
```

### 🔄 Als Markdown-Dateien speichern

Dokumente zu KI-ready Markdown-Dateien konvertieren und speichern:

```
Konvertieren Sie /Users/username/contract.pdf in Markdown-Format
→ Erstellt contract.pdf.md mit strukturiertem Inhalt

Speichern Sie /Users/username/analysis.xlsx als Markdown in /Users/username/output/
→ Speichert formatierte Tabellen und Daten als Markdown
```

## Konfiguration

### Grundlegende Einstellungen (.env)

```bash
# Dateizugriffskontrolle (ERFORDERLICH)
LOCAL_FILE_ALLOWED_DIRECTORIES=/Users/username/Documents,/Users/username/Downloads

# Leistungsoptimierung
TOTAL_CACHE_SIZE_MB=500          # Einheitliches Cache-Limit
CACHE_EXPIRE_DAYS=30             # Cache-Aufbewahrung
FILE_READER_MAX_FILE_SIZE_MB=20  # Dateigrößenlimit

# Protokollierung
LOG_LEVEL=INFO
```

### Optionale OCR-Einstellungen

Für Bildtexterkennung:

```bash
# Vision-Modell für OCR
LLM_VISION_BASE_URL=https://api.openai.com/v1
LLM_VISION_API_KEY=sk-your-api-key-here
LLM_VISION_MODEL=gpt-4o  # oder qwen-vl-plus
```

## Umgebungsvariablen

| Variable | Erforderlich | Standard | Beschreibung |
|----------|----------|---------|-------------|
| `LOCAL_FILE_ALLOWED_DIRECTORIES` | ✅ | `current_dir` | Kommagetrennte erlaubte Verzeichnisse |
| `TOTAL_CACHE_SIZE_MB` | ❌ | `500` | Einheitliches Cache-Größenlimit |
| `FILE_READER_MAX_FILE_SIZE_MB` | ❌ | `20` | Maximale Dateigröße |
| `LOG_LEVEL` | ❌ | `INFO` | Protokollierungsebene |
| `LLM_VISION_API_KEY` | ❌ | - | OCR-Vision-Modell-API-Schlüssel |

## MCP-Tools

### `read_local_file`

Inhalt aus lokalen Dateien extrahieren und als KI-optimiertes Markdown zurückgeben.

| Parameter | Typ | Beschreibung |
|-----------|------|-------------|
| `file_path` | string | Absoluter Pfad zur Datei |
| `max_size` | number | Dateigrößenlimit in MB (optional) |

### `convert_local_file`

Dateien in KI-ready Markdown konvertieren und im Dateisystem speichern.

| Parameter | Typ | Beschreibung |
|-----------|------|-------------|
| `file_path` | string | Absoluter Pfad zur Eingabedatei |
| `output_path` | string | Ausgabepfad (optional, Standard ist Eingabe+.md) |
| `max_size` | number | Dateigrößenlimit in MB (optional) |
| `overwrite` | boolean | Bestehende Dateien überschreiben (Standard: false) |

## Unterstützte Dateitypen

### Dokumentformate
- **PDF**: `.pdf`
- **Microsoft Office**: `.doc`, `.docx`, `.ppt`, `.pptx`, `.xls`, `.xlsx`
- **OpenDocument**: `.odt`, `.ods`, `.odp`
- **Text**: `.txt`, `.md`, `.rtf`, `.csv`, `.json`, `.xml`

### Bildformate (mit OCR)
- **Häufige**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`
- **Erweiterte**: `.webp`, `.svg`

### Archivformate
- **Komprimiert**: `.zip`, `.tar`, `.tar.gz`, `.7z`
- **Office**: `.docx`, `.xlsx`, `.pptx` (intern zip-basiert)

### Spezialformate
- **E-Books**: `.epub`
- **Daten**: `.csv`, `.tsv`, `.json`

## Architektur

### Kernkomponenten

- **FileReader** (`src/file_reader/core.py`): Hauptorchestrator für Dateiinhalt-Extraktion
- **MCP Server** (`src/mcp_server.py`): FastMCP-basierter Server, der MCP-Tools bereitstellt
- **Parser System** (`src/file_reader/parsers/`): Spezialisierte Parser für verschiedene Dateitypen
- **Cache Manager** (`src/file_reader/cache_manager.py`): Einheitliches Cache-System
- **Storage Layer** (`src/file_reader/storage/`): Sicherer lokaler Dateizugriff

### Leistungsoptimierungen

1. **Einheitlicher Cache**: Einzelne Cache-Instanz statt mehrerer (reduziert von ~6GB auf 500MB Standard)
2. **Lazy Loading**: Parser werden bei Bedarf geladen, nicht beim Start
3. **Abhängigkeitsoptimierung**: Optionale Abhängigkeiten für erweiterte Funktionen
4. **Ressourcenlimits**: Konfigurierbare Speicher- und Dateigrößenlimits

## Entwicklung

### Entwicklungsumgebung einrichten

```bash
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
uv sync
source .venv/bin/activate  # Auf Unix/macOS
```

### Tests ausführen

```bash
# Alle Tests ausführen
uv run python tests/run_tests.py

# Spezifische Testkategorien
uv run python tests/run_tests.py --models     # Datenmodelle
uv run python tests/run_tests.py --parsers    # Dateiparser
uv run python tests/run_tests.py --core       # Kernfunktionalität
uv run python tests/run_tests.py --server     # MCP-Server

# Mit Coverage
uv run python tests/run_tests.py -c

# Alternative pytest-Verwendung
PYTHONPATH=src uv run pytest tests/ -v
```

### Neue Parser hinzufügen

1. Parser in `src/file_reader/parsers/` erstellen
2. Von `BaseParser` erben
3. In `parser_loader.py` registrieren
4. Tests in `tests/test_parsers.py` hinzufügen

Siehe [CONTRIBUTING.md](CONTRIBUTING.md) für detaillierte Entwicklungsrichtlinien.

## Leistungsmerkmale

- **Smart-Caching**: Sofortiger Zugriff auf zuvor verarbeitete Dateien ohne Neukonvertierung
- **Effiziente Speichernutzung**: Optimiert von 6GB+ auf 500MB Standard-Cache-Größe
- **Blitzschneller Start**: 80% schneller mit On-Demand-Komponentenladung
- **Parallele Verarbeitung**: Behandelt mehrere Dokumentkonvertierungen gleichzeitig

## Systemanforderungen

- **Python**: 3.11+
- **Betriebssystem**: macOS, Linux, Windows
- **Speicher**: 2GB+ empfohlen für große Dateien
- **Optional**: LibreOffice (Legacy-Office-Dateien), Pandoc (spezielle Konvertierungen)

## FAQ

**F: Dateien werden nicht korrekt gelesen?**  
A: Stellen Sie sicher, dass `LOCAL_FILE_ALLOWED_DIRECTORIES` das Verzeichnis Ihrer Datei enthält.

**F: OCR funktioniert nicht für Bilder?**  
A: Konfigurieren Sie `LLM_VISION_API_KEY` mit einem gültigen Vision-Modell-API-Schlüssel (OpenAI GPT-4o oder kompatibel).

**F: Möchten Sie die Verarbeitungsgeschwindigkeit verbessern?**  
A: Der Smart-Cache erinnert sich automatisch an verarbeitete Dateien. Löschen Sie das Cache-Verzeichnis, wenn Sie eine frische Verarbeitung aller Dateien wünschen.

**F: Legacy-Office-Dateien (.doc/.ppt) schlagen fehl?**  
A: Installieren Sie LibreOffice: `brew install --cask libreoffice` (macOS) oder Äquivalent für Ihr Betriebssystem.

**F: Welche Dateiformate werden unterstützt?**  
A: PDF, Word, Excel, PowerPoint, OpenDocument, Bilder (mit OCR), Archive, Textdateien und mehr.

## Mitwirken

Wir begrüßen Beiträge! Bitte siehe [CONTRIBUTING.md](CONTRIBUTING.md) für Richtlinien, wie Sie zu diesem Projekt beitragen können.

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe die [LICENSE](LICENSE)-Datei für Details.

## Links

- **Issues**: [Issues melden](https://github.com/freefish1218/mcp-local-reader/issues)
- **Dokumentation**: [CLAUDE.md](CLAUDE.md) für detaillierte Entwicklungsanleitung
- **Model Context Protocol**: [Offizielle MCP-Dokumentation](https://modelcontextprotocol.io/)

## Danksagungen

- Erstellt mit [FastMCP](https://github.com/jlowin/fastmcp)
- PDF-Parsing unterstützt von [PyMuPDF4LLM](https://github.com/pymupdf/PyMuPDF4LLM)
- Cache-System mit [DiskCache](https://github.com/grantjenks/python-diskcache)