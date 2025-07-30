#!/usr/bin/env python3
"""
MCP文件读取器 - HTTP传输模式服务器  
使用Streamable HTTP协议，适用于远程调用和Web集成
"""

import os
import sys
import tomllib
from pathlib import Path
from typing import List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import Server
from mcp.server.streamable_http import streamable_http_server
from mcp.types import Tool, TextContent

from src.file_reader import FileReader, ReadResponse, FailureType, LocalReadRequest, LocalFileStorageClient
from src.file_reader.utils import get_logger

def get_version_from_pyproject() -> str:
    """从 pyproject.toml 文件读取版本号"""
    try:
        current_dir = Path(__file__).parent
        project_root = current_dir.parent
        pyproject_path = project_root / "pyproject.toml"
        
        if not pyproject_path.exists():
            return "unknown"
        
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
        
        version = pyproject_data.get("project", {}).get("version")
        return version if version else "unknown"
        
    except Exception:
        return "unknown"

# 获取版本号
version = get_version_from_pyproject()

# 服务器配置
SERVER_NAME = "local-file-reader"
SERVER_VERSION = version
SERVER_CONFIG = {
    "host": "0.0.0.0", 
    "port": 3001,
    "base_path": "/mcp"
}

# 设置日志
logger = get_logger("mcp.http_server")

# 全局文件读取器实例
local_file_reader = None

def get_local_file_reader() -> FileReader:
    """获取本地文件读取器实例（单例模式）"""
    global local_file_reader
    if local_file_reader is None:
        # 从环境变量读取配置
        min_content_length = int(os.getenv("FILE_READER_MIN_CONTENT_LENGTH", "10"))
        
        # 本地文件存储客户端配置
        allowed_directories = os.getenv("LOCAL_FILE_ALLOWED_DIRECTORIES", "").split(",") if os.getenv("LOCAL_FILE_ALLOWED_DIRECTORIES") else None
        allow_absolute_paths = os.getenv("LOCAL_FILE_ALLOW_ABSOLUTE_PATHS", "false").lower() == "true"
        
        # 如果没有指定允许的目录，默认使用当前工作目录
        if not allowed_directories or allowed_directories == [""]:
            allowed_directories = [os.getcwd()]
        else:
            # 过滤空字符串
            allowed_directories = [d.strip() for d in allowed_directories if d.strip()]
        
        # 创建本地文件存储客户端
        local_storage_client = LocalFileStorageClient(
            allowed_directories=allowed_directories,
            allow_absolute_paths=allow_absolute_paths
        )
        
        local_file_reader = FileReader(
            storage_client=local_storage_client,
            min_content_length=min_content_length
        )
        logger.info("本地文件读取器实例已创建")
    return local_file_reader

# 创建标准MCP服务器实例
app = Server(SERVER_NAME)

