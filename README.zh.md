# MCP-LOCAL-Reader

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.8%2B-green.svg)](https://github.com/jlowin/fastmcp)

[English](README.md) | [日本語](README_ja.md) | [Français](README_fr.md) | [Deutsch](README_de.md)

**AI就绪文档转换器** - 将任何本地文件转换为AI优化的Markdown格式，以便与Claude Desktop、Claude Code和其他MCP客户端无缝集成。

**智能文档处理** - 高性能本地文件内容提取，支持PDF、Office文档、图像等高级解析。自动将复杂文档转换为清晰、结构化的Markdown，使AI模型能够轻松理解和处理。

## 功能特性

### 📄 **AI优化文件处理**
- **PDF文档**: 使用PyMuPDF4LLM进行高级解析 → 输出清洁的Markdown
- **Office套件**: Word、Excel、PowerPoint → 结构化表格和文本
- **OpenDocument**: ODT、ODS、ODP → 标准化Markdown格式
- **文本和数据**: Markdown、JSON、CSV、EPUB → 增强AI可读性
- **图像**: OCR文本识别 → 可搜索的Markdown内容
- **压缩包**: 智能提取 → 有序的文档集合

### 🚀 **智能性能**
- **智能缓存**: 记住已处理的文件，即时重新访问
- **延迟加载**: 仅加载所需组件 - 启动速度提升80%
- **并发处理**: 同时处理多个文件
- **资源优化**: 通过智能限制防止系统过载

### 🔒 **安全与控制**
- **目录权限**: 限制访问特定目录
- **路径验证**: 通过绝对路径要求确保安全的文件访问
- **文件大小限制**: 通过可配置的大小限制防止DoS攻击
- **本地优先**: 数据不会离开您的机器 - 完全隐私

## 快速开始

### 先决条件

- Python 3.11+
- [uv包管理器](https://docs.astral.sh/uv/)

### 安装

#### 选项1: 一键设置（推荐）

```bash
# 克隆并自动配置
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
chmod +x install.sh && ./install.sh
```

安装程序将指导您完成三种安装模式:

1. **最小化**: 仅PDF和基本文本文件（最小占用空间）
2. **标准**: 支持Office文档，无OCR（推荐）
3. **完整**: 包含OCR和压缩包处理的所有功能

#### 选项2: 手动安装

```bash
# 安装uv包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh

# 设置项目
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
uv sync

# 配置环境
cp env.example .env
# 使用您的设置编辑.env

# 启动服务器
uv run python run_mcp_server.py
```

### Claude Desktop配置

#### 自动配置
```bash
chmod +x configure_claude.sh && ./configure_claude.sh
```

#### 手动配置
编辑 `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) 或等效文件:

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

### Claude Code配置

添加到 `.claude/claude_config.json`:
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

## 使用方法

设置完成后，在对话中直接使用这些功能:

### 📄 读取并转换为AI就绪Markdown

将任何文件转换为AI优化的Markdown格式:

```
读取 /Users/username/Documents/report.pdf 的内容
→ 转换为带有表格、标题和结构的清洁Markdown

解析 /Users/username/data.xlsx 并显示数据结构  
→ 将电子表格数据提取为Markdown表格

从 /Users/username/presentation.pptx 提取文本
→ 将幻灯片组织为结构化的Markdown部分
```

### 🔄 保存为Markdown文件

转换并保存文档为AI就绪的Markdown文件:

```
将 /Users/username/contract.pdf 转换为Markdown格式
→ 创建带有结构化内容的contract.pdf.md

将 /Users/username/analysis.xlsx 保存为Markdown到 /Users/username/output/
→ 将格式化的表格和数据保存为Markdown
```

## 配置

### 基本设置 (.env)

```bash
# 文件访问控制（必需）
LOCAL_FILE_ALLOWED_DIRECTORIES=/Users/username/Documents,/Users/username/Downloads

# 性能优化
TOTAL_CACHE_SIZE_MB=500          # 统一缓存限制
CACHE_EXPIRE_DAYS=30             # 缓存保留期
FILE_READER_MAX_FILE_SIZE_MB=20  # 文件大小限制

# 日志记录
LOG_LEVEL=INFO
```

### 可选OCR设置

用于图像文本识别:

```bash
# OCR视觉模型
LLM_VISION_BASE_URL=https://api.openai.com/v1
LLM_VISION_API_KEY=sk-your-api-key-here
LLM_VISION_MODEL=gpt-4o  # 或qwen-vl-plus
```

## 环境变量

| 变量 | 必需 | 默认值 | 描述 |
|----------|----------|---------|-------------|
| `LOCAL_FILE_ALLOWED_DIRECTORIES` | ✅ | `current_dir` | 逗号分隔的允许目录 |
| `TOTAL_CACHE_SIZE_MB` | ❌ | `500` | 统一缓存大小限制 |
| `FILE_READER_MAX_FILE_SIZE_MB` | ❌ | `20` | 最大文件大小 |
| `LOG_LEVEL` | ❌ | `INFO` | 日志级别 |
| `LLM_VISION_API_KEY` | ❌ | - | OCR视觉模型API密钥 |

## MCP工具

### `read_local_file`

从本地文件提取内容并返回AI优化的Markdown。

| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `file_path` | string | 文件的绝对路径 |
| `max_size` | number | 文件大小限制（MB）（可选） |

### `convert_local_file`

将文件转换为AI就绪的Markdown并保存到文件系统。

| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `file_path` | string | 输入文件的绝对路径 |
| `output_path` | string | 输出路径（可选，默认为输入+.md） |
| `max_size` | number | 文件大小限制（MB）（可选） |
| `overwrite` | boolean | 覆盖现有文件（默认：false） |

## 支持的文件类型

### 文档格式
- **PDF**: `.pdf`
- **Microsoft Office**: `.doc`, `.docx`, `.ppt`, `.pptx`, `.xls`, `.xlsx`
- **OpenDocument**: `.odt`, `.ods`, `.odp`
- **文本**: `.txt`, `.md`, `.rtf`, `.csv`, `.json`, `.xml`

### 图像格式（支持OCR）
- **常见**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`
- **高级**: `.webp`, `.svg`

### 压缩包格式
- **压缩**: `.zip`, `.tar`, `.tar.gz`, `.7z`
- **Office**: `.docx`, `.xlsx`, `.pptx`（内部基于zip）

### 特殊格式
- **电子书**: `.epub`
- **数据**: `.csv`, `.tsv`, `.json`

## 架构

### 核心组件

- **FileReader** (`src/file_reader/core.py`): 文件内容提取的主要协调器
- **MCP Server** (`src/mcp_server.py`): 基于FastMCP的服务器，提供MCP工具
- **Parser System** (`src/file_reader/parsers/`): 针对不同文件类型的专门解析器
- **Cache Manager** (`src/file_reader/cache_manager.py`): 统一缓存系统
- **Storage Layer** (`src/file_reader/storage/`): 安全的本地文件访问

### 性能优化

1. **统一缓存**: 使用单个缓存实例而非多个（从约6GB减少到500MB默认）
2. **延迟加载**: 按需加载解析器，而非启动时加载
3. **依赖优化**: 高级功能的可选依赖
4. **资源限制**: 可配置的内存和文件大小限制

## 开发

### 设置开发环境

```bash
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
uv sync
source .venv/bin/activate  # 在Unix/macOS上
```

### 运行测试

```bash
# 运行所有测试
uv run python tests/run_tests.py

# 特定测试类别
uv run python tests/run_tests.py --models     # 数据模型
uv run python tests/run_tests.py --parsers    # 文件解析器
uv run python tests/run_tests.py --core       # 核心功能
uv run python tests/run_tests.py --server     # MCP服务器

# 带覆盖率
uv run python tests/run_tests.py -c

# 替代pytest用法
PYTHONPATH=src uv run pytest tests/ -v
```

### 添加新解析器

1. 在 `src/file_reader/parsers/` 中创建解析器
2. 继承自 `BaseParser`
3. 在 `parser_loader.py` 中注册
4. 在 `tests/test_parsers.py` 中添加测试

详细的开发指南请参见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 性能特征

- **智能缓存**: 即时访问以前处理过的文件而无需重新转换
- **高效内存使用**: 从6GB+优化到500MB默认缓存大小
- **闪电启动**: 通过按需组件加载实现80%更快的启动
- **并行处理**: 同时处理多个文档转换

## 系统要求

- **Python**: 3.11+
- **操作系统**: macOS、Linux、Windows
- **内存**: 推荐2GB+用于大文件
- **可选**: LibreOffice（旧版Office文件）、Pandoc（特殊转换）

## 常见问题

**Q: 文件读取不正确？**  
A: 确保 `LOCAL_FILE_ALLOWED_DIRECTORIES` 包含您的文件目录。

**Q: 图像OCR不工作？**  
A: 使用有效的视觉模型API密钥（OpenAI GPT-4o或兼容）配置 `LLM_VISION_API_KEY`。

**Q: 想要提高处理速度？**  
A: 智能缓存会自动记住已处理的文件。如果您想要所有文件的新鲜处理，请清除缓存目录。

**Q: 旧版Office文件（.doc/.ppt）失败？**  
A: 安装LibreOffice: `brew install --cask libreoffice` (macOS) 或您操作系统的等效命令。

**Q: 支持哪些文件格式？**  
A: PDF、Word、Excel、PowerPoint、OpenDocument、图像（带OCR）、压缩包、文本文件等。

## 贡献

我们欢迎贡献！请参见 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何为此项目做出贡献的指南。

## 许可证

此项目在MIT许可证下授权 - 有关详细信息，请参见 [LICENSE](LICENSE) 文件。

## 链接

- **问题**: [报告问题](https://github.com/freefish1218/mcp-local-reader/issues)
- **文档**: [CLAUDE.md](CLAUDE.md) 详细开发指南
- **模型上下文协议**: [官方MCP文档](https://modelcontextprotocol.io/)

## 致谢

- 使用 [FastMCP](https://github.com/jlowin/fastmcp) 构建
- PDF解析由 [PyMuPDF4LLM](https://github.com/pymupdf/PyMuPDF4LLM) 提供支持
- 缓存系统使用 [DiskCache](https://github.com/grantjenks/python-diskcache)