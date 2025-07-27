# MCP文件读取器 (MCP-LOCAL-Reader)

基于 Model Context Protocol (MCP) 的多格式文件内容提取服务，支持通过 URL 下载和本地文件读取，智能提取结构化内容。

## ToDo

- [x] 缓存图片信息需可共用
- [x] 输出 markdown 时，图片路径带 resource_id
- [x] word/ppt/excel 等，也支持图片提取
- [x] 缓存解析后的结果
- [x] HTTP下载服务集成，替换OSS直接访问
- [x] 上传本地文件识别时, 先上传 Storage（统一管理文件存储）
- [x] 对json进行处理
- [x] 对压缩文件进行处理（zip/rar/7z/tar/gz等），返回压缩文件中的文件列表及链接
- [ ] 考虑增加本地图片 OCR 识别（排除无效图片，需平衡性能和准确率）
- [ ] 返回的元数据信息太多，需精简
- [ ] 高价值图片预热（先简要判断图片是否重要/富文本）

## 🚀 核心功能

### 📄 支持的文件格式

- **PDF文档**: PyMuPDF4LLM 解析为 Markdown，支持图片提取 (`.pdf`)
- **Office文档**: Word (`.doc/.docx`)、Excel (`.xls/.xlsx`)、PowerPoint (`.ppt/.pptx`)
- **OpenDocument**: 文档 (`.odt`)、表格 (`.ods`)、演示 (`.odp`)
- **文本文件**: 纯文本 (`.txt`)、Markdown (`.md`)、RTF (`.rtf`)、CSV (`.csv`)
- **图像文件**: OCR 文字识别 (`.jpg/.png/.gif/.bmp/.webp/.tiff`)
- **压缩文件**: 解压并上传文件，生成资源链接 (`.zip/.rar/.7z/.tar/.gz/.tar.gz/.tgz`)

### 🔧 核心特性

- **MCP 协议**: 基于 FastMCP 框架，支持标准 MCP 客户端集成
- **多种读取模式**: URL 下载、本地文件读取、Docker 环境文件上传
- **智能缓存**: 解析结果和图片缓存，避免重复处理
- **并发处理**: 多线程并发处理，提升效率
- **OCR 识别**: 集成 OpenAI GPT-4o 进行图像文字识别
## 🏗️ 架构设计

```
mcp-local-reader/
├── src/
│   ├── file_reader/         # 核心文件读取模块
│   │   ├── core.py          # 文件读取器主类
│   │   ├── models.py        # 数据模型定义
│   │   ├── storage.py       # HTTP下载客户端
│   │   ├── *_cache.py       # 缓存管理
│   │   └── parsers/         # 解析器模块
│   │       ├── pdf_parser.py    # PDF解析器
│   │       ├── office_parser.py # Office文档解析器
│   │       ├── text_parser.py   # 文本文件解析器
│   │       ├── image_parser.py  # 图像OCR解析器
│   │       └── archive_parser.py # 压缩文件解析器
│   └── mcp_server.py        # MCP服务器实现
├── requirements.txt
└── pyproject.toml
```

## 🔧 安装部署

### 环境依赖

```bash
# 系统依赖（用于解析旧版Office文档）
apt-get install libreoffice  # Ubuntu/Debian
brew install libreoffice     # macOS
```

### Docker 部署（推荐）

```bash
# 1. 构建镜像
chmod +x build.sh && ./build.sh

# 2. 配置环境变量
cp env.example .env
# 编辑 .env 文件配置 OPENAI_API_KEY 等

# 3. 运行容器
docker run -d --name mcp-file-reader \
  -p 3004:3004 --env-file .env \
  -v $(pwd)/cache:/app/cache \
  mcp-file-reader:latest
```

### 本地安装

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
export OPENAI_API_KEY="your_openai_key"
export DOWNLOAD_SERVICE_URL="http://localhost:8080"

# 3. 启动服务
python run_server.py
```
## 📋 环境配置

### 必需配置
```bash
# OpenAI API (图像OCR)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o

# 下载服务
DOWNLOAD_SERVICE_URL=http://localhost:8080

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=3004
```

### 可选配置
```bash
# 文件读取器配置
FILE_READER_MAX_WORKERS=5                    # 最大并发工作线程数（推荐3-10，根据CPU核心数调整）
FILE_READER_MAX_FILE_SIZE_MB=50              # 单个文件大小限制(MB)
FILE_READER_MIN_CONTENT_LENGTH=10            # 最小内容长度
FILE_READER_MAX_FILES_PER_REQUEST=10         # 单次请求最大文件数量

# 缓存配置
CACHE_ROOT_DIR=cache
FILE_READER_CACHE_SIZE_MB=500
PDF_IMAGE_CACHE_SIZE_MB=5000

# 本地文件读取（非Docker环境）
LOCAL_FILE_ALLOWED_DIRECTORIES=/Users/user/documents
LOCAL_FILE_ALLOW_ABSOLUTE_PATHS=true
```

## 🔌 MCP 工具接口

### `get_server_info` - 获取服务信息
获取 MCP 文件读取器服务器的版本和基本信息

### `read_files` - 读取远程文件
通过 URL 下载并读取文件内容

**参数:**
- `urls`: 文件下载链接数组
- `referer`: HTTP Referer 头（可选）
- `max_size`: 单个文件大小限制(MB)（可选）
- `use_proxy`: 是否使用代理（可选）
- `max_retries`: 最大重试次数（可选）

### `read_local_files` - 读取本地文件
读取本地文件系统中的文件（仅非Docker环境）

**参数:**
- `file_paths`: 本地文件绝对路径数组
- `max_size`: 文件大小限制(MB)（可选）

### `upload_and_read_file` - 上传文件读取
上传文件并读取内容（仅Docker环境）

**参数:**
- `filename`: 文件名
- `content`: base64编码的文件内容
- `max_size`: 文件大小限制(MB)（可选）
- `cleanup_after`: 是否清理临时文件（默认true）

### `get_reader_stats` - 获取统计信息
获取文件读取器的运行统计信息

## 📖 使用示例

### MCP 客户端集成

**Claude Desktop 配置** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "file-reader": {
      "command": "python",
      "args": ["/path/to/mcp-file-reader/run_server.py"],
      "env": {
        "OPENAI_API_KEY": "your_openai_key"
      }
    }
  }
}
```

**VS Code 配置** (使用 MCP 扩展):
```json
{
  "mcp.servers": [
    {
      "name": "file-reader",
      "command": "python",
      "args": ["/path/to/mcp-file-reader/run_server.py"]
    }
  ]
}
```

### 命令行测试

```bash
# 启动服务
python run_server.py

# 测试客户端
python client_example.py
```

## ⚡ 技术特性

- **高效解析**: PyMuPDF4LLM(PDF)、python-pptx/openpyxl(Office)、odfpy(OpenDocument)
- **智能OCR**: OpenAI GPT-4o 视觉模型进行图像文字识别
- **多级缓存**: 解析结果缓存和图片资源缓存，避免重复处理
- **错误恢复**: 多层异常处理，优雅降级和详细错误分类
- **并发处理**: 异步多线程处理，支持批量文件操作
- **环境适配**: 自动检测Docker/本地环境，提供不同的文件访问方式

## 📝 日志与监控

- 组件化日志记录：每个解析器和组件独立日志文件
- 统计信息收集：处理成功率、缓存命中率等关键指标
- 错误分类追踪：详细的失败类型和原因记录

## 📄 许可证

MIT License