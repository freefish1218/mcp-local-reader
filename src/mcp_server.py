"""
MCP文件读取器服务器实现
提供文件内容读取功能的MCP服务器
"""

import os
import tomllib
from pathlib import Path
from typing import List, Dict, Optional, Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, ToolAnnotations

from file_reader import FileReader, ReadRequest, ReadResponse, FailureType, LocalReadRequest, LocalFileStorageClient, UrlWithReferer
from file_reader.storage import HTTPDownloadStorageClient
from file_reader.utils import get_logger
from pydantic import Field


def detect_docker_environment() -> bool:
    """
    检测是否在Docker容器中运行
    
    Returns:
        bool: True表示在Docker容器中运行，False表示在原生环境中
    """
    # 方法1: 检查/.dockerenv文件
    if Path("/.dockerenv").exists():
        return True
    
    # 方法2: 检查cgroup信息
    try:
        with open("/proc/1/cgroup", "r") as f:
            content = f.read()
            if "docker" in content or "containerd" in content:
                return True
    except (FileNotFoundError, PermissionError):
        pass
    
    # 方法3: 检查环境变量
    if os.getenv("DOCKER_CONTAINER") == "true":
        return True
    
    return False


# 全局环境检测
IS_DOCKER_ENV = detect_docker_environment()


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
    "name": "MCPFileReaderServer",
    "version": version,
    "description": "专业的文件内容读取服务，支持通过HTTP下载链接获取和解析文件",
    "features": ["HTTP下载", "PDF解析", "Office文档", "图像OCR", "文本提取", "批量处理"],
    "instructions": f"这个服务器提供专业的文件内容读取功能，支持通过HTTP链接下载PDF、Office文档、图像OCR等多种格式的文本提取。当前版本: {version}"
}

# 服务器配置
SERVER_CONFIG = {
    "host": "0.0.0.0",
    "port": 3001,
    "base_path": "/mcp"
}

# 设置日志
logger = get_logger("mcp.file_reader.server")

# 记录版本和环境信息
logger.info(f"MCP文件读取器服务器初始化 - 版本: {SERVER_INFO['version']}")
logger.info(f"运行环境检测: {'Docker容器' if IS_DOCKER_ENV else '原生Python'}")
if IS_DOCKER_ENV:
    logger.info("检测到Docker环境，将提供文件上传功能而非本地文件读取")
else:
    logger.info("检测到原生环境，将提供本地文件读取功能")

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
file_reader = None
local_file_reader = None


def get_file_reader() -> FileReader:
    """获取文件读取器实例（HTTP下载模式）"""
    global file_reader
    if file_reader is None:
        # 从环境变量读取配置
        max_workers = int(os.getenv("FILE_READER_MAX_WORKERS", "5"))
        min_content_length = int(os.getenv("FILE_READER_MIN_CONTENT_LENGTH", "10"))
        download_service_url = os.getenv("DOWNLOAD_SERVICE_URL", "http://localhost:8080")
        download_service_timeout = int(os.getenv("DOWNLOAD_SERVICE_TIMEOUT", "300"))
        
        # 创建HTTP下载存储客户端
        http_storage_client = HTTPDownloadStorageClient(
            download_service_url=download_service_url,
            timeout=download_service_timeout
        )
        
        file_reader = FileReader(
            storage_client=http_storage_client,
            max_workers=max_workers,
            min_content_length=min_content_length
        )
        logger.info("HTTP下载文件读取器实例已创建")
    return file_reader


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


@mcp.tool(
    description="读取文件内容，支持通过HTTP/HTTPS URL和file:///格式下载PDF、Office文档、图像OCR等多种格式",
    annotations=ToolAnnotations(
        title="文件内容读取工具",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
        category="file_reader",
    )
)
async def read_files(
    urls: Annotated[List[UrlWithReferer], "文件下载链接数组，支持HTTP/HTTPS URL和file:///格式，每个链接可以指定专属的Referer"],
    max_size: Annotated[Optional[int], "单个文件大小限制(MB)，为空时默认值为20MB"] = 20,
    use_proxy: Annotated[bool, "是否使用代理下载文件"] = False,
    max_retries: Annotated[int, "最大重试次数"] = 3,
    max_workers: Annotated[int, "最大并发工作线程数"] = 5
) -> List[TextContent]:
    """
    读取文件内容（通过URL下载或file:///格式）
    
    Args:
        urls: 文件下载链接数组，支持HTTP/HTTPS URL和file:///格式，每个链接可以指定专属的Referer
        max_size: 文件大小限制(MB)，为空时使用环境变量FILE_READER_MAX_FILE_SIZE_MB的默认值
        use_proxy: 是否使用代理
        max_retries: 最大重试次数
        max_workers: 最大并发工作线程数
    
    Returns:
        包含读取结果的JSON字符串
    """
    logger.info(f"收到文件内容读取请求，包含 {len(urls)} 个下载链接")
    
    try:
        # 检查文件数量限制
        max_files_per_request = int(os.getenv("FILE_READER_MAX_FILES_PER_REQUEST", "10"))
        if len(urls) > max_files_per_request:
            logger.error(f"请求文件数量超限: {len(urls)} > {max_files_per_request}")
            error_response = ReadResponse()
            for url_item in urls:
                error_response.add_failure(
                    url_item.url,
                    FailureType.OTHER,
                    f"请求文件数量超限: {len(urls)} > {max_files_per_request}，请分批处理"
                )
            return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]
        
        # 提取URL列表和构建referer映射
        url_list = [url_item.url for url_item in urls]
        referer_map = {}
        for url_item in urls:
            if url_item.referer:
                referer_map[url_item.url] = url_item.referer
        
        # 创建读取请求，如果传入了max_size则转换为字节数
        kwargs = {
            "resource_ids": url_list,
            "referer_map": referer_map if referer_map else None,
            "use_proxy": use_proxy,
            "max_retries": max_retries,
            "max_workers": max_workers
        }
        if max_size is not None:
            kwargs["max_size"] = max_size * 1024 * 1024  # 转换MB为字节数
        
        request = ReadRequest(**kwargs)
        
        # 执行文件读取
        reader_instance = get_file_reader()
        response = await reader_instance.read_files(request)
        
        logger.info(f"文件读取完成 - 成功: {len(response.contents)}, 失败: {len(response.failed)}")
        
        # 返回结果，使用JSON格式
        return [TextContent(type="text", text=response.model_dump_json(indent=2))]
        
    except Exception as e:
        logger.error(f"文件读取处理失败: {str(e)}")
        
        # 创建标准的错误响应格式，与正常响应保持一致
        error_response = ReadResponse()
        
        # 为所有请求的URL添加失败记录
        for url_item in urls:
            error_response.add_failure(
                url_item.url,
                FailureType.OTHER,
                f"请求处理异常: {str(e)}"
            )
        
        return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]


