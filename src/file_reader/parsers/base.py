"""
解析器基类
定义所有文档解析器的基类接口
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import os
import time

from ..models import ParseResult
from ..utils import get_logger, normalize_content
from ..parsed_cache import get_parsed_cache
from .mixins import ImageProcessingMixin


class BaseParser(ImageProcessingMixin, ABC):
    """
    文档解析器基类
    所有具体解析器都应继承此类并实现 parse 方法
    """
    
    def __init__(self):
        """
        初始化解析器
        """
        self.logger = get_logger(f"parser.{self.__class__.__name__}")
        
        # 初始化图片处理混入
        super().__init__()
        
        # 解析器信息
        self.parser_name = self.__class__.__name__.replace("Parser", "").lower()
        self.parser_version = "1.0"  # 子类可以重写此版本号
        
        # 解析缓存
        self.parsed_cache = get_parsed_cache()
    
    
    def parse(self, content: bytes, file_extension: str = None, **kwargs) -> ParseResult:
        """
        解析文档方法，带缓存支持（同步版本）
        
        Args:
            content: 文件内容字节数据
            file_extension: 文件扩展名
            **kwargs: 其他解析参数
            
        Returns:
            解析结果对象
        """
        # 生成缓存键（包含kwargs参数）
        cache_key = self.parsed_cache.get_cache_key(
            content, 
            self.parser_name, 
            self.parser_version,
            kwargs if kwargs else None
        )
        
        # 尝试从缓存获取结果
        cached_result = self.parsed_cache.get_cached_result(cache_key)
        if cached_result:
            self.logger.debug(f"使用缓存的解析结果: {cache_key}")
            return ParseResult(
                success=True,
                content=cached_result["content"],
                doc_type=cached_result["doc_type"],
                metadata=cached_result["metadata"],
                image_resources=cached_result.get("image_resources", [])
            )
        
        # 缓存未命中，执行实际解析
        start_time = time.time()
        parse_result = self._parse_content(content, file_extension, **kwargs)
        parsing_time = time.time() - start_time
        
        # 如果解析成功，缓存结果
        if parse_result.success:
            result_data = {
                "content": parse_result.content,
                "doc_type": parse_result.doc_type,
                "metadata": parse_result.metadata,
                "image_resources": getattr(parse_result, 'image_resources', []),
                "parsing_time": parsing_time
            }
            parser_info = {
                "name": self.parser_name,
                "version": self.parser_version
            }
            self.parsed_cache.cache_parse_result(cache_key, result_data, parser_info)
        
        return parse_result
    
    async def parse_async(self, content: bytes, file_extension: str = None, **kwargs) -> ParseResult:
        """
        解析文档方法，带缓存支持（异步版本）
        
        Args:
            content: 文件内容字节数据
            file_extension: 文件扩展名
            **kwargs: 其他解析参数
            
        Returns:
            解析结果对象
        """
        # 生成缓存键（包含kwargs参数）
        cache_key = self.parsed_cache.get_cache_key(
            content, 
            self.parser_name, 
            self.parser_version,
            kwargs if kwargs else None
        )
        
        # 尝试从缓存获取结果
        cached_result = self.parsed_cache.get_cached_result(cache_key)
        if cached_result:
            self.logger.debug(f"使用缓存的解析结果: {cache_key}")
            return ParseResult(
                success=True,
                content=cached_result["content"],
                doc_type=cached_result["doc_type"],
                metadata=cached_result["metadata"],
                image_resources=cached_result.get("image_resources", [])
            )
        
        # 缓存未命中，执行实际解析
        start_time = time.time()
        parse_result = await self._parse_content_async(content, file_extension, **kwargs)
        parsing_time = time.time() - start_time
        
        # 如果解析成功，缓存结果
        if parse_result.success:
            result_data = {
                "content": parse_result.content,
                "doc_type": parse_result.doc_type,
                "metadata": parse_result.metadata,
                "image_resources": getattr(parse_result, 'image_resources', []),
                "parsing_time": parsing_time
            }
            parser_info = {
                "name": self.parser_name,
                "version": self.parser_version
            }
            self.parsed_cache.cache_parse_result(cache_key, result_data, parser_info)
        
        return parse_result
    
    def _parse_content(self, content: bytes, file_extension: str = None, **kwargs) -> ParseResult:
        """
        实际的解析方法，由子类实现（同步版本）
        
        Args:
            content: 文件内容字节数据
            file_extension: 文件扩展名
            **kwargs: 其他解析参数
            
        Returns:
            解析结果对象
        """
        # 大多数解析器使用同步方法，抛出未实现错误
        raise NotImplementedError("子类必须实现 _parse_content 或 _parse_content_async 方法")
    
    async def _parse_content_async(self, content: bytes, file_extension: str = None, **kwargs) -> ParseResult:
        """
        实际的解析方法，由子类实现（异步版本）
        
        Args:
            content: 文件内容字节数据
            file_extension: 文件扩展名
            **kwargs: 其他解析参数
            
        Returns:
            解析结果对象
        """
        # 对于异步解析器，需要实现此方法
        raise NotImplementedError("异步解析器必须实现 _parse_content_async 方法")
    
    def _normalize_content(self, content: str) -> str:
        """
        规范化文本内容
        
        Args:
            content: 原始文本内容
            
        Returns:
            规范化后的文本内容
        """
        return normalize_content(content)
    
    def _create_error_result(self, message: str) -> ParseResult:
        """
        创建错误结果对象
        
        Args:
            message: 错误信息
            
        Returns:
            表示错误的解析结果对象
        """
        return ParseResult(
            success=False,
            error=message
        )
    
    def _create_success_result(
        self, 
        content: str, 
        doc_type: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> ParseResult:
        """
        创建成功结果对象
        
        Args:
            content: 解析后的文本内容
            doc_type: 文档类型
            metadata: 文档元数据
            
        Returns:
            表示成功的解析结果对象
        """
        return ParseResult(
            success=True,
            content=content,
            doc_type=doc_type,
            metadata=metadata or {}
        )
    
    def _save_temp_file(self, content: bytes, suffix: str = None) -> Path:
        """
        保存临时文件
        
        Args:
            content: 文件内容
            suffix: 文件后缀
            
        Returns:
            临时文件路径
        """
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        try:
            # 确保临时文件权限为600（仅所有者可读写）
            os.chmod(temp_path, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(content)
            return Path(temp_path)
        except Exception:
            os.close(fd)
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    
    def _cleanup_temp_file(self, file_path: Path):
        """
        清理临时文件
        
        Args:
            file_path: 临时文件路径
        """
        try:
            if file_path and file_path.exists():
                file_path.unlink()
        except Exception as e:
            self.logger.warning(f"清理临时文件失败: {file_path}, 错误: {e}") 