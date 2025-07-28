"""
文件读取器模块
提供本地文件内容提取功能
"""

from .core import FileReader
from .models import ReadResponse, FailureType, LocalReadRequest
from .storage import LocalFileStorageClient

__version__ = "1.0.0"

__all__ = [
    "FileReader",
    "ReadResponse",
    "FailureType",
    "LocalReadRequest", 
    "LocalFileStorageClient"
] 