# MCP-LOCAL-Reader

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.8%2B-green.svg)](https://github.com/jlowin/fastmcp)

[中文版](README_zh.md) | [日本語](README_ja.md) | [Français](README_fr.md) | [Deutsch](README_de.md)

**AI-Ready Document Converter** - Transform any local file into AI-optimized markdown format for seamless integration with Claude Desktop, Claude Code, and other MCP clients.

**Intelligent Document Processing** - High-performance local file content extraction with advanced parsing for PDF, Office documents, images, and more. Automatically converts complex documents into clean, structured markdown that AI models can easily understand and process.

## Features

### 📄 **AI-Optimized File Processing**
- **PDF Documents**: Advanced parsing with PyMuPDF4LLM → Clean markdown output
- **Office Suite**: Word, Excel, PowerPoint → Structured tables and text
- **OpenDocument**: ODT, ODS, ODP → Standardized markdown format
- **Text & Data**: Markdown, JSON, CSV, EPUB → Enhanced AI readability
- **Images**: OCR text recognition → Searchable markdown content
- **Archives**: Smart extraction → Organized document collections

### 🚀 **Intelligent Performance**
- **Smart Caching**: Remembers processed files for instant re-access
- **Lazy Loading**: Only loads needed components - 80% faster startup
- **Concurrent Processing**: Handles multiple files simultaneously
- **Resource Optimization**: Prevents system overload with smart limits

### 🔒 **Security & Control**
- **Directory Permissions**: Restrict access to specific directories
- **Path Validation**: Secure file access with absolute path requirements
- **File Size Limits**: Prevent DoS with configurable size restrictions
- **Local-First**: No data leaves your machine - complete privacy

## Quick Start

### Prerequisites

- Python 3.11+
- [uv package manager](https://docs.astral.sh/uv/)

### Installation

#### Option 1: One-Command Setup (Recommended)

```bash
# Clone and auto-configure
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
chmod +x install.sh && ./install.sh
```

The installer will guide you through three installation modes:

1. **Minimal**: PDF and basic text files only (smallest footprint)
2. **Standard**: Office documents support, no OCR (recommended)
3. **Complete**: All features including OCR and archive processing

#### Option 2: Manual Installation

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup project
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
uv sync

# Configure environment
cp env.example .env
# Edit .env with your settings

# Start server
uv run python mcp_server.py
```

### Configuration for Claude Desktop

#### Automatic Configuration
```bash
chmod +x configure_claude.sh && ./configure_claude.sh
```

#### Manual Configuration
Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent:

```json
{
  "mcpServers": {
    "mcp-local-reader": {
      "command": "uv",
      "args": [
        "run", 
        "python", 
        "/absolute/path/to/mcp-local-reader/mcp_server.py"
      ],
      "env": {
        "LOCAL_FILE_ALLOWED_DIRECTORIES": "/Users/username/Documents,/Users/username/Downloads"
      }
    }
  }
}
```

### Configuration for Claude Code

Add to `.claude/claude_config.json`:
```json
{
  "mcpServers": {
    "mcp-local-reader": {
      "command": "uv",
      "args": [
        "run", 
        "python", 
        "/absolute/path/to/mcp-local-reader/mcp_server.py"
      ],
      "env": {
        "LOCAL_FILE_ALLOWED_DIRECTORIES": "/Users/username/Documents,/Users/username/Downloads"
      }
    }
  }
}
```

## Usage

After setup, use these features directly in conversations:

### 📄 Read & Convert to AI-Ready Markdown

Transform any file into AI-optimized markdown format:

```
Read the content from /Users/username/Documents/report.pdf
→ Converts to clean markdown with tables, headings, and structure

Parse /Users/username/data.xlsx and show me the data structure  
→ Extracts spreadsheet data as markdown tables

Extract text from /Users/username/presentation.pptx
→ Organizes slides into structured markdown sections
```

### 🔄 Save as Markdown Files

Convert and save documents as AI-ready markdown files:

```
Convert /Users/username/contract.pdf to markdown format
→ Creates contract.pdf.md with structured content

Save /Users/username/analysis.xlsx as markdown in /Users/username/output/
→ Saves formatted tables and data as markdown
```

## Configuration

### Essential Settings (.env)

```bash
# File access control (REQUIRED)
LOCAL_FILE_ALLOWED_DIRECTORIES=/Users/username/Documents,/Users/username/Downloads

# Performance optimization
TOTAL_CACHE_SIZE_MB=500          # Unified cache limit
CACHE_EXPIRE_DAYS=30             # Cache retention
FILE_READER_MAX_FILE_SIZE_MB=20  # File size limit

# Logging
LOG_LEVEL=INFO
```

### Optional OCR Settings

For image text recognition:

```bash
# Vision model for OCR
LLM_VISION_BASE_URL=https://api.openai.com/v1
LLM_VISION_API_KEY=sk-your-api-key-here
LLM_VISION_MODEL=gpt-4o  # or qwen-vl-plus
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOCAL_FILE_ALLOWED_DIRECTORIES` | ✅ | `current_dir` | Comma-separated allowed directories |
| `TOTAL_CACHE_SIZE_MB` | ❌ | `500` | Unified cache size limit |
| `FILE_READER_MAX_FILE_SIZE_MB` | ❌ | `20` | Maximum file size |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |
| `LLM_VISION_API_KEY` | ❌ | - | OCR vision model API key |

## MCP Tools

### `read_local_file`

Extract content from local files and return as AI-optimized markdown.

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | string | Absolute path to the file |
| `max_size` | number | File size limit in MB (optional) |

### `convert_local_file`

Convert files to AI-ready markdown and save to filesystem.

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | string | Absolute path to input file |
| `output_path` | string | Output path (optional, defaults to input+.md) |
| `max_size` | number | File size limit in MB (optional) |
| `overwrite` | boolean | Overwrite existing files (default: false) |

## Supported File Types

### Document Formats
- **PDF**: `.pdf`
- **Microsoft Office**: `.doc`, `.docx`, `.ppt`, `.pptx`, `.xls`, `.xlsx`
- **OpenDocument**: `.odt`, `.ods`, `.odp`
- **Text**: `.txt`, `.md`, `.rtf`, `.csv`, `.json`, `.xml`

### Image Formats (with OCR)
- **Common**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`
- **Advanced**: `.webp`, `.svg`

### Archive Formats
- **Compressed**: `.zip`, `.tar`, `.tar.gz`, `.7z`
- **Office**: `.docx`, `.xlsx`, `.pptx` (internally zip-based)

### Special Formats
- **E-books**: `.epub`
- **Data**: `.csv`, `.tsv`, `.json`

## Architecture

### Core Components

- **FileReader** (`src/file_reader/core.py`): Main orchestrator for file content extraction
- **MCP Server** (`src/mcp_server.py`): FastMCP-based server providing MCP tools
- **Parser System** (`src/file_reader/parsers/`): Specialized parsers for different file types
- **Cache Manager** (`src/file_reader/cache_manager.py`): Unified caching system
- **Storage Layer** (`src/file_reader/storage/`): Secure local file access

### Performance Optimizations

1. **Unified Caching**: Single cache instance instead of multiple (reduced from ~6GB to 500MB default)
2. **Lazy Loading**: Parsers loaded on-demand, not at startup
3. **Dependency Optimization**: Optional dependencies for advanced features
4. **Resource Limits**: Configurable memory and file size limits

## Development

### Setup Development Environment

```bash
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
uv sync
source .venv/bin/activate  # On Unix/macOS
```

### Running Tests

```bash
# Run all tests
uv run python tests/run_tests.py

# Specific test categories
uv run python tests/run_tests.py --models     # Data models
uv run python tests/run_tests.py --parsers    # File parsers
uv run python tests/run_tests.py --core       # Core functionality
uv run python tests/run_tests.py --server     # MCP server

# With coverage
uv run python tests/run_tests.py -c

# Alternative pytest usage
PYTHONPATH=src uv run pytest tests/ -v
```

### Adding New Parsers

1. Create parser in `src/file_reader/parsers/`
2. Inherit from `BaseParser` 
3. Register in `parser_loader.py`
4. Add tests in `tests/test_parsers.py`

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development guidelines.

## Performance Characteristics

- **Smart Caching**: Instantly access previously processed files without re-conversion
- **Efficient Memory Use**: Optimized from 6GB+ to 500MB default cache size
- **Lightning Startup**: 80% faster startup with on-demand component loading
- **Parallel Processing**: Handle multiple document conversions simultaneously

## System Requirements

- **Python**: 3.11+
- **OS**: macOS, Linux, Windows
- **Memory**: 2GB+ recommended for large files
- **Optional**: LibreOffice (legacy Office files), Pandoc (special conversions)

## FAQ

**Q: Files not reading correctly?**  
A: Ensure `LOCAL_FILE_ALLOWED_DIRECTORIES` includes your file's directory.

**Q: OCR not working for images?**  
A: Configure `LLM_VISION_API_KEY` with a valid vision model API key (OpenAI GPT-4o or compatible).

**Q: Want to improve processing speed?**  
A: The smart cache automatically remembers processed files. Clear cache directory if you want fresh processing of all files.

**Q: Legacy Office files (.doc/.ppt) failing?**  
A: Install LibreOffice: `brew install --cask libreoffice` (macOS) or equivalent for your OS.

**Q: What file formats are supported?**  
A: PDF, Word, Excel, PowerPoint, OpenDocument, images (with OCR), archives, text files, and more.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Links

- **Issues**: [Report Issues](https://github.com/freefish1218/mcp-local-reader/issues)
- **Documentation**: [CLAUDE.md](CLAUDE.md) for detailed development guide
- **Model Context Protocol**: [Official MCP Documentation](https://modelcontextprotocol.io/)

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- PDF parsing powered by [PyMuPDF4LLM](https://github.com/pymupdf/PyMuPDF4LLM)
- Caching system using [DiskCache](https://github.com/grantjenks/python-diskcache)