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
        ),
        Tool(
            name="convert_local_file",
            description="将本地文件转换为markdown文件并保存到文件系统",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "本地文件绝对路径，必须使用完整的绝对路径(如/Users/user/document.pdf)。支持格式：PDF、Office文档(doc/docx/xls/xlsx/ppt/pptx)、OpenDocument(odt/ods/odp)。不支持图片"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出markdown文件路径，默认为原文件名+.md",
                        "default": None
                    },
                    "max_size": {
                        "type": "integer",
                        "description": "单个文件大小限制(MB)，默认20MB",
                        "default": 20
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "是否覆盖已存在的文件",
                        "default": False
                    }
                },
                "required": ["file_path"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """处理工具调用"""
    if name == "read_local_file":
        return await handle_read_local_file(arguments)
    elif name == "convert_local_file":
        return await handle_convert_local_file(arguments)
    else:
        raise ValueError(f"未知工具: {name}")

async def handle_read_local_file(arguments: dict) -> List[TextContent]:
    """处理读取文件请求"""
    file_path = arguments.get("file_path", "")
    max_size = arguments.get("max_size", 20)
    
    logger.info(f"收到HTTP文件读取请求: {file_path}")
    
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
            response = ReadResponse()
            response.add_failure(file_path, FailureType.OTHER, error_msg)
            return [TextContent(type="text", text=response.model_dump_json(indent=2))]
        
        # 创建本地文件读取请求
        kwargs = {
            "file_paths": [file_path],
            "allow_absolute_paths": True  # 强制使用绝对路径
        }
        if max_size is not None:
            kwargs["max_size"] = max_size * 1024 * 1024  # 转换MB为字节数
        
        request = LocalReadRequest(**kwargs)
        
        # 执行文件读取
        reader_instance = get_local_file_reader()
        response = await reader_instance.read_file(request)
        
        logger.info(f"HTTP文件读取完成 - 成功: {len(response.contents)}, 失败: {len(response.failed)}")
        
        # 返回结果，使用JSON格式
        return [TextContent(type="text", text=response.model_dump_json(indent=2))]
        
    except Exception as e:
        logger.error(f"HTTP文件读取处理失败: {str(e)}")
        
        # 创建标准的错误响应格式
        error_response = ReadResponse()
        
        # 为所有请求的文件路径添加失败记录
        error_response.add_failure(
            file_path,
            FailureType.OTHER,
            f"请求处理异常: {str(e)}"
        )
        
        return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]

async def handle_convert_local_file(arguments: dict) -> List[TextContent]:
    """处理文件转换请求"""
    file_path = arguments.get("file_path", "")
    output_path = arguments.get("output_path")
    max_size = arguments.get("max_size", 20)
    overwrite = arguments.get("overwrite", False)
    
    logger.info(f"收到HTTP文件转换请求: {file_path}")
    
    try:
        # 1. 先使用现有逻辑读取文件内容
        import urllib.parse
        decoded_path = urllib.parse.unquote(file_path)
        if decoded_path != file_path:
            logger.debug(f"URL解码路径: {file_path} -> {decoded_path}")
        file_path = decoded_path
        
        # 验证路径必须是绝对路径
        if not os.path.isabs(file_path):
            error_msg = f"路径格式错误: 必须使用绝对路径(以/开头)，当前路径'{file_path}'为相对路径"
            logger.error(error_msg)
            error_response = ReadResponse()
            error_response.add_failure(file_path, FailureType.OTHER, error_msg)
            return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]
        
        # 创建读取请求
        kwargs = {
            "file_paths": [file_path],
            "allow_absolute_paths": True
        }
        if max_size is not None:
            kwargs["max_size"] = max_size * 1024 * 1024
        
        request = LocalReadRequest(**kwargs)
        reader_instance = get_local_file_reader()
        response = await reader_instance.read_file(request)
        
        # 检查读取结果
        if not response.contents:
            if response.failed:
                logger.error(f"文件读取失败: {response.failed[0].error_message}")
                return [TextContent(type="text", text=response.model_dump_json(indent=2))]
            else:
                error_msg = "文件读取异常：未返回内容或错误信息"
                logger.error(error_msg)
                error_response = ReadResponse()
                error_response.add_failure(file_path, FailureType.OTHER, error_msg)
                return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]
        
        markdown_content = response.contents[0].content
        logger.info(f"文件读取成功: {file_path}, 内容长度: {len(markdown_content)} 字符")
        
        # 2. 确定输出路径
        if output_path is None:
            # 默认使用原文件名 + .md 扩展名
            from pathlib import Path
            input_path = Path(file_path)
            output_path = str(input_path.with_suffix('.md'))
        
        # 验证输出路径是绝对路径
        if not os.path.isabs(output_path):
            error_msg = f"输出路径必须是绝对路径: {output_path}"
            logger.error(error_msg)
            error_response = ReadResponse()
            error_response.add_failure(file_path, FailureType.OTHER, error_msg)
            return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]
        
        # 3. 检查文件是否已存在
        if os.path.exists(output_path) and not overwrite:
            error_msg = f"输出文件已存在: {output_path}，使用 overwrite=true 来覆盖"
            logger.warning(error_msg)
            error_response = ReadResponse()
            error_response.add_failure(file_path, FailureType.OTHER, error_msg)
            return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]
        
        # 4. 检查输出目录是否存在，不存在则创建
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"创建输出目录: {output_dir}")
            except Exception as e:
                error_msg = f"创建输出目录失败: {output_dir}, 错误: {e}"
                logger.error(error_msg)
                error_response = ReadResponse()
                error_response.add_failure(file_path, FailureType.OTHER, error_msg)
                return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]
        
        # 5. 写入markdown文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            success_msg = f"文件转换成功: {file_path} -> {output_path}"
            logger.info(success_msg)
            
            # 创建成功响应
            success_response = ReadResponse()
            success_response.add_content(file_path, success_msg)
            return [TextContent(type="text", text=success_response.model_dump_json(indent=2))]
            
        except Exception as e:
            error_msg = f"写入输出文件失败: {output_path}, 错误: {e}"
            logger.error(error_msg)
            error_response = ReadResponse()
            error_response.add_failure(file_path, FailureType.OTHER, error_msg)
            return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]
            
    except Exception as e:
        error_msg = f"文件转换处理异常: {str(e)}"
        logger.error(error_msg)
        error_response = ReadResponse()
        error_response.add_failure(file_path, FailureType.OTHER, error_msg)
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