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
        
        # 统计信息
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_writes": 0,
            "cache_errors": 0
        }

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
                self.stats["cache_hits"] += 1
                return cached_data
            else:
                self.logger.debug(f"解析结果缓存未命中: {cache_key}")
                self.stats["cache_misses"] += 1
                return None
        except Exception as e:
            self.logger.warning(f"获取缓存失败: {cache_key}, 错误: {e}")
            self.stats["cache_errors"] += 1
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
            self.stats["cache_writes"] += 1
            return True
            
        except Exception as e:
            self.logger.warning(f"缓存解析结果失败: {cache_key}, 错误: {e}")
            self.stats["cache_errors"] += 1
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

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计数据
        """
        try:
            # 基础统计
            total_items = len(self.cache) if self.cache else 0
            total_size = 0
            parser_stats = {}
            doc_type_stats = {}
            
            # 遍历缓存项统计详细信息
            if self.cache:
                for key in self.cache:
                    try:
                        cached_data = self.cache.get(key)
                        if cached_data:
                            content_length = cached_data.get('content_length', 0)
                            total_size += content_length
                            
                            # 按解析器统计
                            parser_name = cached_data.get('parser_name', 'unknown')
                            if parser_name not in parser_stats:
                                parser_stats[parser_name] = {"count": 0, "total_size": 0}
                            parser_stats[parser_name]["count"] += 1
                            parser_stats[parser_name]["total_size"] += content_length
                            
                            # 按文档类型统计
                            doc_type = cached_data.get('doc_type', 'unknown')
                            if doc_type not in doc_type_stats:
                                doc_type_stats[doc_type] = {"count": 0, "total_size": 0}
                            doc_type_stats[doc_type]["count"] += 1
                            doc_type_stats[doc_type]["total_size"] += content_length
                            
                    except Exception as e:
                        self.logger.debug(f"统计缓存项失败: {key}, 错误: {e}")
            
            # 计算命中率
            total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
            hit_rate = self.stats["cache_hits"] / total_requests if total_requests > 0 else 0
            
            return {
                "total_items": total_items,
                "total_content_size": total_size,
                "cache_hits": self.stats["cache_hits"],
                "cache_misses": self.stats["cache_misses"],
                "cache_writes": self.stats["cache_writes"],
                "cache_errors": self.stats["cache_errors"],
                "cache_hit_rate": hit_rate,
                "parser_stats": parser_stats,
                "doc_type_stats": doc_type_stats,
                "cache_directory": str(self.cache.directory) if hasattr(self.cache, 'directory') else None,
                "cache_size_limit": getattr(self.cache, 'size_limit', 0),
                "expire_days": self.expire_days
            }
            
        except Exception as e:
            self.logger.error(f"获取缓存统计失败: {e}")
            return {
                "total_items": 0,
                "total_content_size": 0,
                "cache_hits": self.stats["cache_hits"],
                "cache_misses": self.stats["cache_misses"],
                "cache_writes": self.stats["cache_writes"],
                "cache_errors": self.stats["cache_errors"],
                "cache_hit_rate": 0,
                "parser_stats": {},
                "doc_type_stats": {},
                "error": str(e)
            }


# 全局解析缓存实例
_global_parsed_cache = None

def get_parsed_cache() -> ParsedContentCache:
    """获取全局解析缓存实例"""
    global _global_parsed_cache
    if _global_parsed_cache is None:
        _global_parsed_cache = ParsedContentCache()
    return _global_parsed_cache 