"""
存储客户端模块
提供本地文件存储功能
"""

from .base import BaseStorageClient
from .local import LocalFileStorageClient

__all__ = [
    'BaseStorageClient',
    'LocalFileStorageClient'
] 