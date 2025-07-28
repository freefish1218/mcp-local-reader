"""
文件处理混入类
为解析器提供统一的文件处理能力（用于压缩包文件）
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple

from ...file_cache import FileCacheManager


class FileProcessingMixin:
    """文件处理混入类，为解析器提供文件缓存和处理能力"""
    
    def __init__(self):
        """
        初始化文件处理混入
        """
        # 获取或创建文件缓存管理器
        if not hasattr(self, '_file_cache_manager'):
            self._file_cache_manager = FileCacheManager()
    
    
    def process_archive_files(self, files: List[Path], markdown_content: str, 
                             temp_dir: str, doc_type: str, source_file_path: str = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        处理压缩包中的文件，统一的文件处理接口
        
        Args:
            files: 文件路径列表
            markdown_content: 原始Markdown内容
            temp_dir: 临时目录
            doc_type: 文档类型 (zip, rar, 7z, etc.)
            source_file_path: 原始压缩包文件路径（可选）
            
        Returns:
            (处理后的Markdown内容, 文件资源列表)
        """
        if not files:
            return markdown_content, []
        
        # 构建文档信息
        doc_info = {
            'markdown_content': markdown_content,
            'doc_type': doc_type,
            'temp_dir': temp_dir,
            'source_file_path': source_file_path
        }
        
        # 使用文件缓存管理器处理文件
        return self._file_cache_manager.cache_archive_files(files, doc_info)
    
    
    def clear_file_cache(self):
        """清空文件缓存"""
        self._file_cache_manager.clear_cache()
