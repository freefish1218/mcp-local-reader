#!/bin/bash
# 用于本地运行 docker 镜像, 方便调试

# 从 pyproject.toml 获取版本和项目名称信息
VERSION=$(grep -o 'version = "[^"]*"' pyproject.toml | cut -d'"' -f2 || echo "latest")
IMAGE_NAME=$(grep -o 'name = "[^"]*"' pyproject.toml | head -1 | cut -d'"' -f2 || echo "mcp-file-reader")

# 使用 mcp_mcp 网络, 覆盖环境变量中的配置中心地址和下载服务地址
docker run --platform linux/amd64 -d -p 3004:3001 \
    --name ${IMAGE_NAME} \
    --env-file .env \
    --network mcp_mcp \
    -e CONFIG_URL_BASE=http://mcp-config-center-1:3000 \
    -e DOWNLOAD_SERVICE_URL=http://storage-server:8082 \
    ${IMAGE_NAME}:${VERSION}