@app.list_tools()
async def list_tools() -> List[Tool]:
    """列出可用的工具"""
    return [
        Tool(
            name="read_local_files",
            description="读取本地文件系统中的PDF、Office文档",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "本地文件绝对路径数组，必须使用完整的绝对路径(如/Users/user/document.pdf)。支持格式：PDF、Office文档(doc/docx/xls/xlsx/ppt/pptx)、OpenDocument(odt/ods/odp)。不支持图片"
                    },
                    "max_size": {
                        "type": "integer", 
                        "description": "单个文件大小限制(MB)，默认20MB",
                        "default": 20
                    }
                },
                "required": ["file_paths"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """处理工具调用"""
    if name != "read_local_files":
        raise ValueError(f"未知工具: {name}")
    
    file_paths = arguments.get("file_paths", [])
    max_size = arguments.get("max_size", 20)
    
    logger.info(f"收到HTTP文件读取请求，包含 {len(file_paths)} 个文件路径")
    
    try:
        # URL解码所有文件路径
        import urllib.parse
        decoded_file_paths = []
        for file_path in file_paths:
            decoded_path = urllib.parse.unquote(file_path)
            decoded_file_paths.append(decoded_path)
            if decoded_path != file_path:
                logger.debug(f"URL解码路径: {file_path} -> {decoded_path}")
        
        file_paths = decoded_file_paths
        
        # 检查文件数量限制
        max_files_per_request = int(os.getenv("FILE_READER_MAX_FILES_PER_REQUEST", "10"))
        if len(file_paths) > max_files_per_request:
            logger.error(f"请求文件数量超限: {len(file_paths)} > {max_files_per_request}")
            error_response = ReadResponse()
            for file_path in file_paths:
                error_response.add_failure(
                    file_path,
                    FailureType.OTHER,
                    f"请求文件数量超限: {len(file_paths)} > {max_files_per_request}，请分批处理"
                )
            return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]
        
        # 验证所有路径必须是绝对路径
        invalid_paths = []
        for file_path in file_paths:
            if not os.path.isabs(file_path):
                invalid_paths.append(file_path)
        
        if invalid_paths:
            logger.error(f"检测到相对路径，仅支持绝对路径: {invalid_paths}")
            error_response = ReadResponse()
            for file_path in invalid_paths:
                error_response.add_failure(
                    file_path,
                    FailureType.OTHER,
                    f"路径格式错误: 必须使用绝对路径(以/开头)，当前路径'{file_path}'为相对路径"
                )
            # 为其他有效的绝对路径也添加取消处理的错误
            for file_path in file_paths:
                if file_path not in invalid_paths:
                    error_response.add_failure(
                        file_path,
                        FailureType.OTHER,
                        "因批次中包含无效路径，整个请求被取消"
                    )
            return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]
        
        # 创建本地文件读取请求
        kwargs = {
            "file_paths": file_paths,
            "allow_absolute_paths": True  # 强制使用绝对路径
        }
        if max_size is not None:
            kwargs["max_size"] = max_size * 1024 * 1024  # 转换MB为字节数
        
        request = LocalReadRequest(**kwargs)
        
        # 执行文件读取
        reader_instance = get_local_file_reader()
        response = await reader_instance.read_files(request)
        
        logger.info(f"HTTP文件读取完成 - 成功: {len(response.contents)}, 失败: {len(response.failed)}")
        
        # 返回结果，使用JSON格式
        return [TextContent(type="text", text=response.model_dump_json(indent=2))]
        
    except Exception as e:
        logger.error(f"HTTP文件读取处理失败: {str(e)}")
        
        # 创建标准的错误响应格式
        error_response = ReadResponse()
        
        # 为所有请求的文件路径添加失败记录
        for file_path in file_paths:
            error_response.add_failure(
                file_path,
                FailureType.OTHER,
                f"请求处理异常: {str(e)}"
            )
        
        return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]

def run_http_server():
    """运行HTTP模式的MCP服务器"""
    host = SERVER_CONFIG["host"]
    port = SERVER_CONFIG["port"] 
    base_path = SERVER_CONFIG["base_path"]
    
    logger.info(f"启动MCP文件读取器 HTTP 服务器 - 版本: {SERVER_VERSION}")
    logger.info(f"HTTP服务器地址: {host}:{port}{base_path}")
    logger.info("使用Streamable HTTP传输，适用于远程调用和Web集成")
    
    try:
        # 使用streamable HTTP传输启动服务器
        import uvicorn
        from mcp.server.streamable_http import create_streamable_http_app
        
        # 创建streamable HTTP应用
        http_app = create_streamable_http_app(app, base_path)
        
        # 启动服务器
        uvicorn.run(
            http_app,
            host=host,
            port=port,
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"启动HTTP服务器失败: {str(e)}")
        raise
    finally:
        # 清理资源
        global local_file_reader
        if local_file_reader:
            local_file_reader = None

if __name__ == "__main__":
    run_http_server()