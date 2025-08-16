# MCP Local File Reader

🤖 **AI-Ready Document Converter** - Transform any local file into AI-optimized markdown format for seamless integration with Claude Desktop, Claude Code, and other MCP clients.

⚡ **Intelligent Document Processing** - High-performance local file content extraction with advanced parsing for PDF, Office documents, images, and more. Automatically converts complex documents into clean, structured markdown that AI models can easily understand and process.

## 🎯 Core Value: AI-Ready Document Conversion

**Transform ANY document format into perfectly structured markdown** - The key differentiator is our intelligent conversion engine that understands document structure and outputs markdown optimized for AI processing. No more wrestling with unstructured text or losing formatting context.

## 🌟 Why Choose MCP Local File Reader?

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

## 📋 Quick Setup

### Claude Desktop (Recommended)

**One-command setup:**
```bash
# Clone and auto-configure
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
chmod +x install.sh && ./install.sh
chmod +x configure_claude.sh && ./configure_claude.sh
```

**Manual configuration in `claude_desktop_config.json`:**
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
        "LOCAL_FILE_ALLOWED_DIRECTORIES": "/Users/username",
        "LOCAL_FILE_ALLOW_ABSOLUTE_PATHS": "true"
      }
    }
  }
}
```

### Claude Code

Add to `.claude/claude_config.json`:
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
        "LOCAL_FILE_ALLOWED_DIRECTORIES": "/Users/username",
        "LOCAL_FILE_ALLOW_ABSOLUTE_PATHS": "true"
      }
    }
  }
}
```

### Manual Installation

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
uv run python run_mcp_server.py
```

## 🛠 Usage

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

## ⚙️ Configuration

### Essential Settings (.env)

```bash
# File access control (REQUIRED)
LOCAL_FILE_ALLOWED_DIRECTORIES=/Users/username/Documents,/Users/username/Downloads
LOCAL_FILE_ALLOW_ABSOLUTE_PATHS=true

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

## 🔧 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOCAL_FILE_ALLOWED_DIRECTORIES` | ✅ | `current_dir` | Comma-separated allowed directories |
| `LOCAL_FILE_ALLOW_ABSOLUTE_PATHS` | ✅ | `false` | Enable absolute path access |
| `TOTAL_CACHE_SIZE_MB` | ❌ | `500` | Unified cache size limit |
| `FILE_READER_MAX_FILE_SIZE_MB` | ❌ | `20` | Maximum file size |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |
| `LLM_VISION_API_KEY` | ❌ | - | OCR vision model API key |

## 📝 Supported Tools

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

## ❓ FAQ

**Q: Files not reading correctly?**  
A: Ensure `LOCAL_FILE_ALLOWED_DIRECTORIES` includes your file's directory and `LOCAL_FILE_ALLOW_ABSOLUTE_PATHS=true`.

**Q: OCR not working for images?**  
A: Configure `LLM_VISION_API_KEY` with a valid vision model API key (OpenAI GPT-4o or compatible).

**Q: Want to improve processing speed?**  
A: The smart cache automatically remembers processed files. Clear cache directory if you want fresh processing of all files.

**Q: Legacy Office files (.doc/.ppt) failing?**  
A: Install LibreOffice: `brew install libreoffice` (macOS) or equivalent for your OS.

**Q: What file formats are supported?**  
A: PDF, Word, Excel, PowerPoint, OpenDocument, images (with OCR), archives, text files, and more.

## 🏗 Development

### Prerequisites

- Python 3.11+
- uv package manager
- Optional: LibreOffice, Pandoc

### Setup

```bash
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
uv sync
```

### Testing

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
```

### Adding New Parsers

1. Create parser in `src/file_reader/parsers/`
2. Inherit from `BaseParser` 
3. Register in `parser_loader.py`
4. Add tests in `tests/test_parsers.py`

### Performance Profiling

```bash
# Profile the server
python -m cProfile -o profile.stats src/mcp_server.py

# Analyze results
python -m pstats profile.stats
```

## 🏎 Performance Features

- **Smart Caching**: Instantly access previously processed files without re-conversion
- **Efficient Memory Use**: Optimized from 6GB+ to 500MB default cache size
- **Lightning Startup**: 80% faster startup with on-demand component loading
- **Parallel Processing**: Handle multiple document conversions simultaneously

## 📋 System Requirements

- **Python**: 3.11+
- **OS**: macOS, Linux, Windows
- **Memory**: 2GB+ recommended for large files
- **Optional**: LibreOffice (legacy Office files), Pandoc (special conversions)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 📖 Links

- Issues: [Report Issues](https://github.com/freefish1218/mcp-local-reader/issues)
- Documentation: [CLAUDE.md](CLAUDE.md) for detailed development guide

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.