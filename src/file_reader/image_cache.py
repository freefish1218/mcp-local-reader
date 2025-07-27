"""
文档图片缓存管理器
统一管理所有文档类型的图片提取和缓存
"""

import os
import asyncio
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from diskcache import Cache

from .utils import get_logger


class ImageCacheManager:
    """统一的文档图片缓存管理器"""

    def __init__(self, storage_client=None):
        """
        初始化图片缓存管理器
        
        Args:
            storage_client: 存储客户端，用于上传图片到存储服务
        """
        self.logger = get_logger("image_cache")
        
        # 存储客户端，用于上传图片
        self.storage_client = storage_client
        
        # 图片上传配置
        self.upload_enabled = os.getenv("IMAGE_AUTO_UPLOAD_ENABLED", "true").lower() == "true"
        self.upload_timeout = int(os.getenv("IMAGE_UPLOAD_TIMEOUT", "60"))
        self.max_concurrent_uploads = int(os.getenv("IMAGE_UPLOAD_MAX_CONCURRENT", "3"))
        
        self.logger.info(f"图片上传配置 - 启用: {self.upload_enabled}, 超时: {self.upload_timeout}s, 最大并发: {self.max_concurrent_uploads}")
        
        # 初始化统一的图片缓存
        cache_root = os.getenv("CACHE_ROOT_DIR", "cache")
        image_cache_dir = os.path.join(cache_root, "document_images")
        cache_size_mb = int(os.getenv("IMAGE_FILE_CACHE_SIZE_MB", "1000"))
        cache_size_bytes = cache_size_mb * 1024 * 1024

        # 计算缓存过期时间
        expire_days = int(os.getenv("CACHE_EXPIRE_DAYS", "90"))
        expire_seconds = expire_days * 24 * 3600
                
        self.cache = Cache(image_cache_dir, size_limit=cache_size_bytes, expire=expire_seconds)
        self.logger.info(f"文档图片缓存初始化完成 - 目录: {image_cache_dir}, 大小: {cache_size_mb}MB, 有效期: {expire_days}天")
        
        # 统计信息
        self.upload_stats = {
            "total_uploads": 0,
            "successful_uploads": 0,
            "failed_uploads": 0,
            "upload_errors": []
        }

    def cache_document_images(self, image_files: List[Path], doc_info: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        批量缓存文档图片，并处理Markdown内容中的图片引用
        
        Args:
            image_files: 图片文件路径列表
            doc_info: 文档信息，包含文档类型、Markdown内容等
            
        Returns:
            (处理后的Markdown内容, 图片资源列表)
        """
        markdown_content = doc_info.get('markdown_content', '')
        doc_type = doc_info.get('doc_type', 'unknown')
        temp_image_dir = doc_info.get('temp_image_dir', '')
        
        image_resources = []
        processed_markdown = markdown_content
        
        # 准备上传的图片数据
        upload_images = []
        image_file_mapping = {}  # 索引 -> 图片文件信息的映射
        
        for image_file in image_files:
            try:
                # 读取图片数据
                with open(image_file, 'rb') as f:
                    image_data = f.read()
                
                if not image_data:
                    continue
                
                # 提取图片信息
                image_info = self._extract_image_info(image_file, image_data)
                
                # 准备上传的图片信息
                upload_image_info = {
                    'data': image_data,
                    'filename': image_file.name,
                    'content_type': None  # 让上传方法自动检测
                }
                upload_images.append(upload_image_info)
                
                # 保存映射关系
                image_file_mapping[len(upload_images) - 1] = {
                    'image_file': image_file,
                    'image_data': image_data,
                    'image_info': image_info
                }
                
                self.logger.debug(f"准备上传图片: {image_file.name}")
                
            except Exception as e:
                self.logger.warning(f"处理图片失败: {image_file.name}, 错误: {e}")
                continue
        
        # 批量上传图片到HTTP存储服务
        if self.upload_enabled and self.storage_client and hasattr(self.storage_client, 'upload_images_batch') and upload_images:
            try:
                self.logger.info(f"开始批量上传 {len(upload_images)} 个图片到HTTP存储服务")
                
                # 同步调用异步批量上传方法
                import asyncio
                import concurrent.futures
                
                # 在新线程中运行异步方法，避免事件循环冲突
                def run_async_upload():
                    # 创建新的事件循环
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self.storage_client.upload_images_batch(upload_images))
                    finally:
                        new_loop.close()
                
                # 在线程池中执行异步上传，增加并发度
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    future = executor.submit(run_async_upload)
                    upload_results = future.result(timeout=300)  # 5分钟超时
                
                self.logger.info(f"批量上传完成，收到 {len(upload_results)} 个结果")
                
                # 用真实的resource_id替换Markdown中的图片引用
                successful_uploads = 0
                for index, upload_result in enumerate(upload_results):
                    if index in image_file_mapping:
                        mapping_info = image_file_mapping[index]
                        image_file = mapping_info['image_file']
                        
                        if upload_result.get('success', False) and upload_result.get('url'):
                            # 上传成功，获取真实的文件URL (格式: file:///{resource_id})
                            file_url = upload_result['url']
                            
                            # 在Markdown中替换原始图片引用为文件URL
                            processed_markdown = self._replace_image_references_with_file_url(
                                processed_markdown, image_file, file_url, temp_image_dir
                            )
                            
                            # 从file_url中提取resource_id (去掉file:///)
                            resource_id = file_url.replace('file:///', '') if file_url.startswith('file:///') else upload_result.get('resource_id', file_url)
                            
                            # 创建图片资源信息
                            image_resource = {
                                'resource_id': resource_id,
                                'filename': upload_result.get('filename', image_file.name),
                                'format': image_file.suffix.lower()[1:] if image_file.suffix else 'png',
                                'size': upload_result.get('size', len(mapping_info['image_data'])),
                                'doc_type': doc_type,
                                'url': file_url,
                                'upload_status': 'success',
                                **mapping_info['image_info']
                            }
                            image_resources.append(image_resource)
                            successful_uploads += 1
                            
                            self.logger.debug(f"图片上传成功: {image_file.name} -> {file_url}")
                        else:
                            # 上传失败
                            error_msg = upload_result.get('error', '上传失败')
                            self.logger.error(f"图片上传失败: {image_file.name}, 错误: {error_msg}")
                            
                            # 上传失败时，直接移除Markdown中的图片引用
                            processed_markdown = self._remove_image_references(
                                processed_markdown, image_file, temp_image_dir
                            )
                
                self.logger.info(f"批量上传完成 - 成功: {successful_uploads}/{len(upload_images)}")
                
            except Exception as e:
                self.logger.error(f"批量上传失败: {e}")
                # 上传失败时，移除所有图片引用
                for mapping_info in image_file_mapping.values():
                    processed_markdown = self._remove_image_references(
                        processed_markdown, mapping_info['image_file'], temp_image_dir
                    )
                image_resources = []
        else:
            # 没有存储客户端或未启用上传，移除所有图片引用
            self.logger.info("未启用批量上传或存储客户端不可用，移除文档中的图片引用")
            for mapping_info in image_file_mapping.values():
                processed_markdown = self._remove_image_references(
                    processed_markdown, mapping_info['image_file'], temp_image_dir
                )
            image_resources = []
        
        return processed_markdown, image_resources
    




    def get_upload_stats(self) -> Dict[str, Any]:
        """
        获取图片上传统计信息
        
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





    def _replace_image_references_with_file_url(self, markdown_content: str, image_file: Path, 
                                file_url: str, temp_image_dir: str) -> str:
        """
        在Markdown中替换图片引用为文件URL (格式: file:///{resource_id})
        
        Args:
            markdown_content: 原始Markdown内容
            image_file: 图片文件路径
            file_url: 文件URL (例如: file:///20250618_92c0a018_9a2083d1c42b361e.png)
            temp_image_dir: 临时图片目录
            
        Returns:
            处理后的Markdown内容
        """
        # 获取可能的图片引用路径
        absolute_path = str(image_file.absolute())
        filename_only = image_file.name
        
        # 如果有临时目录，计算相对路径
        relative_path = filename_only
        if temp_image_dir:
            try:
                temp_path = Path(temp_image_dir)
                relative_path = str(image_file.relative_to(temp_path))
            except:
                pass
        
        # 定义所有可能的图片引用格式
        possible_refs = [
            f"![image]({filename_only})",
            f"![image]({relative_path})", 
            f"![image]({absolute_path})",
            f"![]({filename_only})",
            f"![]({relative_path})",
            f"![]({absolute_path})",
            f"({filename_only})",
            f"({relative_path})",
            f"({absolute_path})"
        ]
        
        # 直接使用返回的file_url，它已经是 file:///{resource_id} 格式
        new_image_ref = f"![]({file_url})"
        
        # 执行替换
        for old_ref in possible_refs:
            if old_ref.startswith('!['):
                # 图片引用替换为新的格式
                markdown_content = markdown_content.replace(old_ref, new_image_ref)
            else:
                # 括号内的路径替换
                markdown_content = markdown_content.replace(old_ref, f"({file_url})")
        
        return markdown_content

    def _remove_image_references(self, markdown_content: str, image_file: Path, temp_image_dir: str) -> str:
        """
        移除Markdown中的图片引用
        
        Args:
            markdown_content: 原始Markdown内容
            image_file: 图片文件路径
            temp_image_dir: 临时图片目录
            
        Returns:
            处理后的Markdown内容
        """
        # 获取可能的图片引用路径
        absolute_path = str(image_file.absolute())
        filename_only = image_file.name
        
        # 如果有临时目录，计算相对路径
        relative_path = filename_only
        if temp_image_dir:
            try:
                temp_path = Path(temp_image_dir)
                relative_path = str(image_file.relative_to(temp_path))
            except:
                pass
        
        # 定义所有可能的图片引用格式
        possible_refs = [
            f"![image]({filename_only})",
            f"![image]({relative_path})", 
            f"![image]({absolute_path})",
            f"![]({filename_only})",
            f"![]({relative_path})",
            f"![]({absolute_path})",
            f"({filename_only})",
            f"({relative_path})",
            f"({absolute_path})"
        ]
        
        # 执行移除
        for old_ref in possible_refs:
            markdown_content = markdown_content.replace(old_ref, '')
        
        return markdown_content

    def _extract_image_info(self, image_file: Path, image_data: bytes) -> Dict[str, Any]:
        """
        提取图片基本信息
        
        Args:
            image_file: 图片文件路径
            image_data: 图片数据
            
        Returns:
            图片信息字典
        """
        info = {}
        
        try:
            # 尝试使用PIL获取图片尺寸（如果可用）
            try:
                from PIL import Image
                import io
                
                with Image.open(io.BytesIO(image_data)) as img:
                    info['width'] = img.width
                    info['height'] = img.height
                    info['mode'] = img.mode
            except ImportError:
                # PIL不可用，使用基本信息
                pass
            except Exception as e:
                self.logger.debug(f"提取图片尺寸失败: {e}")
            
            # 文件基本信息
            info['file_size'] = len(image_data)
            info['created_from'] = 'document_extraction'
            
        except Exception as e:
            self.logger.warning(f"提取图片信息失败: {e}")
        
        return info



    def clear_cache(self):
        """清空图片缓存"""
        if self.cache:
            self.cache.clear()
            self.logger.info("文档图片缓存已清空")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取图片缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        try:
            if not self.cache:
                return {}
            
            total_images = 0
            total_size = 0
            doc_type_stats = {}
            
            for key in self.cache:
                if isinstance(key, str) and key.startswith("doc_image:"):
                    total_images += 1
                    try:
                        cached_data = self.cache.get(key)
                        if cached_data:
                            size = cached_data.get('size', 0)
                            total_size += size
                            
                            # 按文档类型统计
                            doc_type = cached_data.get('doc_type', 'unknown')
                            if doc_type not in doc_type_stats:
                                doc_type_stats[doc_type] = {'count': 0, 'size': 0}
                            doc_type_stats[doc_type]['count'] += 1
                            doc_type_stats[doc_type]['size'] += size
                    except:
                        pass
            
            return {
                "total_images": total_images,
                "total_size_bytes": total_size,
                "doc_type_stats": doc_type_stats,
                "cache_directory": str(self.cache.directory) if hasattr(self.cache, 'directory') else None,
                "cache_size_limit": getattr(self.cache, 'size_limit', 0)
            }
            
        except Exception as e:
            self.logger.error(f"获取图片缓存统计失败: {e}")
            return {"error": str(e)} 