"""
MCP文件读取器服务器实现
提供文件内容读取功能的MCP服务器
"""

import os
import tomllib
from pathlib import Path
from typing import List, Optional, Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, ToolAnnotations

from .file_reader import FileReader, LocalReadRequest, LocalFileStorageClient
from .file_reader.utils import get_logger


def get_version_from_pyproject() -> str:
    """
    从 pyproject.toml 文件读取版本号
    
    Returns:
        版本号字符串，读取失败时返回 "unknown"
    """
    try:
        # 获取项目根目录路径（假设 pyproject.toml 在项目根目录）
        current_dir = Path(__file__).parent
        project_root = current_dir.parent  # src 的上一级目录
        pyproject_path = project_root / "pyproject.toml"
        
        if not pyproject_path.exists():
            return "unknown"
        
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
        
        version = pyproject_data.get("project", {}).get("version")
        return version if version else "unknown"
        
    except (FileNotFoundError, tomllib.TOMLDecodeError, KeyError, OSError) as e:
        # 日志记录在实际运行时才会输出，这里先返回默认值
        return "unknown"
    except Exception:
        # 处理其他可能的异常
        return "unknown"


# 获取版本号
version = get_version_from_pyproject()

# 获取服务器信息
SERVER_INFO = {
    "name": "MCPLocalFileReaderServer",
    "version": version,
    "description": "本地文件内容读取服务，支持解析PDF、Office文档等多种格式",
    "features": ["PDF解析", "Office文档", "图像OCR", "文本提取"],
    "instructions": f"这个服务器提供本地文件内容读取功能，支持解析PDF、Office文档、图像OCR等多种格式。当前版本: {version}"
}

# 服务器配置
SERVER_CONFIG = {
    "host": "0.0.0.0",
    "port": 3001,
    "base_path": "/mcp"
}

# 设置日志
logger = get_logger("mcp.file_reader.server")

# 记录版本信息
logger.info(f"MCP本地文件读取器服务器初始化 - 版本: {SERVER_INFO['version']}")
logger.info("本地文件读取模式，只支持读取本地文件系统中的文件")

# 创建FastMCP实例，在服务器层面设置版本和描述信息
mcp = FastMCP(
    name=SERVER_INFO["name"],
    description=SERVER_INFO["instructions"],  # 在 description 中包含版本信息
    host=SERVER_CONFIG["host"],
    port=SERVER_CONFIG["port"], 
    base_path=SERVER_CONFIG["base_path"],
    json_response=False,  # 使用SSE流
    stateless_http=True,  # 无状态模式，适合生产部署
)

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
        
        # 如果没有指定允许的目录，默认使用当前工作目录
        if not allowed_directories or allowed_directories == [""]:
            allowed_directories = [os.getcwd()]
        else:
            # 过滤空字符串
            allowed_directories = [d.strip() for d in allowed_directories if d.strip()]
        
        # 创建本地文件存储客户端
        local_storage_client = LocalFileStorageClient(
            allowed_directories=allowed_directories
        )
        
        local_file_reader = FileReader(
            storage_client=local_storage_client,
            min_content_length=min_content_length
        )
        logger.info("本地文件读取器实例已创建")
    return local_file_reader


# 本地文件读取工具
@mcp.tool(
    description="读取本地文件系统中的PDF、Office文档（不支持图片）",
    annotations=ToolAnnotations(
        title="本地PDF、Office文档读取工具",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
        category="file_reader",
    )
)
async def read_local_file(
    file_path: Annotated[str, "本地文件绝对路径，必须使用完整的绝对路径(如/Users/user/document.pdf)。支持格式：PDF、Office文档(doc/docx/xls/xlsx/ppt/pptx)、OpenDocument(odt/ods/odp)。不支持图片"],
    max_size: Annotated[Optional[int], "单个文件大小限制(MB)"] = 20,
) -> List[TextContent]:
    """
    读取本地文件系统中的文件内容（仅支持绝对路径）

    Args:
        file_path: 本地文件绝对路径（必须使用绝对路径，如/Users/user/file.pdf）
        max_size: 文件大小限制(MB)，为空时使用环境变量FILE_READER_MAX_FILE_SIZE_MB的默认值

    Returns:
        文件内容字符串（markdown格式）
    """
    logger.info(f"收到本地文件内容读取请求: {file_path}")

    try:
        # URL解码文件路径（解决Agent传入URL编码路径的问题）
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

        # 创建本地文件读取请求，如果传入了max_size则转换为字节数
        kwargs = {
            "file_paths": [file_path]  # 转换为数组格式
        }
        if max_size is not None:
            kwargs["max_size"] = max_size * 1024 * 1024  # 转换MB为字节数

        request = LocalReadRequest(**kwargs)

        # 执行文件读取
        reader_instance = get_local_file_reader()
        response = await reader_instance.read_file(request)

        # 检查读取结果
        if response.contents:
            # 成功读取，直接返回文件内容
            content = response.contents[0].content
            logger.info(f"文件读取成功: {file_path}, 内容长度: {len(content)} 字符")
            return [TextContent(type="text", text=content)]
        elif response.failed:
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


