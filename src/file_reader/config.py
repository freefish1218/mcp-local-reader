"""
MCP-File-Reader 配置模块
提供配置信息的获取和缓存功能，以及文件类型定义
"""

import os
import time
import random
import aiohttp
import asyncio

from typing import Dict, List, Any, TypedDict, Optional, Union, Callable, TypeVar, Awaitable
from functools import wraps
from .utils import get_logger

from dotenv import load_dotenv
load_dotenv(override=True)

# ============================
# 文件类型定义
# ============================

# 支持解析的文档类型（包含文档、图像等所有支持的格式）
SUPPORTED_DOC_TYPES = [
    # PDF文档
    '.pdf',
    
    # Microsoft Office文档
    '.doc', '.docx',        # Word文档
    '.xls', '.xlsx',        # Excel电子表格
    '.ppt', '.pptx',        # PowerPoint演示文稿
    '.rtf',                 # 富文本格式

    # 电子表格
    '.csv',                 # CSV文件
    '.epub',                # EPUB电子书
    
    # OpenDocument格式
    '.odt',                 # OpenDocument文本
    '.ods',                 # OpenDocument电子表格
    '.odp',                 # OpenDocument演示文稿
    
    # 文本文档
    '.txt',                 # 纯文本
    '.md', '.markdown',     # Markdown文档
    '.json',                # JSON文档
    
    # 图像文件（支持OCR文字识别）
    '.jpg', '.jpeg',        # JPEG图像
    '.png',                 # PNG图像
    '.gif',                 # GIF图像
    '.bmp',                 # 位图
    '.webp',                # WebP图像
    '.tiff',                # TIFF图像
    
    # 压缩文件（解包处理）
    '.zip',                 # ZIP压缩包
    '.rar',                 # RAR压缩包  
    '.7z',                  # 7-Zip压缩包
    '.tar',                 # TAR归档文件
    '.gz',                  # GZIP压缩文件
    '.tar.gz', '.tgz',      # TAR.GZ压缩包
    '.tar.bz2', '.tbz2',    # TAR.BZ2压缩包
]

# 忽略的文件类型（不进行解析的文件格式）
IGNORED_TYPES = [
    # 磁盘镜像
    '.iso', '.img', '.dmg',
    
    # 二进制文件
    '.bin', '.exe', '.msi',
    
    # 包文件
    '.pkg', '.deb', '.rpm', '.app', '.ipa', '.apk',
]

# ============================
# Resource ID 处理配置
# ============================

# 特殊的resource_id前缀配置
SPECIAL_RESOURCE_PREFIXES = {
    'pdf_img_': {
        'type': 'pdf_image', 
        'default_extension': '.png',
        'description': 'PDF文档中提取的图片资源（resource_id已包含扩展名）'
    },
    'archive_file_': {
        'type': 'archive_file', 
        'description': '压缩包中提取的文件资源'
    }
}

# Resource ID vs URL 的检测规则
RESOURCE_ID_DETECTION_RULES = {
    'url_schemes': ['http://', 'https://', 'ftp://'],
    'resource_id_patterns': [
        r'^[a-zA-Z0-9_-]+\.[a-zA-Z0-9]+$',  # 文件名格式
        r'^[a-zA-Z_]+_[a-fA-F0-9]+.*$',      # 带前缀的ID格式
    ],
    'min_length': 3,
    'max_length': 512
}


# 从环境变量获取配置 URL 基地址
CONFIG_URL_BASE = os.environ.get("CONFIG_URL_BASE")
if not CONFIG_URL_BASE:
    raise ValueError("环境变量 CONFIG_URL_BASE 未设置")

# 缓存时间（毫秒）
CACHE_TIME = 1000 * 60  # 1分钟

# 日志配置
logger = get_logger(__name__)

# 类型定义
T = TypeVar('T')

class Endpoint(TypedDict):
    url: str

class McpServer(TypedDict):
    name: str
    version: str
    category: Optional[List[str]]
    endpoints: List[Endpoint]

class McpServerInstance(TypedDict):
    name: str
    version: str
    category: Optional[List[str]]
    endpoints: str

# 缓存变量
config_cache = {"lastUpdate": 0, "data": None}
server_cache = {"lastUpdate": 0, "data": None}


