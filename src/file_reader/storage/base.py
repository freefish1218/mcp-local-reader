"""
存储客户端基类和共用工具
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseStorageClient(ABC):
    """存储客户端基类"""
    
    def __init__(self):
        pass
    
    @abstractmethod
    def get_file_info(self, resource_id: str, headers: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            resource_id: 资源ID
            headers: HTTP头部信息（如果适用）
            
        Returns:
            文件信息字典，失败返回None
        """
        pass
    
    
    @abstractmethod
    def clear_cache(self):
        """清除缓存"""
        pass 