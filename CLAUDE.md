# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP-LOCAL-Reader is a Model Context Protocol (MCP) server that provides local file content extraction services. It supports reading local files with intelligent structured content extraction. The system supports PDF, Office documents, images (with OCR), compressed files, and more.

## Development Commands

### Testing
```bash
# Run all tests
python tests/run_tests.py

# Run specific test categories
python tests/run_tests.py --models     # Data model tests
python tests/run_tests.py --parsers    # Parser tests  
python tests/run_tests.py --core       # Core functionality tests
python tests/run_tests.py --server     # MCP server tests

# Run with coverage
python tests/run_tests.py -c

# Run specific test file
python tests/run_tests.py tests/test_core.py

# Alternative pytest direct usage
python -m pytest tests/ -v
```

### Server Operations
```bash
# Start MCP server locally
python run_server.py

# Test with example client
python client_example.py
```

## Architecture Overview

### Core Components

**FileReader (`src/file_reader/core.py`)**: Main orchestrator class that coordinates all components for local file content extraction. Handles batch processing, concurrency, and caching.

**MCP Server (`src/mcp_server.py`)**: FastMCP-based server providing MCP tools for local file reading. Simplified to only handle local file system access.

**Storage Layer (`src/file_reader/storage/`)**: 
- `LocalFileStorageClient`: Reads local filesystem files with permission and security controls
- Base abstraction allows pluggable storage backends if needed

**Parser System (`src/file_reader/parsers/`)**: Modular parser architecture with:
- `BaseParser`: Abstract base with caching and image processing mixins
- Specialized parsers: `PDFParser`, `OfficeParser`, `TextParser`, `ImageParser`, `ArchiveParser`
- Each parser handles specific file types and extracts structured markdown content

**Caching System**: Multi-level caching with separate SQLite databases:
- `parsed_cache/`: Stores parsed document content  
- `document_images/`: Caches extracted images
- `archive_files/`: Caches extracted archive contents

### Key Design Patterns

**Local File Focus**: System is designed specifically for local file system access with security controls and path validation.

**Modular Parsers**: Each file type has dedicated parser implementing `BaseParser` interface. Parsers use mixins for common functionality like image extraction.

**Async/Concurrent Processing**: Core uses asyncio and ThreadPoolExecutor for concurrent file processing while maintaining thread safety for caches.

**Intelligent Caching**: Parsed results are cached based on content hash to avoid reprocessing identical files.

## MCP Tools Provided

- `read_local_files`: Read local filesystem files with absolute path validation

## Configuration

Environment variables are defined in `env.example`. Key settings:
- `OPENAI_API_KEY`: Required for image OCR processing
- `FILE_READER_MAX_WORKERS`: Concurrent processing threads (3-10 recommended)
- `LOCAL_FILE_ALLOWED_DIRECTORIES`: Comma-separated list of allowed directories
- `LOCAL_FILE_ALLOW_ABSOLUTE_PATHS`: Whether to allow absolute path access
- Cache and file size limits configurable via environment variables

## Dependencies

Core dependencies managed in `requirements.txt`:
- `fastmcp>=2.8.0`: MCP server framework
- `pymupdf4llm>=0.0.24`: PDF parsing
- `python-pptx`, `openpyxl`, `odfpy`: Office document parsing
- `langchain_openai`: Image OCR via GPT-4o
- `diskcache`: Local caching system
- External: LibreOffice for legacy Office formats, Pandoc for some document types