def sync(max_try_times: int = 3):
    """
    装饰器函数，用于同步请求并处理重试逻辑
    
    Args:
        max_try_times: 最大重试次数
        
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        _promise = None
        try_times = 0
        
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            nonlocal _promise, try_times
            
            if not _promise:
                try:
                    _promise = asyncio.create_task(func(*args, **kwargs))
                    result = await _promise
                    try_times = 0
                    return result
                except Exception as e:
                    try_times += 1
                    logger.warning(f"调用 {func.__name__} 时发生错误，重试次数: {try_times}，错误: {str(e)}")
                    if try_times >= max_try_times:
                        raise Exception("已达到最大重试次数")
                    return await wrapper(*args, **kwargs)
                finally:
                    _promise = None
            else:
                return await _promise
                
        return wrapper
    return decorator

@sync()
async def fetch_config_sync() -> Dict:
    """
    获取配置信息
    
    Returns:
        配置数据字典
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{CONFIG_URL_BASE}/config/get") as response:
                response.raise_for_status()  # 检查HTTP响应状态
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"获取配置时遇到HTTP错误: {str(e)}")
            raise

@sync()
async def fetch_server_sync() -> Dict[str, McpServer]:
    """
    获取服务器信息
    
    Returns:
        服务器数据字典
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{CONFIG_URL_BASE}/server/get") as response:
                response.raise_for_status()  # 检查HTTP响应状态
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"获取服务器信息时遇到HTTP错误: {str(e)}")
            raise

def deep_freeze(obj: Any) -> Any:
    """
    深度冻结对象（在 Python 中实际使用深拷贝）
    
    Args:
        obj: 需要冻结的对象
        
    Returns:
        冻结后的对象（在 Python 中为深拷贝）
    """
    import copy
    return copy.deepcopy(obj)

async def get_config(key: Optional[str] = None) -> Any:
    """
    获取配置信息，带缓存
    
    Args:
        key: 可选的配置键名
        
    Returns:
        完整配置或特定键的配置
    """
    global config_cache
    
    current_time = int(time.time() * 1000)
    if not config_cache["data"] or (current_time - config_cache["lastUpdate"]) > CACHE_TIME:
        data = deep_freeze(await fetch_config_sync())
        config_cache = {
            "lastUpdate": current_time,
            "data": data
        }
    
    if key:
        return config_cache["data"].get(key, {})
    return config_cache["data"]

def random_server(servers: Dict[str, McpServer]) -> Dict[str, McpServerInstance]:
    """
    从服务器列表中随机选择端点
    
    Args:
        servers: 服务器字典
        
    Returns:
        处理后的服务器实例字典
    """
    result: Dict[str, McpServerInstance] = {}
    
    for key in servers.keys():
        if not servers[key]["endpoints"]:
            continue
            
        if len(servers[key]["endpoints"]) == 1:
            result[key] = {
                "name": servers[key]["name"],
                "version": servers[key]["version"],
                "category": servers[key].get("category"),
                "endpoints": servers[key]["endpoints"][0]["url"]
            }
            continue
            
        endpoints = [e["url"] for e in servers[key]["endpoints"]]
        random_endpoint = random.choice(endpoints)
        result[key] = {
            "name": servers[key]["name"],
            "version": servers[key]["version"],
            "category": servers[key].get("category"),
            "endpoints": random_endpoint
        }
    
    return result

async def get_server(key: Optional[str] = None) -> Dict[str, McpServerInstance]:
    """
    获取服务器信息，带缓存
    
    Args:
        key: 可选的服务器键名
        
    Returns:
        完整服务器信息或特定键的服务器信息
    """
    global server_cache
    
    current_time = int(time.time() * 1000)
    if not server_cache["data"] or (current_time - server_cache["lastUpdate"]) > CACHE_TIME:
        data = deep_freeze(await fetch_server_sync())
        server_cache = {
            "lastUpdate": current_time,
            "data": data
        }
    
    if key:
        if key in server_cache["data"]:
            return random_server({key: server_cache["data"][key]})
        else:
            return {}
    
    return random_server(server_cache["data"])

async def get_cat_server(cats: Union[str, List[str]]) -> Dict[str, McpServerInstance]:
    """
    按分类获取服务器信息
    
    Args:
        cats: 分类名称或分类名称列表
        
    Returns:
        匹配分类的服务器信息
    """
    if not isinstance(cats, list):
        cats = [cats]
    
    servers = await get_server()
    result: Dict[str, McpServerInstance] = {}
    
    for key in servers.keys():
        if servers[key].get("category") and any(cat in cats for cat in servers[key]["category"]):
            result[key] = servers[key]
    
    return result
