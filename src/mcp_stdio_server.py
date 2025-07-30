#!/usr/bin/env python3
"""
MCP文件读取器 - stdio传输模式服务器
使用标准MCP协议通过stdin/stdout通信，适用于本地集成和嵌入式部署
"""

import os
import sys
import asyncio
import json
from typing import List, Optional, Annotated
from pathlib import Path

# 添加项目根目录到Python路径，确保可以导入模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.file_reader import FileReader, ReadResponse, FailureType, LocalReadRequest, LocalFileStorageClient
from src.file_reader.utils import get_logger

# 设置日志 - stdio模式下日志输出到stderr，避免干扰stdin/stdout通信
logger = get_logger("mcp.stdio_server")

# 服务器信息
SERVER_NAME = "local-file-reader"
SERVER_VERSION = "1.1.0"

# 全局文件读取器实例
local_file_reader = None

def get_local_file_reader() -> FileReader:
    """获取本地文件读取器实例（单例模式）"""
    global local_file_reader
    if local_file_reader is None:
        # 从环境变量读取配置
        max_workers = int(os.getenv("FILE_READER_MAX_WORKERS", "5"))
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
            max_workers=max_workers,
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
            description="读取本地文件系统中的文件内容，支持PDF、Office文档、图像OCR等多种格式",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "本地文件绝对路径数组，必须使用完整的绝对路径(如/Users/user/document.pdf)。支持格式：PDF、Office文档(doc/docx/xls/xlsx/ppt/pptx)、OpenDocument(odt/ods/odp)、图像文件(png/jpg/gif等)"
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
    
    logger.info(f"收到stdio文件读取请求，包含 {len(file_paths)} 个文件路径")
    
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
        
        logger.info(f"stdio文件读取完成 - 成功: {len(response.contents)}, 失败: {len(response.failed)}")
        
        # 返回结果，使用JSON格式
        return [TextContent(type="text", text=response.model_dump_json(indent=2))]
        
    except Exception as e:
        logger.error(f"stdio文件读取处理失败: {str(e)}")
        
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

async def main():
    """启动stdio模式的MCP服务器"""
    # stdio模式下不能向stdout输出日志，会干扰MCP通信
    # 所有日志都通过logger输出到文件或stderr
    logger.info(f"启动MCP文件读取器 stdio 服务器 - 版本: {SERVER_VERSION}")
    logger.info("使用stdio传输，适用于本地集成和嵌入式部署")
    
    # 使用stdio传输启动服务器
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream, 
            write_stream, 
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())