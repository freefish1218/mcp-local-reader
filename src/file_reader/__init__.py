"""
文件读取器模块
提供文件内容提取功能
"""

from .core import FileReader
from .models import ReadRequest, ReadResponse, FailureType, LocalReadRequest, UrlWithReferer
from .storage import HTTPDownloadStorageClient, LocalFileStorageClient

__version__ = "1.0.0"

__all__ = [
    "FileReader",
    "ReadRequest", 
    "ReadResponse",
    "FailureType",
    "LocalReadRequest",
    "UrlWithReferer",
    "HTTPDownloadStorageClient",
    "LocalFileStorageClient"
] 