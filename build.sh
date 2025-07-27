#!/bin/bash

# 构建MCP文件读取器Docker镜像
set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}开始构建 MCP 文件读取器 Docker 镜像...${NC}"

# 从 pyproject.toml 获取版本和项目名称信息
VERSION=$(grep -o 'version = "[^"]*"' pyproject.toml | cut -d'"' -f2 || echo "latest")
IMAGE_NAME=$(grep -o 'name = "[^"]*"' pyproject.toml | head -1 | cut -d'"' -f2 || echo "mcp-file-reader")

echo -e "${YELLOW}构建版本: ${VERSION}${NC}"
echo -e "${YELLOW}构建平台: linux/amd64${NC}"

# 构建镜像（只构建特定版本号）
echo -e "${YELLOW}构建中...${NC}"
docker build \
    --platform linux/amd64 \
    --tag ${IMAGE_NAME}:${VERSION} \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 构建成功！${NC}"
    
    # 显示镜像信息
    echo -e "${YELLOW}镜像信息:${NC}"
    docker images ${IMAGE_NAME}:${VERSION} --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    
    echo -e "${YELLOW}运行示例:${NC}"
    echo -e "  docker run -p 3001:3001 --env-file .env ${IMAGE_NAME}:${VERSION}"
    
else
    echo -e "${RED}❌ 构建失败！${NC}"
    exit 1
fi 