# 本地文件转换工具
@mcp.tool(
    description="将本地文件转换为markdown文件并保存到文件系统",
    annotations=ToolAnnotations(
        title="本地文件转换工具",
        readOnlyHint=False,  # 会写入文件
        destructiveHint=False,
        idempotentHint=False,  # 每次执行可能产生不同结果
        openWorldHint=True,
        category="file_converter",
    )
)
async def convert_local_file(
    file_path: Annotated[str, "本地文件绝对路径，必须使用完整的绝对路径(如/Users/user/document.pdf)。支持格式：PDF、Office文档(doc/docx/xls/xlsx/ppt/pptx)、OpenDocument(odt/ods/odp)。不支持图片"],
    output_path: Annotated[Optional[str], "输出markdown文件路径，默认为原文件名+.md"] = None,
    max_size: Annotated[Optional[int], "单个文件大小限制(MB)"] = 20,
    overwrite: Annotated[bool, "是否覆盖已存在的文件"] = False,
) -> List[TextContent]:
    """
    将指定文件转换为markdown格式并保存到文件系统
    
    Args:
        file_path: 输入文件的绝对路径
        output_path: 输出文件路径，为空时使用原文件名+.md扩展名
        max_size: 文件大小限制(MB)
        overwrite: 是否覆盖已存在的文件
    
    Returns:
        转换操作结果信息
    """
    logger.info(f"收到文件转换请求: {file_path}")
    
    try:
        # 1. 先使用现有逻辑读取文件内容
        # 复用 read_local_file 的核心逻辑
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
        
        # 创建读取请求
        kwargs = {
            "file_paths": [file_path]
        }
        if max_size is not None:
            kwargs["max_size"] = max_size * 1024 * 1024
        
        request = LocalReadRequest(**kwargs)
        reader_instance = get_local_file_reader()
        response = await reader_instance.read_file(request)
        
        # 检查读取结果
        if not response.contents:
            if response.failed:
                failed_file = response.failed[0]
                error_msg = f"文件读取失败: {failed_file.type.value} - {failed_file.error_message}"
                logger.error(error_msg)
                return [TextContent(type="text", text=f"错误: {error_msg}")]
            else:
                error_msg = "文件读取异常：未返回内容或错误信息"
                logger.error(error_msg)
                return [TextContent(type="text", text=f"错误: {error_msg}")]
        
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
            return [TextContent(type="text", text=f"错误: {error_msg}")]
        
        # 3. 检查文件是否已存在
        if os.path.exists(output_path) and not overwrite:
            error_msg = f"输出文件已存在: {output_path}，使用 overwrite=true 来覆盖"
            logger.warning(error_msg)
            return [TextContent(type="text", text=f"错误: {error_msg}")]
        
        # 4. 检查输出目录是否存在，不存在则创建
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"创建输出目录: {output_dir}")
            except Exception as e:
                error_msg = f"创建输出目录失败: {output_dir}, 错误: {e}"
                logger.error(error_msg)
                return [TextContent(type="text", text=f"错误: {error_msg}")]
        
        # 5. 写入markdown文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            success_msg = f"文件转换成功: {file_path} -> {output_path}"
            logger.info(success_msg)
            return [TextContent(type="text", text=success_msg)]
            
        except Exception as e:
            error_msg = f"写入输出文件失败: {output_path}, 错误: {e}"
            logger.error(error_msg)
            return [TextContent(type="text", text=f"错误: {error_msg}")]
            
    except Exception as e:
        error_msg = f"文件转换处理异常: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"错误: {error_msg}")]


def run_server():
    """
    运行MCP服务器
    """
    # 获取配置或使用默认值
    host = SERVER_CONFIG.get("host")
    port = SERVER_CONFIG.get("port")
    base_path = SERVER_CONFIG.get("base_path")
    
    logger.info(f"启动MCP文件读取器服务器 - {SERVER_INFO['name']} - 地址: {host}:{port}{base_path}")
    
    try:
        # 使用 FastMCP 实例的 run 方法启动服务器
        mcp.run(transport="streamable-http")
        
    except Exception as e:
        logger.error(f"启动服务器失败: {str(e)}")
        raise
    finally:
        # 清理资源
        global local_file_reader
        if local_file_reader:
            # FileReader没有close方法，这里重置为None
            local_file_reader = None 