# 条件性注册本地文件读取工具（仅在非Docker环境下）
# 说明中去掉图像OCR、文本提取, 这些用 cursor/vscode 自身能力
if not IS_DOCKER_ENV:
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
    async def read_local_files(
        file_paths: Annotated[List[str], "本地文件绝对路径数组，必须使用完整的绝对路径(如/Users/user/document.pdf)。支持格式：PDF、Office文档(doc/docx/xls/xlsx/ppt/pptx)、OpenDocument(odt/ods/odp)。不支持图片"],
        max_size: Annotated[Optional[int], "单个文件大小限制(MB)"] = 20,
    ) -> List[TextContent]:
        """
        读取本地文件系统中的文件内容（仅支持绝对路径）
        
        Args:
            file_paths: 本地文件绝对路径数组（必须使用绝对路径，如/Users/user/file.pdf）
            max_size: 文件大小限制(MB)，为空时使用环境变量FILE_READER_MAX_FILE_SIZE_MB的默认值
        
        Returns:
            包含读取结果的JSON字符串
        """
        logger.info(f"收到本地文件内容读取请求，包含 {len(file_paths)} 个文件路径")

        try:
            # URL解码所有文件路径（解决Agent传入URL编码路径的问题）
            import urllib.parse
            decoded_file_paths = []
            for file_path in file_paths:
                decoded_path = urllib.parse.unquote(file_path)
                decoded_file_paths.append(decoded_path)
                if decoded_path != file_path:
                    logger.debug(f"URL解码路径: {file_path} -> {decoded_path}")
            
            # 使用解码后的路径继续处理
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
            
            # 创建本地文件读取请求，如果传入了max_size则转换为字节数
            # 所有路径已验证为绝对路径，强制启用绝对路径支持
            kwargs = {
                "file_paths": file_paths,
                "allow_absolute_paths": True  # 强制使用绝对路径
            }
            if max_size is not None:
                kwargs["max_size"] = max_size * 1024 * 1024  # 转换MB为字节数
            
            request = LocalReadRequest(**kwargs)
            
            # 执行文件读取
            reader_instance = get_local_file_reader()
            
            # 需要将LocalReadRequest转换为FileReader可以处理的格式
            # 创建一个与读取器兼容的ReadRequest，使用file_paths作为resource_ids
            read_kwargs = {
                "resource_ids": request.file_paths
            }
            if hasattr(request, 'max_size'):
                read_kwargs["max_size"] = request.max_size
            
            compatible_request = ReadRequest(**read_kwargs)
            
            response = await reader_instance.read_files(compatible_request)
            
            logger.info(f"本地文件读取完成 - 成功: {len(response.contents)}, 失败: {len(response.failed)}")
            
            # 返回结果，使用JSON格式
            return [TextContent(type="text", text=response.model_dump_json(indent=2))]
            
        except Exception as e:
            logger.error(f"本地文件读取处理失败: {str(e)}")
            
            # 创建标准的错误响应格式，与正常响应保持一致
            error_response = ReadResponse()
            
            # 为所有请求的文件路径添加失败记录
            for file_path in file_paths:
                error_response.add_failure(
                    file_path,
                    FailureType.OTHER,
                    f"请求处理异常: {str(e)}"
                )
            
            return [TextContent(type="text", text=error_response.model_dump_json(indent=2))]


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
        global file_reader, local_file_reader
        if file_reader:
            # FileReader没有close方法，这里重置为None
            file_reader = None
        if local_file_reader:
            # LocalFileReader没有close方法，这里重置为None
            local_file_reader = None 