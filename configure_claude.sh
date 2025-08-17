#!/bin/bash
# Claude Desktop MCP 配置脚本

set -e

echo "========================================="
echo "Claude Desktop MCP 配置向导"
echo "========================================="
echo ""

# 检测操作系统
CONFIG_PATH=""
if [[ "$OSTYPE" == "darwin"* ]]; then
    CONFIG_PATH="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    CONFIG_PATH="$HOME/.config/Claude/claude_desktop_config.json"
else
    echo "❌ 不支持的操作系统: $OSTYPE"
    exit 1
fi

echo "📍 配置文件路径: $CONFIG_PATH"

# 获取当前目录的绝对路径
CURRENT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "📂 MCP服务器路径: $CURRENT_DIR"

# 检查虚拟环境是否存在
if [ ! -d "$CURRENT_DIR/.venv" ]; then
    echo "⚠️  未检测到虚拟环境，请先运行 ./install.sh 安装"
    exit 1
fi

# 获取用户主目录
USER_HOME="$HOME"

# 询问允许访问的目录
echo ""
echo "配置文件访问权限"
echo "默认允许访问: $USER_HOME"
read -p "是否需要添加其他目录？(y/n): " ADD_DIRS

ALLOWED_DIRS="$USER_HOME"
if [ "$ADD_DIRS" = "y" ] || [ "$ADD_DIRS" = "Y" ]; then
    echo "请输入要允许访问的目录路径（多个目录用逗号分隔）："
    read EXTRA_DIRS
    if [ ! -z "$EXTRA_DIRS" ]; then
        ALLOWED_DIRS="$USER_HOME,$EXTRA_DIRS"
    fi
fi

# 构建MCP配置
MCP_CONFIG=$(cat <<EOF
{
  "mcpServers": {
    "mcp-local-reader": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "$CURRENT_DIR/mcp_server.py"
      ],
      "env": {
        "CACHE_ROOT_DIR": "$CURRENT_DIR/cache",
        "CACHE_EXPIRE_DAYS": "30",
        "TOTAL_CACHE_SIZE_MB": "500",
        "LOCAL_FILE_ALLOWED_DIRECTORIES": "$ALLOWED_DIRS",
        "FILE_READER_MAX_FILE_SIZE_MB": "20",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
EOF
)

# 检查配置文件是否存在
if [ -f "$CONFIG_PATH" ]; then
    echo ""
    echo "⚠️  配置文件已存在"
    echo "请选择操作："
    echo "1) 备份并覆盖"
    echo "2) 合并配置（需要 jq）"
    echo "3) 显示配置供手动添加"
    read -p "请输入选项 (1-3): " ACTION
    
    case $ACTION in
        1)
            # 备份并覆盖
            BACKUP_FILE="${CONFIG_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
            cp "$CONFIG_PATH" "$BACKUP_FILE"
            echo "✅ 已备份到: $BACKUP_FILE"
            echo "$MCP_CONFIG" > "$CONFIG_PATH"
            echo "✅ 配置已覆盖"
            ;;
        2)
            # 合并配置
            if ! command -v jq &> /dev/null; then
                echo "❌ 需要安装 jq 工具来合并配置"
                echo "  macOS: brew install jq"
                echo "  Linux: sudo apt-get install jq"
                exit 1
            fi
            
            # 备份原配置
            BACKUP_FILE="${CONFIG_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
            cp "$CONFIG_PATH" "$BACKUP_FILE"
            echo "✅ 已备份到: $BACKUP_FILE"
            
            # 合并配置
            EXISTING_CONFIG=$(cat "$CONFIG_PATH")
            MERGED_CONFIG=$(echo "$EXISTING_CONFIG" | jq --argjson new "$MCP_CONFIG" '.mcpServers["mcp-local-reader"] = $new.mcpServers["mcp-local-reader"]')
            echo "$MERGED_CONFIG" > "$CONFIG_PATH"
            echo "✅ 配置已合并"
            ;;
        3)
            # 显示配置
            echo ""
            echo "请将以下配置添加到 $CONFIG_PATH 的 mcpServers 部分："
            echo ""
            echo "----------------------------------------"
            if command -v jq &> /dev/null; then
                echo "$MCP_CONFIG" | jq '.mcpServers["mcp-local-reader"]'
            else
                echo "$MCP_CONFIG"
            fi
            echo "----------------------------------------"
            echo ""
            echo "按任意键继续..."
            read -n 1
            ;;
        *)
            echo "❌ 无效的选项"
            exit 1
            ;;
    esac
else
    # 创建新配置文件
    mkdir -p "$(dirname "$CONFIG_PATH")"
    echo "$MCP_CONFIG" > "$CONFIG_PATH"
    echo "✅ 配置文件已创建"
fi

# 创建测试文件（可选）
echo ""
read -p "是否创建测试文件用于验证？(y/n): " CREATE_TEST

if [ "$CREATE_TEST" = "y" ] || [ "$CREATE_TEST" = "Y" ]; then
    TEST_FILE="$HOME/mcp_test.txt"
    cat > "$TEST_FILE" << EOF
这是一个 MCP 测试文件
用于验证 MCP-LOCAL-Reader 是否正常工作

测试内容：
1. 文本读取功能
2. 文件路径验证
3. Claude Desktop 集成

如果你能在 Claude 中看到这些内容，说明配置成功！
EOF
    echo "✅ 测试文件已创建: $TEST_FILE"
fi

echo ""
echo "========================================="
echo "🎉 配置完成！"
echo "========================================="
echo ""
echo "后续步骤："
echo "1. 重启 Claude Desktop 应用"
echo "2. 在 Claude 中测试："

if [ "$CREATE_TEST" = "y" ] || [ "$CREATE_TEST" = "Y" ]; then
    echo "   输入: 使用 read_local_file 工具读取 $HOME/mcp_test.txt"
else
    echo "   输入: 使用 read_local_file 工具读取 [你的文件路径]"
fi

echo ""
echo "手动测试服务器："
echo "  cd $CURRENT_DIR"
echo "  source .venv/bin/activate"
echo "  uv run python mcp_server.py"
echo ""