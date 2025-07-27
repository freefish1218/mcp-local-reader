"""
文件缓存管理器
专门管理压缩包中提取的文件的缓存和上传
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from diskcache import Cache

from .utils import get_logger


class FileCacheManager:
    """压缩包文件缓存管理器"""

    def __init__(self, storage_client=None):
        """
        初始化文件缓存管理器
        
        Args:
            storage_client: 存储客户端，用于上传文件到存储服务
        """
        self.logger = get_logger("file_cache")
        
        # 存储客户端，用于上传文件
        self.storage_client = storage_client
        
        # 文件上传配置
        self.upload_enabled = os.getenv("ARCHIVE_FILE_AUTO_UPLOAD_ENABLED", "true").lower() == "true"
        self.upload_timeout = int(os.getenv("ARCHIVE_FILE_UPLOAD_TIMEOUT", "120"))
        self.max_concurrent_uploads = int(os.getenv("ARCHIVE_FILE_UPLOAD_MAX_CONCURRENT", "5"))
        
        self.logger.info(f"文件上传配置 - 启用: {self.upload_enabled}, 超时: {self.upload_timeout}s, 最大并发: {self.max_concurrent_uploads}")
        
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
        
        # 统计信息
        self.upload_stats = {
            "total_uploads": 0,
            "successful_uploads": 0,
            "failed_uploads": 0,
            "upload_errors": []
        }

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
        doc_type = doc_info.get('doc_type', 'unknown')
        temp_dir = doc_info.get('temp_dir', '')
        
        file_resources = []
        processed_markdown = markdown_content
        
        # 准备上传的文件数据
        upload_files = []
        file_mapping = {}  # 索引 -> 文件信息的映射
        
        for file_path in files:
            try:
                # 检查文件大小限制
                file_size = file_path.stat().st_size
                max_single_file_size = int(os.getenv("ARCHIVE_MAX_FILE_SIZE_MB", "100")) * 1024 * 1024
                if file_size > max_single_file_size:
                    self.logger.warning(f"文件过大，跳过上传: {file_path.name}, 大小: {file_size}")
                    continue
                
                # 读取文件数据
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                if not file_data:
                    continue
                
                # 提取文件信息
                file_info = self._extract_file_info(file_path, file_data)
                
                # 准备上传的文件信息
                upload_file_info = {
                    'data': file_data,
                    'filename': file_path.name,
                    'content_type': self._get_content_type(file_path)
                }
                upload_files.append(upload_file_info)
                
                # 保存映射关系
                file_mapping[len(upload_files) - 1] = {
                    'file_path': file_path,
                    'file_data': file_data,
                    'file_info': file_info
                }
                
                self.logger.debug(f"准备上传文件: {file_path.name}")
                
            except Exception as e:
                self.logger.warning(f"处理文件失败: {file_path.name}, 错误: {e}")
                continue
        
        # 批量上传文件到HTTP存储服务
        if self.upload_enabled and self.storage_client and hasattr(self.storage_client, 'upload_files_batch') and upload_files:
            try:
                self.logger.info(f"开始批量上传 {len(upload_files)} 个文件到HTTP存储服务")
                
                # 同步调用异步批量上传方法
                import asyncio
                import concurrent.futures
                
                # 在新线程中运行异步方法，避免事件循环冲突
                def run_async_upload():
                    # 创建新的事件循环
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self.storage_client.upload_files_batch(upload_files))
                    finally:
                        new_loop.close()
                
                # 在线程池中执行异步上传，增加并发度
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    future = executor.submit(run_async_upload)
                    upload_results = future.result(timeout=self.upload_timeout)
                
                self.logger.info(f"批量上传完成，收到 {len(upload_results)} 个结果")
                
                # 用真实的resource_id替换Markdown中的文件引用
                successful_uploads = 0
                for index, upload_result in enumerate(upload_results):
                    if index in file_mapping:
                        mapping_info = file_mapping[index]
                        file_path = mapping_info['file_path']
                        
                        if upload_result.get('success', False) and upload_result.get('url'):
                            # 上传成功，获取真实的文件URL (格式: file:///{resource_id})
                            file_url = upload_result['url']
                            
                            # 在Markdown中替换原始文件引用为文件URL
                            processed_markdown = self._replace_file_references_with_file_url(
                                processed_markdown, file_path, file_url, temp_dir
                            )
                            
                            # 从file_url中提取resource_id (去掉file:///)
                            resource_id = file_url.replace('file:///', '') if file_url.startswith('file:///') else upload_result.get('resource_id', file_url)
                            
                            # 创建文件资源信息
                            file_resource = {
                                'resource_id': resource_id,
                                'filename': upload_result.get('filename', file_path.name),
                                'format': file_path.suffix.lower()[1:] if file_path.suffix else 'bin',
                                'size': upload_result.get('size', len(mapping_info['file_data'])),
                                'doc_type': doc_type,
                                'url': file_url,
                                'upload_status': 'success',
                                **mapping_info['file_info']
                            }
                            file_resources.append(file_resource)
                            successful_uploads += 1
                            
                            self.logger.debug(f"文件上传成功: {file_path.name} -> {file_url}")
                        else:
                            # 上传失败
                            error_msg = upload_result.get('error', '上传失败')
                            self.logger.error(f"文件上传失败: {file_path.name}, 错误: {error_msg}")
                            
                            # 上传失败时，直接移除Markdown中的文件引用
                            processed_markdown = self._remove_file_references(
                                processed_markdown, file_path, temp_dir
                            )
                
                self.logger.info(f"批量上传完成 - 成功: {successful_uploads}/{len(upload_files)}")
                
            except Exception as e:
                self.logger.error(f"批量上传失败: {e}")
                # 上传失败时，移除所有文件引用
                for mapping_info in file_mapping.values():
                    processed_markdown = self._remove_file_references(
                        processed_markdown, mapping_info['file_path'], temp_dir
                    )
                file_resources = []
        else:
            # 没有存储客户端或未启用上传，移除所有文件引用
            self.logger.info("未启用批量上传或存储客户端不可用，移除文档中的文件引用")
            for mapping_info in file_mapping.values():
                processed_markdown = self._remove_file_references(
                    processed_markdown, mapping_info['file_path'], temp_dir
                )
            file_resources = []
        
        return processed_markdown, file_resources

    def _replace_file_references_with_file_url(self, markdown_content: str, file_path: Path, 
                                file_url: str, temp_dir: str) -> str:
        """
        在Markdown中替换文件引用为文件URL (格式: file:///{resource_id})
        
        Args:
            markdown_content: 原始Markdown内容
            file_path: 文件路径
            file_url: 文件URL (例如: file:///archive_file_20250619_filename.ext)
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
        
        # 直接使用返回的file_url，它已经是 file:///{resource_id} 格式
        new_file_ref = f"[{filename_only}]({file_url})"
        
        # 执行替换
        for old_ref in possible_refs:
            if old_ref.startswith('['):
                # 链接引用替换为新的格式
                markdown_content = markdown_content.replace(old_ref, new_file_ref)
            else:
                # 括号内的路径替换
                markdown_content = markdown_content.replace(old_ref, f"({file_url})")
        
        return markdown_content

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

    def get_upload_stats(self) -> Dict[str, Any]:
        """
        获取文件上传统计信息
        
        Returns:
            上传统计信息字典
        """
        return {
            **self.upload_stats,
            "upload_success_rate": (
                self.upload_stats['successful_uploads'] / max(self.upload_stats['total_uploads'], 1) * 100
                if self.upload_stats['total_uploads'] > 0 else 0
            )
        }

    def clear_cache(self):
        """清空文件缓存"""
        if self.cache:
            self.cache.clear()
            self.logger.info("压缩包文件缓存已清空")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取文件缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        try:
            if not self.cache:
                return {}
            
            total_files = 0
            total_size = 0
            file_type_stats = {}
            
            for key in self.cache:
                if isinstance(key, str) and key.startswith("archive_file:"):
                    total_files += 1
                    try:
                        cached_data = self.cache.get(key)
                        if cached_data:
                            size = cached_data.get('size', 0)
                            total_size += size
                            
                            # 按文件类型统计
                            file_type = cached_data.get('file_extension', 'unknown')
                            if file_type not in file_type_stats:
                                file_type_stats[file_type] = {'count': 0, 'size': 0}
                            file_type_stats[file_type]['count'] += 1
                            file_type_stats[file_type]['size'] += size
                    except:
                        pass
            
            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "file_type_stats": file_type_stats,
                "cache_directory": str(self.cache.directory) if hasattr(self.cache, 'directory') else None,
                "cache_size_limit": getattr(self.cache, 'size_limit', 0)
            }
            
        except Exception as e:
            self.logger.error(f"获取文件缓存统计失败: {e}")
            return {"error": str(e)}
