"""
文件缓存管理器
专门管理压缩包中提取的文件的缓存
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from diskcache import Cache

from .utils import get_logger


class FileCacheManager:
    """压缩包文件缓存管理器"""

    def __init__(self):
        """
        初始化文件缓存管理器
        """
        self.logger = get_logger("file_cache")
        
        # 初始化统一的文件缓存
        cache_root = os.getenv("CACHE_ROOT_DIR", "cache")
        file_cache_dir = os.path.join(cache_root, "archive_files")
        cache_size_mb = int(os.getenv("ARCHIVE_FILE_CACHE_SIZE_MB", "2000"))
        cache_size_bytes = cache_size_mb * 1024 * 1024

        # 计算缓存过期时间
        expire_days = int(os.getenv("CACHE_EXPIRE_DAYS", "90"))
        expire_seconds = expire_days * 24 * 3600
                
        self.cache = Cache(file_cache_dir, size_limit=cache_size_bytes, expire=expire_seconds)
        self.logger.info(f"压缩包文件缓存初始化完成 - 目录: {file_cache_dir}, 大小: {cache_size_mb}MB, 有效期: {expire_days}天")

    def cache_archive_files(self, files: List[Path], doc_info: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        批量缓存压缩包文件，并处理Markdown内容中的文件引用
        
        Args:
            files: 文件路径列表
            doc_info: 文档信息，包含文档类型、Markdown内容等
            
        Returns:
            (处理后的Markdown内容, 文件资源列表)
        """
        markdown_content = doc_info.get('markdown_content', '')
        temp_dir = doc_info.get('temp_dir', '')
        
        file_resources = []
        processed_markdown = markdown_content
        
        # 本地文件模式：直接移除文件引用，不进行上传处理
        self.logger.info(f"本地文件模式：移除文档中的 {len(files)} 个文件引用")
        
        for file_path in files:
            try:
                # 移除Markdown中的文件引用
                processed_markdown = self._remove_file_references(
                    processed_markdown, file_path, temp_dir
                )
                self.logger.debug(f"移除文件引用: {file_path.name}")
                
            except Exception as e:
                self.logger.warning(f"处理文件失败: {file_path.name}, 错误: {e}")
                continue
        
        return processed_markdown, file_resources


    def _remove_file_references(self, markdown_content: str, file_path: Path, temp_dir: str) -> str:
        """
        移除Markdown中的文件引用
        
        Args:
            markdown_content: 原始Markdown内容
            file_path: 文件路径
            temp_dir: 临时目录
            
        Returns:
            处理后的Markdown内容
        """
        # 获取可能的文件引用路径
        absolute_path = str(file_path.absolute())
        filename_only = file_path.name
        
        # 如果有临时目录，计算相对路径
        relative_path = filename_only
        if temp_dir:
            try:
                temp_path = Path(temp_dir)
                relative_path = str(file_path.relative_to(temp_path))
            except:
                pass
        
        # 定义所有可能的文件引用格式
        possible_refs = [
            f"[{filename_only}]({filename_only})",
            f"[{filename_only}]({relative_path})", 
            f"[{filename_only}]({absolute_path})",
            f"({filename_only})",
            f"({relative_path})",
            f"({absolute_path})"
        ]
        
        # 执行移除
        for old_ref in possible_refs:
            markdown_content = markdown_content.replace(old_ref, '')
        
        return markdown_content

    def _extract_file_info(self, file_path: Path, file_data: bytes) -> Dict[str, Any]:
        """
        提取文件基本信息
        
        Args:
            file_path: 文件路径
            file_data: 文件数据
            
        Returns:
            文件信息字典
        """
        info = {}
        
        try:
            # 文件基本信息
            info['file_size'] = len(file_data)
            info['file_extension'] = file_path.suffix.lower()
            info['created_from'] = 'archive_extraction'
            
            # 尝试获取更多文件信息
            stat_info = file_path.stat()
            info['modified_time'] = stat_info.st_mtime
            
        except Exception as e:
            self.logger.warning(f"提取文件信息失败: {e}")
        
        return info

    def _get_content_type(self, file_path: Path) -> str:
        """
        根据文件扩展名获取MIME类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            MIME类型字符串
        """
        extension = file_path.suffix.lower()
        
        mime_types = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.json': 'application/json',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed',
            '.7z': 'application/x-7z-compressed',
            '.tar': 'application/x-tar',
            '.gz': 'application/gzip'
        }
        
        return mime_types.get(extension, 'application/octet-stream')


    def clear_cache(self):
        """清空文件缓存"""
        if self.cache:
            self.cache.clear()
            self.logger.info("压缩包文件缓存已清空")

