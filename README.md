# MCP 本地文件读取器 (MCP-LOCAL-Reader)

基于 Model Context Protocol (MCP) 的本地文件内容提取服务，支持多种格式文件的智能解析和结构化内容提取。

## 🚀 核心功能

### 📄 支持的文件格式

- **PDF 文档**: 使用 PyMuPDF4LLM 解析为 Markdown，支持图片提取
- **Office 文档**: Word (`.doc/.docx`)、Excel (`.xls/.xlsx`)、PowerPoint (`.ppt/.pptx`)
- **OpenDocument**: 文档 (`.odt`)、表格 (`.ods`)、演示 (`.odp`)
- **文本文件**: 纯文本、Markdown、JSON、CSV、EPUB
- **图像文件**: OCR 文字识别 (`.jpg/.png/.gif/.bmp/.webp/.tiff`)
- **压缩文件**: 智能解压并处理内部文件 (`.zip/.rar/.7z/.tar/.gz`)

> 注：解析旧版 `.doc/.ppt` 文件需要安装 LibreOffice

### 🔧 核心特性

- **MCP 协议**: 基于 FastMCP 框架，完美集成 Claude Desktop
- **本地文件安全访问**: 支持目录权限控制和路径验证
- **智能缓存系统**: 避免重复解析，提升响应速度
- **并发处理**: 多线程并发，批量文件高效处理
- **按需加载**: 解析器懒加载机制，降低资源消耗
- **OCR 支持**: 可选配置视觉模型进行图像文字识别

## 📦 快速安装

### 最简安装（推荐）

```bash
# 1. 运行安装脚本
chmod +x install.sh
./install.sh

# 2. 配置 Claude Desktop
chmod +x configure_claude.sh
./configure_claude.sh
```

### 手动安装

```bash
# 1. 安装 uv 包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 创建虚拟环境并安装依赖
uv venv
uv sync

# 3. 复制并编辑配置文件
cp env.example .env
# 编辑 .env 设置必要的配置

# 4. 启动服务
source .venv/bin/activate
uv run python run_mcp_server.py
```

## ⚙️ 配置说明

### 基础配置 (.env)

```bash
# 缓存配置
CACHE_ROOT_DIR=cache
CACHE_EXPIRE_DAYS=30
TOTAL_CACHE_SIZE_MB=500  # 统一缓存大小限制

# 本地文件访问控制
LOCAL_FILE_ALLOWED_DIRECTORIES=/Users/username/Documents,/Users/username/Downloads
LOCAL_FILE_ALLOW_ABSOLUTE_PATHS=true

# 文件处理限制
FILE_READER_MAX_FILE_SIZE_MB=20
FILE_READER_MIN_CONTENT_LENGTH=10

# 日志级别
LOG_LEVEL=INFO
```

### OCR 配置（可选）

如需图像 OCR 功能，配置视觉模型：

```bash
# 视觉模型配置
LLM_VISION_BASE_URL=https://api.example.com
LLM_VISION_API_KEY=sk-xxxxxxxxxx
LLM_VISION_MODEL=qwen-vl-plus  # 或 gpt-4o
```

## 🔌 Claude Desktop 集成

### 自动配置

运行配置脚本：
```bash
./configure_claude.sh
```

### 手动配置

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "mcp-local-reader": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "/path/to/mcp-local-reader/run_mcp_server.py"
      ],
      "env": {
        "LOCAL_FILE_ALLOWED_DIRECTORIES": "/Users/username",
        "LOCAL_FILE_ALLOW_ABSOLUTE_PATHS": "true"
      }
    }
  }
}
```

## 📖 使用示例

在 Claude Desktop 中使用：

```
使用 read_local_file 工具读取 /Users/username/Documents/report.pdf

将 /Users/username/data.xlsx 转换为 markdown 格式
```

## 🏗️ 项目结构

```
mcp-local-reader/
├── src/
│   ├── file_reader/         # 核心文件读取模块
│   │   ├── core.py          # 文件读取器主类
│   │   ├── parser_loader.py # 解析器懒加载管理
│   │   ├── cache_manager.py # 统一缓存管理
│   │   ├── storage/         # 存储层抽象
│   │   └── parsers/         # 各类文件解析器
│   └── mcp_server.py        # MCP 服务器实现
├── tests/                   # 测试套件
├── install.sh              # 安装脚本
├── configure_claude.sh     # Claude 配置脚本
└── requirements.txt        # Python 依赖
```

## 🔨 开发指南

### 运行测试

```bash
# 运行所有测试
uv run python tests/run_tests.py

# 运行特定测试
uv run python tests/run_tests.py --parsers
uv run python tests/run_tests.py --core
```

### 添加新的解析器

1. 在 `src/file_reader/parsers/` 创建新解析器
2. 继承 `BaseParser` 类
3. 在 `parser_loader.py` 中注册映射

## 🚀 性能优化

- **缓存优化**: 统一缓存管理，默认 500MB 限制
- **懒加载**: 按需加载解析器，减少启动时间
- **并发控制**: 可配置最大工作线程数
- **文件大小限制**: 防止处理超大文件

## 📋 系统要求

- Python 3.11+
- macOS/Linux/Windows
- 可选：LibreOffice（旧版 Office 文件）
- 可选：Pandoc（特殊文档转换）

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License