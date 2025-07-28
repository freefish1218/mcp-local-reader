"""
解析结果缓存管理器
负责管理文档解析结果的缓存
"""

import os
import json
import hashlib
import time
from typing import Dict, Any, Optional

from diskcache import Cache

from .utils import get_logger


class ParsedContentCache:
    """解析结果缓存管理器"""

    def __init__(self):
        """初始化解析结果缓存管理器"""
        self.logger = get_logger("parsed_cache")
        
        # 初始化解析结果缓存
        cache_root = os.getenv("CACHE_ROOT_DIR", "cache")
        cache_dir = os.path.join(cache_root, "parsed_content")
        cache_size_mb = int(os.getenv("PARSED_CONTENT_CACHE_SIZE_MB", "2000"))
        cache_size_bytes = cache_size_mb * 1024 * 1024
        
        self.cache = Cache(cache_dir, size_limit=cache_size_bytes)
        
        # 缓存有效期（天）
        self.expire_days = int(os.getenv("CACHE_EXPIRE_DAYS", "90"))
        self.expire_seconds = self.expire_days * 24 * 3600
        
        self.logger.info(f"解析结果缓存初始化完成 - 目录: {cache_dir}, 大小: {cache_size_mb}MB, 有效期: {self.expire_days}天")
        

    def get_cache_key(self, file_content: bytes, parser_name: str, parser_version: str, 
                     parse_config: Optional[Dict[str, Any]] = None) -> str:
        """
        生成解析结果缓存键
        
        Args:
            file_content: 文件内容字节数据
            parser_name: 解析器名称
            parser_version: 解析器版本
            parse_config: 解析配置参数
            
        Returns:
            缓存键字符串
        """
        # 文件内容哈希
        file_hash = hashlib.sha256(file_content).hexdigest()[:16]
        
        # 解析器版本
        parser_version_str = f"{parser_name}:v{parser_version}"
        
        # 配置哈希（如果有配置参数）
        config_hash = ""
        if parse_config:
            config_str = json.dumps(parse_config, sort_keys=True)
            config_hash = f":{hashlib.md5(config_str.encode()).hexdigest()[:8]}"
        
        # 生成最终缓存键
        cache_key = f"parsed:{file_hash}:{parser_version_str}{config_hash}"
        return cache_key

    def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的解析结果
        
        Args:
            cache_key: 缓存键
            
        Returns:
            缓存的解析结果，未找到返回None
        """
        try:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                self.logger.debug(f"解析结果缓存命中: {cache_key}")
                return cached_data
            else:
                self.logger.debug(f"解析结果缓存未命中: {cache_key}")
                return None
        except Exception as e:
            self.logger.warning(f"获取缓存失败: {cache_key}, 错误: {e}")
            return None

    def cache_parse_result(self, cache_key: str, parse_result: Dict[str, Any], 
                          parser_info: Dict[str, Any]) -> bool:
        """
        缓存解析结果
        
        Args:
            cache_key: 缓存键
            parse_result: 解析结果数据
            parser_info: 解析器信息（名称、版本等）
            
        Returns:
            是否成功缓存
        """
        try:
            # 构建缓存数据
            cache_data = {
                "content": parse_result.get("content", ""),
                "doc_type": parse_result.get("doc_type", "unknown"),
                "metadata": parse_result.get("metadata", {}),
                "image_resources": parse_result.get("image_resources", []),
                "parser_name": parser_info.get("name", "unknown"),
                "parser_version": parser_info.get("version", "1.0"),
                "parsing_time": parse_result.get("parsing_time", 0),
                "content_length": len(parse_result.get("content", "")),
                "timestamp": int(time.time()),
                "cache_key": cache_key
            }
            
            # 保存到缓存
            self.cache.set(cache_key, cache_data, expire=self.expire_seconds)
            
            self.logger.debug(f"解析结果已缓存: {cache_key}, 内容长度: {cache_data['content_length']}")
            return True
            
        except Exception as e:
            self.logger.warning(f"缓存解析结果失败: {cache_key}, 错误: {e}")
            return False

    def clear_cache(self):
        """清理所有解析结果缓存"""
        try:
            if self.cache:
                self.cache.clear()
                self.logger.info("解析结果缓存已清理")
        except Exception as e:
            self.logger.error(f"清理解析结果缓存失败: {e}")

    def clear_parser_cache(self, parser_name: str):
        """
        清理指定解析器的缓存
        
        Args:
            parser_name: 解析器名称
        """
        try:
            keys_to_delete = []
            for key in self.cache:
                if key.startswith(f"parsed:") and f":{parser_name}:v" in key:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.cache[key]
            
            self.logger.info(f"已清理 {parser_name} 解析器的 {len(keys_to_delete)} 个缓存项")
            
        except Exception as e:
            self.logger.error(f"清理解析器缓存失败: {parser_name}, 错误: {e}")



# 全局解析缓存实例
_global_parsed_cache = None

def get_parsed_cache() -> ParsedContentCache:
    """获取全局解析缓存实例"""
    global _global_parsed_cache
    if _global_parsed_cache is None:
        _global_parsed_cache = ParsedContentCache()
    return _global_parsed_cache 