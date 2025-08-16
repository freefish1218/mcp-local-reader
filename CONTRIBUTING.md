# Contributing to MCP-LOCAL-Reader

Thank you for your interest in contributing to MCP-LOCAL-Reader! This guide will help you get started with development and ensure your contributions align with the project's standards.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting Guidelines](#issue-reporting-guidelines)
- [Adding New Features](#adding-new-features)

## Code of Conduct

This project and everyone participating in it is governed by our commitment to creating a welcoming and inclusive environment. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [uv package manager](https://docs.astral.sh/uv/)
- Git
- Basic understanding of the Model Context Protocol (MCP)

### First-time Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/mcp-local-reader.git
   cd mcp-local-reader
   ```
3. **Add the upstream remote**:
   ```bash
   git remote add upstream https://github.com/freefish1218/mcp-local-reader.git
   ```

## Development Setup

### Environment Setup

```bash
# Install uv package manager (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows
```

### Configuration

```bash
# Create development environment file
cp env.example .env

# Edit .env with development settings
LOCAL_FILE_ALLOWED_DIRECTORIES=/path/to/test/files
LOG_LEVEL=DEBUG
TOTAL_CACHE_SIZE_MB=100  # Smaller cache for development
```

### Verify Installation

```bash
# Test the installation
uv run python tests/run_tests.py

# Test MCP server startup
uv run python run_mcp_server.py
```

## Project Structure

```
mcp-local-reader/
├── src/
│   ├── file_reader/
│   │   ├── core.py              # Main FileReader orchestrator
│   │   ├── cache_manager.py     # Unified caching system
│   │   ├── parser_loader.py     # Lazy parser loading
│   │   ├── parsers/             # File format parsers
│   │   │   ├── base.py          # BaseParser abstract class
│   │   │   ├── pdf_parser.py    # PDF document parser
│   │   │   ├── office_parser.py # Office document parser
│   │   │   ├── image_parser.py  # Image + OCR parser
│   │   │   ├── text_parser.py   # Text format parser
│   │   │   ├── archive_parser.py # Archive extraction parser
│   │   │   └── mixins/          # Reusable parser functionality
│   │   └── storage/             # Storage abstraction layer
│   └── mcp_server.py            # FastMCP server implementation
├── tests/                       # Test suite
├── install.sh                   # Automated installation script
├── configure_claude.sh          # Claude Desktop configuration
└── docs/                        # Documentation
```

## Development Workflow

### 1. Create a Feature Branch

```bash
# Sync with upstream
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write your code following the [Code Style Guidelines](#code-style-guidelines)
- Add tests for new functionality
- Update documentation as needed
- Test your changes thoroughly

### 3. Commit Changes

```bash
# Stage your changes
git add .

# Commit with descriptive message
git commit -m "feat: add support for new file format

- Implement XYZ parser for .abc files
- Add comprehensive tests
- Update documentation"
```

### 4. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
```

## Code Style Guidelines

### Python Code Style

We follow PEP 8 with some modifications:

- **Line length**: 88 characters (Black formatter default)
- **Type hints**: Required for all function parameters and return values
- **Docstrings**: Google style for public methods and classes
- **Imports**: Use absolute imports, group by standard/third-party/local

### Example Code Style

```python
from typing import Optional, Dict, Any
from pathlib import Path

from src.file_reader.models import ProcessingResult
from src.file_reader.parsers.base import BaseParser


class ExampleParser(BaseParser):
    """Example parser demonstrating code style guidelines.
    
    This parser handles example file formats and demonstrates
    the expected code structure and documentation style.
    
    Args:
        config: Parser configuration options
        cache_manager: Unified cache manager instance
    """
    
    def __init__(self, config: Dict[str, Any], cache_manager: Any) -> None:
        super().__init__(config, cache_manager)
        self._initialize_parser()
    
    def parse_file(self, file_path: Path, **kwargs) -> ProcessingResult:
        """Parse a file and return structured content.
        
        Args:
            file_path: Absolute path to the file to parse
            **kwargs: Additional parsing options
            
        Returns:
            ProcessingResult containing parsed content and metadata
            
        Raises:
            ParsingError: If file cannot be parsed
        """
        try:
            # Implementation here
            return self._process_content(content)
        except Exception as e:
            self.logger.error(f"Failed to parse {file_path}: {e}")
            raise ParsingError(f"Parsing failed: {e}") from e
    
    def _process_content(self, content: str) -> ProcessingResult:
        """Private method for content processing."""
        # Private methods start with underscore
        pass
```

### Documentation Style

- **Public methods**: Comprehensive Google-style docstrings
- **Private methods**: Brief description of purpose
- **Classes**: Description, args, and usage examples
- **Modules**: File-level docstring explaining purpose

### Error Handling

```python
# Good: Specific exception handling
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise ProcessingError("User-friendly message") from e

# Good: Resource cleanup
with open(file_path, 'rb') as f:
    data = f.read()

# Good: Validation
if not file_path.exists():
    raise FileNotFoundError(f"File not found: {file_path}")
```

## Testing Requirements

### Test Categories

We use categorized testing for different components:

```bash
# Run all tests
uv run python tests/run_tests.py

# Run specific categories
uv run python tests/run_tests.py --models     # Data model tests
uv run python tests/run_tests.py --parsers    # Parser tests
uv run python tests/run_tests.py --core       # Core functionality
uv run python tests/run_tests.py --server     # MCP server tests

# Run with coverage
uv run python tests/run_tests.py -c
```

### Writing Tests

#### Unit Tests

```python
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.file_reader.parsers.example_parser import ExampleParser
from src.file_reader.models import ProcessingResult


class TestExampleParser:
    """Test suite for ExampleParser."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance for testing."""
        config = {"max_file_size": 10 * 1024 * 1024}
        cache_manager = Mock()
        return ExampleParser(config, cache_manager)
    
    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create sample file for testing."""
        file_path = tmp_path / "test.example"
        file_path.write_text("Sample content")
        return file_path
    
    def test_parse_valid_file(self, parser, sample_file):
        """Test parsing a valid file."""
        result = parser.parse_file(sample_file)
        
        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert "Sample content" in result.content
    
    def test_parse_nonexistent_file(self, parser):
        """Test error handling for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            parser.parse_file(Path("/nonexistent/file.example"))
    
    @patch('src.file_reader.parsers.example_parser.external_library')
    def test_parse_with_mock(self, mock_library, parser, sample_file):
        """Test parsing with mocked external dependency."""
        mock_library.process.return_value = "Processed content"
        
        result = parser.parse_file(sample_file)
        
        mock_library.process.assert_called_once()
        assert "Processed content" in result.content
```

#### Integration Tests

```python
def test_file_reader_integration(tmp_path):
    """Test complete file reading workflow."""
    # Create test file
    test_file = tmp_path / "integration_test.pdf"
    create_sample_pdf(test_file)
    
    # Test FileReader
    from src.file_reader.core import FileReader
    from src.file_reader.models import LocalReadRequest
    
    reader = FileReader()
    request = LocalReadRequest(file_paths=[str(test_file)])
    
    response = await reader.read_file(request)
    
    assert response.success is True
    assert len(response.results) == 1
    assert response.results[0].content is not None
```

### Test Files

- Place test files in `tests/files/`
- Use small, representative files
- Include files that test edge cases
- Document the purpose of each test file

### Coverage Requirements

- **Minimum coverage**: 80% for all new code
- **Critical paths**: 90%+ coverage for core functionality
- **Parsers**: 85%+ coverage for each parser

## Pull Request Process

### Before Submitting

1. **Run all tests**: `uv run python tests/run_tests.py -c`
2. **Check code style**: Ensure code follows guidelines
3. **Update documentation**: Include relevant documentation updates
4. **Test manually**: Verify changes work in real scenarios

### PR Title Format

Use conventional commit format:

- `feat: add new parser for XYZ format`
- `fix: resolve caching issue with large files`
- `docs: update installation instructions`
- `refactor: improve parser performance`
- `test: add comprehensive parser tests`

### PR Description Template

```markdown
## Description
Brief description of the changes and their purpose.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## How Has This Been Tested?
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows the project's style guidelines
- [ ] Self-review of code completed
- [ ] Code is properly commented
- [ ] Corresponding documentation updates made
- [ ] Tests added for new functionality
- [ ] All tests pass
```

### Review Process

1. **Automated checks**: CI/CD runs tests and checks
2. **Code review**: Maintainers review code quality and design
3. **Testing**: Reviewers may test functionality
4. **Approval**: At least one maintainer approval required
5. **Merge**: Squash and merge to main branch

## Issue Reporting Guidelines

### Before Creating an Issue

1. **Search existing issues** to avoid duplicates
2. **Check documentation** for solutions
3. **Try the latest version** to see if issue is resolved

### Bug Reports

Use the bug report template and include:

- **Environment details**: OS, Python version, package versions
- **Steps to reproduce**: Clear, minimal reproduction steps
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Error messages**: Full error output
- **Sample files**: If relevant, provide sample files (ensure no sensitive data)

### Feature Requests

Use the feature request template and include:

- **Problem description**: What problem does this solve?
- **Proposed solution**: How should it work?
- **Alternatives considered**: Other approaches considered
- **Use cases**: Real-world scenarios where this helps

## Adding New Features

### Parser Development

To add support for a new file format:

1. **Create parser class**:
   ```python
   # src/file_reader/parsers/new_format_parser.py
   from .base import BaseParser
   
   class NewFormatParser(BaseParser):
       """Parser for new file format."""
       
       SUPPORTED_EXTENSIONS = ['.new', '.format']
       
       def parse_file(self, file_path: Path, **kwargs) -> ProcessingResult:
           # Implementation
           pass
   ```

2. **Register parser**:
   ```python
   # src/file_reader/parser_loader.py
   PARSER_MAPPING = {
       # ... existing parsers
       '.new': 'new_format_parser.NewFormatParser',
       '.format': 'new_format_parser.NewFormatParser',
   }
   ```

3. **Add tests**:
   ```python
   # tests/test_new_format_parser.py
   class TestNewFormatParser:
       # Comprehensive test suite
       pass
   ```

4. **Update documentation**: Add to supported formats list

### Dependencies

- **Core dependencies**: Add to `pyproject.toml` dependencies
- **Optional dependencies**: Add to extras in `pyproject.toml`
- **External tools**: Document in installation guide

### Configuration

New configuration options should:

- Have sensible defaults
- Be documented in `env.example`
- Include validation in configuration loading
- Be backward compatible when possible

## Getting Help

- **Documentation**: Check [CLAUDE.md](CLAUDE.md) for detailed technical docs
- **Issues**: Search existing issues or create new one
- **Discussions**: Use GitHub Discussions for general questions

## Recognition

Contributors will be acknowledged in:

- Git commit history
- Release notes for significant contributions
- README acknowledgments section

Thank you for contributing to MCP-LOCAL-Reader!