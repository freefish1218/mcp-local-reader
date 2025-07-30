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

from src.file_reader import FileReader, LocalReadRequest, LocalFileStorageClient
from src.file_reader.utils import get_logger

# 设置日志 - stdio模式下日志输出到stderr，避免干扰stdin/stdout通信
logger = get_logger("mcp.stdio_server")

# 服务器信息
SERVER_NAME = "local-file-reader"
SERVER_VERSION = "1.1.0"

# 记录服务器初始化开始
logger.info(f"初始化MCP文件读取器 stdio 服务器 - 版本: {SERVER_VERSION}")
logger.info("使用stdio传输，适用于本地集成和嵌入式部署")

# 全局文件读取器实例
local_file_reader = None

def get_local_file_reader() -> FileReader:
    """获取本地文件读取器实例（单例模式）"""
    global local_file_reader
    if local_file_reader is None:
        # 从环境变量读取配置
        min_content_length = int(os.getenv("FILE_READER_MIN_CONTENT_LENGTH", "1"))
        
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
logger.info(f"创建MCP服务器实例: {SERVER_NAME}")
app = Server(SERVER_NAME)

@app.list_tools()
async def list_tools() -> List[Tool]:
    """列出可用的工具"""
    return [
        Tool(
            name="read_local_file",
            description="读取本地文件系统中的PDF、Office文档",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "本地文件绝对路径，必须使用完整的绝对路径(如/Users/user/document.pdf)。支持格式：PDF、Office文档(doc/docx/xls/xlsx/ppt/pptx)、OpenDocument(odt/ods/odp)。不支持图片"
                    },
                    "max_size": {
                        "type": "integer",
                        "description": "单个文件大小限制(MB)，默认20MB",
                        "default": 20
                    }
                },
                "required": ["file_path"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """处理工具调用"""
    if name != "read_local_file":
        raise ValueError(f"未知工具: {name}")
    
    file_path = arguments.get("file_path", "")
    max_size = arguments.get("max_size", 20)
    
    logger.info(f"收到stdio文件读取请求: {file_path}")
    
    try:
        # URL解码文件路径
        import urllib.parse
        decoded_path = urllib.parse.unquote(file_path)
        if decoded_path != file_path:
            logger.debug(f"URL解码路径: {file_path} -> {decoded_path}")
        file_path = decoded_path
        
        # 验证路径必须是绝对路径
        if not os.path.isabs(file_path):
            error_msg = f"路径格式错误: 必须使用绝对路径(以/开头)，当前路径'{file_path}'为相对路径"
            logger.error(error_msg)
            return [TextContent(type="text", text=f"错误: {error_msg}")]
        
        # 创建本地文件读取请求
        kwargs = {
            "file_paths": [file_path],  # 转换为数组格式
            "allow_absolute_paths": True  # 强制使用绝对路径
        }
        if max_size is not None:
            kwargs["max_size"] = max_size * 1024 * 1024  # 转换MB为字节数
        
        request = LocalReadRequest(**kwargs)
        
        # 执行文件读取
        reader_instance = get_local_file_reader()
        response = await reader_instance.read_files(request)
        
        # 检查读取结果
        if response.contents and len(response.contents) > 0:
            # 成功读取，直接返回文件内容
            content = response.contents[0].content
            logger.info(f"文件读取成功: {file_path}, 内容长度: {len(content)} 字符")
            return [TextContent(type="text", text=content)]
        elif response.failed and len(response.failed) > 0:
            # 读取失败，返回错误信息
            failed_file = response.failed[0]
            error_msg = f"文件读取失败: {failed_file.type.value} - {failed_file.error_message}"
            logger.error(error_msg)
            return [TextContent(type="text", text=f"错误: {error_msg}")]
        else:
            # 异常情况：既没有内容也没有失败记录
            error_msg = "文件读取异常：未返回内容或错误信息"
            logger.error(error_msg)
            return [TextContent(type="text", text=f"错误: {error_msg}")]
        
    except Exception as e:
        error_msg = f"文件读取处理异常: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"错误: {error_msg}")]

async def main():
    """启动stdio模式的MCP服务器"""
    # stdio模式下不能向stdout输出日志，会干扰MCP通信
    # 所有日志都通过logger输出到文件或stderr
    logger.info("开始启动stdio传输层...")
    
    try:
        # 使用stdio传输启动服务器
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream, 
                write_stream, 
                app.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"MCP服务器运行异常: {e}")
        import traceback
        logger.error(f"异常详情: {traceback.format_exc()}")
        
        # 检查是否是因为客户端提前关闭连接导致的异常
        if "ClosedResourceError" in str(e) or "unhandled errors in a TaskGroup" in str(e):
            logger.info("检测到客户端连接关闭，服务器正常退出")
            # 不重新抛出异常，让服务器正常退出
        else:
            # 其他异常继续抛出
            raise

if __name__ == "__main__":
    asyncio.run(main())