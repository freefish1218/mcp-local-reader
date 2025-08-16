# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP-LOCAL-Reader is a Model Context Protocol (MCP) server that provides local file content extraction services. It's designed for efficient local file reading with intelligent structured content extraction, supporting PDF, Office documents, images (with OCR), compressed files, and more.

## Key Design Principles

1. **Local-First**: Optimized for local file system access, not suitable for containerization
2. **Resource Efficient**: Lazy loading, unified caching, minimal dependencies
3. **Security Focused**: Path validation, directory permissions, safe file access
4. **Developer Friendly**: Simple installation, clear configuration, easy debugging

## Development Commands

### Environment Setup
```bash
# Install uv package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies using uv
uv sync

# Activate virtual environment
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows
```

### Testing
```bash
# Run all tests
uv run python tests/run_tests.py

# Run specific test categories
uv run python tests/run_tests.py --models     # Data model tests
uv run python tests/run_tests.py --parsers    # Parser tests  
uv run python tests/run_tests.py --core       # Core functionality tests
uv run python tests/run_tests.py --server     # MCP server tests

# Run with coverage
uv run python tests/run_tests.py -c

# Alternative pytest usage
PYTHONPATH=src uv run pytest tests/ -v
```

### Server Operations
```bash
# Start MCP server locally
uv run python run_mcp_server.py

# Quick installation
./install.sh

# Configure Claude Desktop
./configure_claude.sh
```

## Architecture Overview

### Core Components

**FileReader (`src/file_reader/core.py`)**: Main orchestrator for local file content extraction. Handles batch processing, concurrency control, and cache coordination.

**MCP Server (`src/mcp_server.py`)**: FastMCP-based server providing MCP tools. Focuses exclusively on local file system operations.

**Parser System (`src/file_reader/parsers/`)**: 
- `BaseParser`: Abstract base with caching and image processing mixins
- Specialized parsers: `PDFParser`, `OfficeParser`, `TextParser`, `ImageParser`, `ArchiveParser`
- Each parser extracts structured markdown content from specific file types

**Parser Loader (`src/file_reader/parser_loader.py`)**: Lazy loading manager for parsers
- Loads parsers only when needed
- Checks dependency availability
- Reduces startup time and memory usage

**Cache Manager (`src/file_reader/cache_manager.py`)**: Unified caching system
- Single cache instance for all components
- LRU eviction policy
- Configurable size limits (default 500MB)
- Namespace isolation for different cache types

**Storage Layer (`src/file_reader/storage/`)**: 
- `LocalFileStorageClient`: Secure local file access with permission controls
- Path validation and directory restrictions
- Extensible for future storage backends

### Performance Optimizations

1. **Unified Caching**: Single DiskCache instance instead of multiple (reduced from ~6GB to 500MB default)
2. **Lazy Loading**: Parsers loaded on-demand, not at startup
3. **Dependency Optimization**: Optional dependencies for advanced features
4. **Resource Limits**: Configurable memory and file size limits

## MCP Tools Provided

- `read_local_file`: Read and parse local files (PDF, Office, images, etc.)
- `convert_local_file`: Convert files to markdown and save to filesystem

## Configuration

### Essential Settings (.env)
```bash
# Cache configuration (optimized defaults)
CACHE_ROOT_DIR=cache
CACHE_EXPIRE_DAYS=30
TOTAL_CACHE_SIZE_MB=500  # Unified cache size

# Local file access control
LOCAL_FILE_ALLOWED_DIRECTORIES=/Users/username
LOCAL_FILE_ALLOW_ABSOLUTE_PATHS=true
FILE_READER_MAX_FILE_SIZE_MB=20

# Logging
LOG_LEVEL=INFO
```

### Optional OCR Configuration
```bash
# Vision model for image OCR
LLM_VISION_BASE_URL=https://api.example.com
LLM_VISION_API_KEY=sk-xxxxxxxxxx
LLM_VISION_MODEL=qwen-vl-plus
```

## Installation Modes

The `install.sh` script supports three modes:

1. **Minimal**: PDF and basic text files only (smallest footprint)
2. **Standard**: Office documents support, no OCR (recommended)
3. **Complete**: All features including OCR and archive processing

## Dependencies Management

### Core Dependencies (always required)
- `fastmcp>=2.8.0`: MCP server framework
- `pydantic>=2.11.4`: Data validation
- `diskcache>=5.6.3`: Caching system
- `pymupdf4llm>=0.0.24`: PDF parsing

### Optional Dependencies
- Office support: `python-pptx`, `openpyxl`, `odfpy`
- OCR support: `langchain_openai`, `Pillow`
- Data processing: `pandas`, `tabulate`

### External Tools (optional)
- LibreOffice: For legacy .doc/.ppt files
- Pandoc: For special document conversions

## Code Style Guidelines

- Use type hints for all function parameters and returns
- Follow existing patterns in the codebase
- Keep methods focused and single-purpose
- Add docstrings for public methods
- Use logging instead of print statements
- Handle exceptions gracefully with proper error messages

## Common Development Tasks

### Adding a New Parser
1. Create parser in `src/file_reader/parsers/`
2. Inherit from `BaseParser`
3. Register in `parser_loader.py` mapping
4. Add tests in `tests/test_parsers.py`

### Debugging File Parsing
```python
# Enable debug logging
LOG_LEVEL=DEBUG uv run python run_mcp_server.py

# Test specific file
from src.file_reader import FileReader, LocalReadRequest
reader = FileReader()
request = LocalReadRequest(file_paths=["/path/to/file.pdf"])
response = await reader.read_file(request)
```

### Performance Profiling
```bash
# Run with profiling
python -m cProfile -o profile.stats run_mcp_server.py

# Analyze results
python -m pstats profile.stats
```

## Security Considerations

- Always validate file paths before access
- Use `LOCAL_FILE_ALLOWED_DIRECTORIES` to restrict access
- Sanitize file names when creating cache keys
- Never execute code from parsed documents
- Limit file sizes to prevent DoS

## Troubleshooting

### Common Issues

1. **Parser not found**: Check if dependencies are installed
2. **Cache errors**: Clear cache directory and restart
3. **OCR not working**: Verify LLM_VISION_API_KEY is set
4. **Old Office files fail**: Install LibreOffice

### Debug Commands
```bash
# Check available parsers
python -c "from src.file_reader.parser_loader import parser_loader; print(parser_loader.available_parsers)"

# Clear all caches
rm -rf cache/

# Test MCP connection
uv run python -c "from src.mcp_server import mcp; print(mcp)"
```

## Future Improvements

- [ ] Streaming support for large files
- [ ] Parallel parser execution
- [ ] Plugin system for custom parsers
- [ ] Web UI for configuration
- [ ] Metrics and monitoring