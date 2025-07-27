"""
存储客户端模块
提供各种文件存储和下载功能
"""

from .base import BaseStorageClient
from .local import LocalFileStorageClient
from .http_client import HTTPDownloadStorageClient

__all__ = [
    'BaseStorageClient',
    'LocalFileStorageClient',
    'HTTPDownloadStorageClient'
] 