"""
本地文件存储客户端
负责读取本地文件系统中的文件
"""

import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any

from diskcache import Cache

from .base import BaseStorageClient
from ..utils import get_logger


class LocalFileStorageClient(BaseStorageClient):
    """
    本地文件存储客户端
    负责读取本地文件系统中的文件
    """
    
    def __init__(
        self,
        allowed_directories: Optional[list] = None,
        allow_absolute_paths: bool = False,
        max_file_size: int = None,
        cache_directory: Optional[str] = None,
        cache_size_mb: Optional[int] = None
    ):
        """
        初始化本地文件存储客户端
        
        Args:
            allowed_directories: 允许访问的目录列表（相对路径）
            allow_absolute_paths: 是否允许绝对路径
            max_file_size: 最大文件大小限制（字节），为None时不设置默认限制
            cache_directory: 本地缓存目录
            cache_size_mb: 缓存大小(MB)
        """
        super().__init__()
        self.logger = get_logger("storage.local")
        
        # 安全配置
        self.allow_absolute_paths = allow_absolute_paths
        self.max_file_size = max_file_size
        
        # 设置允许访问的目录
        if allowed_directories is None:
            # 默认允许当前工作目录
            self.allowed_directories = [os.getcwd()]
        else:
            self.allowed_directories = [os.path.abspath(d) for d in allowed_directories]
        
        # 获取缓存目录配置
        if cache_directory is None:
            cache_root = os.getenv("CACHE_ROOT_DIR", "cache")
            cache_directory = os.path.join(cache_root, "local_file_reader")
        
        # 获取缓存大小配置
        if cache_size_mb is None:
            cache_size_mb = int(os.getenv("LOCAL_FILE_READER_CACHE_SIZE_MB", "100"))
        
        cache_size_bytes = cache_size_mb * 1024 * 1024
        
        # 初始化本地缓存
        self.cache = Cache(cache_directory, size_limit=cache_size_bytes)
        
        self.logger.info(f"本地文件读取器初始化完成")
        self.logger.info(f"允许的目录: {self.allowed_directories}")
        self.logger.info(f"允许绝对路径: {self.allow_absolute_paths}")
        self.logger.info(f"缓存配置 - 目录: {cache_directory}, 大小: {cache_size_mb}MB")
        
    
    def get_file_info(self, file_path: str, headers: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            headers: HTTP头部信息（本地文件存储中不使用）
            
        Returns:
            文件信息字典，失败返回None
        """
        try:
            # 安全检查
            safe_path = self._validate_file_path(file_path)
            if not safe_path or not os.path.exists(safe_path):
                return None
            
            stat = os.stat(safe_path)
            
            # 尝试猜测MIME类型
            content_type, _ = mimetypes.guess_type(safe_path)
            if not content_type:
                content_type = "application/octet-stream"
            
            return {
                "size": stat.st_size,
                "last_modified": stat.st_mtime,
                "content_type": content_type,
                "path": safe_path
            }
            
        except Exception as e:
            self.logger.error(f"获取文件信息失败: {file_path}, 错误: {e}")
            return None
    
    def _validate_file_path(self, file_path: str) -> Optional[str]:
        """
        验证文件路径的安全性
        
        Args:
            file_path: 待验证的文件路径
            
        Returns:
            规范化后的安全路径，验证失败返回None
        """
        try:
            # 规范化路径
            if os.path.isabs(file_path):
                if not self.allow_absolute_paths:
                    self.logger.error(f"不允许使用绝对路径: {file_path}")
                    return None
                normalized_path = os.path.normpath(file_path)
            else:
                # 相对路径基于当前工作目录
                normalized_path = os.path.abspath(os.path.normpath(file_path))
            
            # 解析真实路径（处理符号链接）
            real_path = os.path.realpath(normalized_path)
            
            # 检查路径是否在允许的目录内
            path_allowed = False
            for allowed_dir in self.allowed_directories:
                try:
                    # 使用 Path.resolve() 来处理路径比较
                    real_path_obj = Path(real_path).resolve()
                    allowed_dir_obj = Path(allowed_dir).resolve()
                    
                    # 检查是否为子路径（兼容Python 3.8及以下版本）
                    try:
                        # Python 3.9+ 支持 is_relative_to()
                        if hasattr(real_path_obj, 'is_relative_to'):
                            if real_path_obj.is_relative_to(allowed_dir_obj):
                                path_allowed = True
                                break
                        else:
                            # Python 3.8及以下版本的兼容方案
                            try:
                                real_path_obj.relative_to(allowed_dir_obj)
                                path_allowed = True
                                break
                            except ValueError:
                                # 不是子路径，继续检查下一个
                                continue
                    except Exception:
                        # 如果路径比较失败，使用字符串比较作为后备
                        real_path_str = str(real_path_obj)
                        allowed_dir_str = str(allowed_dir_obj)
                        if real_path_str.startswith(allowed_dir_str + os.sep) or real_path_str == allowed_dir_str:
                            path_allowed = True
                            break
                            
                except Exception as e:
                    self.logger.warning(f"路径比较失败: {allowed_dir}, 错误: {e}")
                    continue
            
            if not path_allowed:
                self.logger.error(f"文件路径不在允许范围内: {file_path} -> {real_path}")
                return None
            
            return real_path
            
        except Exception as e:
            self.logger.error(f"路径验证失败: {file_path}, 错误: {e}")
            return None
    
    def _get_cache_key(self, file_path: str) -> str:
        """
        生成缓存键
        
        Args:
            file_path: 文件路径
            
        Returns:
            缓存键字符串
        """
        return hashlib.md5(file_path.encode()).hexdigest()
    
    def _get_enhanced_cache_key(self, file_path: str, file_info: Dict[str, Any]) -> str:
        """
        生成增强的缓存键（包含文件元数据）
        
        Args:
            file_path: 文件路径
            file_info: 文件信息（包含大小、修改时间等）
            
        Returns:
            增强的缓存键字符串
        """
        # 组合文件路径、大小、修改时间生成更准确的缓存键
        key_components = [
            file_path,
            str(file_info.get("size", 0)),
            str(file_info.get("mtime", 0))
        ]
        combined = "|".join(key_components)
        return hashlib.md5(combined.encode()).hexdigest()
    
    
    def clear_cache(self):
        """清除本地文件缓存"""
        try:
            self.cache.clear()
            self.logger.info("本地文件缓存已清空")
        except Exception as e:
            self.logger.error(f"清空本地文件缓存失败: {e}")
    
    def clear_file_cache(self, file_path: str):
        """
        清除特定文件的缓存
        
        Args:
            file_path: 文件路径
        """
        try:
            # 尝试获取文件信息生成缓存键
            safe_path = self._validate_file_path(file_path)
            if safe_path and os.path.exists(safe_path):
                file_stat = os.stat(safe_path)
                file_info = {
                    "size": file_stat.st_size,
                    "mtime": file_stat.st_mtime,
                    "path": safe_path
                }
                cache_key = self._get_enhanced_cache_key(safe_path, file_info)
                if cache_key in self.cache:
                    del self.cache[cache_key]
                    self.logger.info(f"已清除文件缓存: {file_path}")
                else:
                    self.logger.info(f"文件未缓存: {file_path}")
            else:
                # 如果无法获取文件信息，尝试基础缓存键
                basic_cache_key = self._get_cache_key(file_path)
                if basic_cache_key in self.cache:
                    del self.cache[basic_cache_key]
                    self.logger.info(f"已清除文件基础缓存: {file_path}")
                
        except Exception as e:
            self.logger.error(f"清除文件缓存失败: {file_path}, 错误: {e}")
    
    def get_cache_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        获取特定文件的缓存信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            缓存信息字典，如果文件未缓存则返回None
        """
        try:
            safe_path = self._validate_file_path(file_path)
            if not safe_path or not os.path.exists(safe_path):
                return None
            
            file_stat = os.stat(safe_path)
            file_info = {
                "size": file_stat.st_size,
                "mtime": file_stat.st_mtime,
                "path": safe_path
            }
            
            cache_key = self._get_enhanced_cache_key(safe_path, file_info)
            
            if cache_key in self.cache:
                return {
                    "is_cached": True,
                    "cache_key": cache_key,
                    "file_size": file_info["size"],
                    "last_modified": file_info["mtime"]
                }
            else:
                return {
                    "is_cached": False,
                    "cache_key": cache_key,
                    "file_size": file_info["size"],
                    "last_modified": file_info["mtime"]
                }
                
        except Exception as e:
            self.logger.error(f"获取缓存信息失败: {file_path}, 错误: {e}")
            return None 