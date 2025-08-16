#!/bin/bash
# MCP-LOCAL-Reader 快速安装脚本

set -e

echo "========================================="
echo "MCP-LOCAL-Reader 安装向导"
echo "========================================="
echo ""

# 检测操作系统
OS_TYPE=""
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
else
    echo "❌ 不支持的操作系统: $OSTYPE"
    exit 1
fi

echo "✅ 检测到操作系统: $OS_TYPE"

# 安装模式选择
echo ""
echo "请选择安装模式："
echo "1) 最小安装 (仅支持PDF和基础文档)"
echo "2) 标准安装 (支持Office文档，无OCR)"
echo "3) 完整安装 (支持所有功能)"
read -p "请输入选项 (1-3): " INSTALL_MODE

# 检查Python版本
echo ""
echo "检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ $(echo "$PYTHON_VERSION >= 3.11" | bc) -ne 1 ]]; then
    echo "❌ Python版本需要 3.11+，当前版本: $PYTHON_VERSION"
    exit 1
fi
echo "✅ Python版本: $PYTHON_VERSION"

# 安装uv包管理器
echo ""
echo "安装uv包管理器..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi
echo "✅ uv已安装"

# 创建虚拟环境
echo ""
echo "创建Python虚拟环境..."
uv venv
echo "✅ 虚拟环境创建完成"

# 根据安装模式安装依赖
echo ""
echo "安装Python依赖..."

case $INSTALL_MODE in
    1)
        echo "安装最小依赖集..."
        cat > requirements-minimal.txt << EOF
fastmcp>=2.8.0
pydantic>=2.11.4
diskcache>=5.6.3
pymupdf4llm>=0.0.24
EOF
        uv pip install -r requirements-minimal.txt
        ;;
    2)
        echo "安装标准依赖集..."
        cat > requirements-standard.txt << EOF
fastmcp>=2.8.0
pydantic>=2.11.4
diskcache>=5.6.3
pymupdf4llm>=0.0.24
python-pptx>=1.0.2
openpyxl>=3.1.5
tabulate>=0.9.0
odfpy>=1.4.1
EOF
        uv pip install -r requirements-standard.txt
        ;;
    3)
        echo "安装完整依赖集..."
        uv pip install -r requirements.txt
        
        # 安装外部工具提示
        echo ""
        echo "⚠️  完整功能需要额外安装："
        if [[ "$OS_TYPE" == "macos" ]]; then
            echo "  - LibreOffice: brew install --cask libreoffice"
            echo "  - Pandoc: brew install pandoc"
        else
            echo "  - LibreOffice: sudo apt-get install libreoffice"
            echo "  - Pandoc: sudo apt-get install pandoc"
        fi
        ;;
esac

echo "✅ 依赖安装完成"

# 创建默认配置文件
echo ""
echo "创建配置文件..."
if [ ! -f .env ]; then
    cat > .env << EOF
# 基础配置
CACHE_ROOT_DIR=cache
CACHE_EXPIRE_DAYS=30
LOG_LEVEL=INFO

# 资源限制（优化后的默认值）
TOTAL_CACHE_SIZE_MB=500
FILE_READER_MAX_FILE_SIZE_MB=20

# 本地文件访问
LOCAL_FILE_ALLOWED_DIRECTORIES=$HOME

# OCR配置（可选）
# LLM_VISION_BASE_URL=https://xxx
# LLM_VISION_API_KEY=sk-xxx
# LLM_VISION_MODEL=qwen-vl-plus
EOF
    echo "✅ 配置文件 .env 已创建"
else
    echo "⚠️  配置文件 .env 已存在，跳过创建"
fi

# 创建缓存目录
echo ""
echo "创建缓存目录..."
mkdir -p cache/parsed_content
mkdir -p cache/document_images
mkdir -p cache/archive_files
echo "✅ 缓存目录创建完成"

# 测试安装
echo ""
echo "测试安装..."
source .venv/bin/activate
python -c "from src.mcp_server import mcp; print('✅ MCP服务器导入成功')"

echo ""
echo "========================================="
echo "🎉 安装完成！"
echo "========================================="
echo ""
echo "启动服务器："
echo "  source .venv/bin/activate"
echo "  uv run python run_mcp_server.py"
echo ""
echo "配置Claude Desktop："
echo "  编辑 ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "  添加MCP服务器配置"
echo ""