"""
统一缓存管理器 - 优化资源消耗
使用单一Cache实例管理所有缓存，减少内存占用
"""

import os
import hashlib
import json
from typing import Optional, Any, Dict
from pathlib import Path

from diskcache import Cache

from .utils import get_logger


class UnifiedCacheManager:
    """统一缓存管理器 - 使用单一Cache实例减少资源消耗"""
    
    _instance = None
    _cache = None
    
    def __new__(cls):
        """单例模式确保只有一个缓存实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化统一缓存"""
        if self._cache is None:
            self.logger = get_logger("unified_cache")
            
            # 读取环境配置
            cache_root = os.getenv("CACHE_ROOT_DIR", "cache")
            cache_dir = os.path.join(cache_root, "unified")
            
            # 统一缓存大小限制（默认500MB，大幅减少）
            total_cache_size_mb = int(os.getenv("TOTAL_CACHE_SIZE_MB", "500"))
            cache_size_bytes = total_cache_size_mb * 1024 * 1024
            
            # 创建单一缓存实例
            self._cache = Cache(
                cache_dir,
                size_limit=cache_size_bytes,
                eviction_policy='least-recently-used'  # LRU策略
            )
            
            # 缓存有效期
            self.expire_days = int(os.getenv("CACHE_EXPIRE_DAYS", "30"))
            self.expire_seconds = self.expire_days * 24 * 3600
            
            self.logger.info(
                f"统一缓存初始化 - 目录: {cache_dir}, "
                f"总大小: {total_cache_size_mb}MB, "
                f"有效期: {self.expire_days}天"
            )
    
    def _make_key(self, namespace: str, key: str) -> str:
        """生成带命名空间的缓存键"""
        return f"{namespace}:{key}"
    
    def get(self, namespace: str, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            namespace: 缓存命名空间（如 'parsed', 'image', 'archive'）
            key: 缓存键
            
        Returns:
            缓存的值，不存在返回None
        """
        full_key = self._make_key(namespace, key)
        try:
            value = self._cache.get(full_key)
            if value is not None:
                self.logger.debug(f"缓存命中: {namespace}/{key[:50]}...")
            return value
        except Exception as e:
            self.logger.error(f"读取缓存失败: {e}")
            return None
    
    def set(self, namespace: str, key: str, value: Any, expire: Optional[int] = None):
        """
        设置缓存值
        
        Args:
            namespace: 缓存命名空间
            key: 缓存键
            value: 要缓存的值
            expire: 过期时间（秒），默认使用配置的过期时间
        """
        full_key = self._make_key(namespace, key)
        expire = expire or self.expire_seconds
        
        try:
            self._cache.set(full_key, value, expire=expire)
            self.logger.debug(f"缓存写入: {namespace}/{key[:50]}...")
        except Exception as e:
            self.logger.error(f"写入缓存失败: {e}")
    
    def delete(self, namespace: str, key: str) -> bool:
        """
        删除缓存项
        
        Args:
            namespace: 缓存命名空间
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        full_key = self._make_key(namespace, key)
        try:
            return self._cache.delete(full_key)
        except Exception as e:
            self.logger.error(f"删除缓存失败: {e}")
            return False
    
    def clear_namespace(self, namespace: str):
        """清空指定命名空间的所有缓存"""
        prefix = f"{namespace}:"
        try:
            for key in list(self._cache.iterkeys()):
                if key.startswith(prefix):
                    self._cache.delete(key)
            self.logger.info(f"清空命名空间缓存: {namespace}")
        except Exception as e:
            self.logger.error(f"清空命名空间缓存失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            return {
                "size": len(self._cache),
                "volume": self._cache.volume(),
                "size_mb": self._cache.volume() / (1024 * 1024),
                "hit_rate": getattr(self._cache, 'hit_rate', 0)
            }
        except Exception as e:
            self.logger.error(f"获取缓存统计失败: {e}")
            return {}
    
    def close(self):
        """关闭缓存"""
        if self._cache:
            self._cache.close()
            self._cache = None
            self.logger.info("缓存已关闭")


# 创建全局缓存管理器实例
cache_manager = UnifiedCacheManager()


# 兼容性包装类
class ParsedContentCache:
    """解析内容缓存的兼容性包装"""
    
    def __init__(self):
        self.logger = get_logger("parsed_cache_compat")
        self.cache_mgr = cache_manager
        self.namespace = "parsed"
    
    def get_cache_key(self, file_content: bytes, parser_name: str, 
                     parser_version: str, parse_config: Optional[Dict] = None) -> str:
        """生成缓存键"""
        key_data = {
            "content_hash": hashlib.sha256(file_content).hexdigest(),
            "parser": parser_name,
            "version": parser_version,
            "config": parse_config or {}
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, file_content: bytes, parser_name: str, 
            parser_version: str, parse_config: Optional[Dict] = None) -> Optional[str]:
        """获取缓存的解析结果"""
        key = self.get_cache_key(file_content, parser_name, parser_version, parse_config)
        return self.cache_mgr.get(self.namespace, key)
    
    def set(self, file_content: bytes, parser_name: str, parser_version: str,
            parsed_content: str, parse_config: Optional[Dict] = None):
        """缓存解析结果"""
        key = self.get_cache_key(file_content, parser_name, parser_version, parse_config)
        self.cache_mgr.set(self.namespace, key, parsed_content)
    
    def clear(self):
        """清空解析缓存"""
        self.cache_mgr.clear_namespace(self.namespace)


class ImageCache:
    """图像缓存的兼容性包装"""
    
    def __init__(self):
        self.logger = get_logger("image_cache_compat")
        self.cache_mgr = cache_manager
        self.namespace = "image"
    
    def get_image_key(self, image_id: str) -> str:
        """生成图像缓存键"""
        return hashlib.md5(image_id.encode()).hexdigest()
    
    def get_image(self, image_id: str) -> Optional[bytes]:
        """获取缓存的图像"""
        key = self.get_image_key(image_id)
        return self.cache_mgr.get(self.namespace, key)
    
    def save_image(self, image_id: str, image_data: bytes) -> bool:
        """保存图像到缓存"""
        key = self.get_image_key(image_id)
        self.cache_mgr.set(self.namespace, key, image_data)
        return True
    
    def clear(self):
        """清空图像缓存"""
        self.cache_mgr.clear_namespace(self.namespace)


class FileCache:
    """文件缓存的兼容性包装"""
    
    def __init__(self):
        self.logger = get_logger("file_cache_compat")
        self.cache_mgr = cache_manager
        self.namespace = "file"
    
    def get_file_key(self, file_id: str) -> str:
        """生成文件缓存键"""
        return hashlib.md5(file_id.encode()).hexdigest()
    
    def get_file(self, file_id: str) -> Optional[bytes]:
        """获取缓存的文件"""
        key = self.get_file_key(file_id)
        return self.cache_mgr.get(self.namespace, key)
    
    def save_file(self, file_id: str, file_data: bytes, metadata: Optional[Dict] = None) -> bool:
        """保存文件到缓存"""
        key = self.get_file_key(file_id)
        cache_data = {
            "data": file_data,
            "metadata": metadata or {}
        }
        self.cache_mgr.set(self.namespace, key, cache_data)
        return True
    
    def clear(self):
        """清空文件缓存"""
        self.cache_mgr.clear_namespace(self.namespace)