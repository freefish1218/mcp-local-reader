# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.2] - 2025-08-20

### Documentation
- Updated all README files (English, Chinese, Japanese, French, German) to use `start_mcp.sh` script for MCP server configuration
- Improved installation and setup instructions across all language versions

### Maintenance
- Updated .gitignore to ignore .playwright-mcp/ directory for cleaner repository structure

## [1.2.1] - 2025-08-17

### Changed
- Refactored server entry point: renamed `run_mcp_server.py` to `mcp_server.py` for better naming consistency

### Documentation
- Added Smithery platform integration screenshots and documentation

### Maintenance
- Added promotion directory to gitignore for cleaner repository structure

## [1.2.0] - 2025-08-16

### Added
- Multilingual README support with Chinese, Japanese, French, and German translations
- Comprehensive GitHub templates and project governance documentation
- File conversion tool (`convert_local_file`) for saving markdown output to filesystem

### Changed
- Unified cache system architecture for improved performance (reduced from ~6GB to 500MB default)
- Reorganized environment configuration sections for better clarity
- Simplified project structure with lazy loading optimization
- Updated development commands and environment setup documentation

### Security
- Enhanced file permissions and command safety measures
- Added secure handling for temporary files and directories
- Implemented command injection prevention with proper escaping

### Fixed
- Corrected pytest configuration section header
- Updated directory path in startup script
- Improved API method naming consistency

### Removed
- Removed absolute path permission control for simplified access
- Cleaned up debug and test scripts
- Removed unnecessary file upload and cache statistics logic

## [1.1.0] - 2025-07-30

### Added
- Initial release with PDF, Office, and image parsing capabilities
- MCP server implementation with FastMCP
- Local file reading with security controls
- OCR support for image text extraction
- Archive processing capabilities

### Features
- Multi-format document parsing (PDF, Office, OpenDocument, text, images)
- Intelligent caching system
- Secure local file access with directory restrictions
- Concurrent processing support
- Resource optimization and limits