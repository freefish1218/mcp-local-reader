"""
文档图片缓存管理器
使用统一缓存系统管理所有文档类型的图片提取和缓存
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from .cache_manager import cache_manager
from .utils import get_logger


class ImageCacheManager:
    """统一的文档图片缓存管理器"""

    def __init__(self):
        """
        初始化图片缓存管理器
        """
        self.logger = get_logger("image_cache")
        self.cache_mgr = cache_manager
        self.namespace = "image"
        
        # 计算缓存过期时间
        expire_days = int(os.getenv("CACHE_EXPIRE_DAYS", "30"))
        self.expire_seconds = expire_days * 24 * 3600
        
        self.logger.info(f"文档图片缓存初始化完成 - 使用统一缓存系统, 有效期: {expire_days}天")

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
        
        # 本地文件读取模式：直接移除图片引用，不进行上传处理
        self.logger.info(f"本地文件模式：移除文档中的 {len(image_files)} 个图片引用")
        
        for image_file in image_files:
            try:
                # 移除Markdown中的图片引用
                processed_markdown = self._remove_image_references(
                    processed_markdown, image_file, temp_image_dir
                )
                self.logger.debug(f"移除图片引用: {image_file.name}")
                
            except Exception as e:
                self.logger.warning(f"处理图片失败: {image_file.name}, 错误: {e}")
                continue
        
        return processed_markdown, image_resources
    
    def _remove_image_references(self, markdown_content: str, image_file: Path, temp_image_dir: str = '') -> str:
        """
        从Markdown内容中移除指定图片的引用
        
        Args:
            markdown_content: 原始Markdown内容
            image_file: 要移除的图片文件路径
            temp_image_dir: 临时图片目录路径
            
        Returns:
            移除图片引用后的Markdown内容
        """
        import re
        
        # 构建可能的图片引用模式
        patterns_to_remove = []
        
        # 基于文件名的模式
        filename = image_file.name
        patterns_to_remove.extend([
            rf'!\[([^\]]*)\]\([^)]*{re.escape(filename)}[^)]*\)',  # ![alt](path/filename)
            rf'!\[[^\]]*\]\([^)]*{re.escape(filename.replace(" ", "%20"))}[^)]*\)',  # URL编码的文件名
        ])
        
        # 基于临时目录的模式（如果提供了临时目录）
        if temp_image_dir:
            temp_dir_name = Path(temp_image_dir).name
            patterns_to_remove.extend([
                rf'!\[([^\]]*)\]\([^)]*{re.escape(temp_dir_name)}[^)]*{re.escape(filename)}[^)]*\)',
                rf'!\[([^\]]*)\]\([^)]*/{re.escape(filename)}[^)]*\)',
            ])
        
        # 应用所有模式移除图片引用
        processed_content = markdown_content
        for pattern in patterns_to_remove:
            processed_content = re.sub(pattern, '', processed_content)
        
        # 清理多余的空行
        processed_content = re.sub(r'\n{3,}', '\n\n', processed_content)
        
        return processed_content

    def _extract_image_info(self, image_file: Path, image_data: bytes) -> Dict[str, Any]:
        """
        提取图片基本信息
        
        Args:
            image_file: 图片文件路径
            image_data: 图片数据
            
        Returns:
            图片信息字典
        """
        info = {
            'filename': image_file.name,
            'size': len(image_data),
            'content_type': self._detect_content_type(image_file),
            'width': None,
            'height': None
        }
        
        # 尝试获取图片尺寸（可选功能）
        try:
            from PIL import Image
            import io
            
            with Image.open(io.BytesIO(image_data)) as img:
                info['width'] = img.width
                info['height'] = img.height
        except Exception:
            # 如果PIL不可用或图片格式不支持，跳过尺寸信息
            pass
        
        return info

    def _detect_content_type(self, image_file: Path) -> str:
        """
        根据文件扩展名检测内容类型
        
        Args:
            image_file: 图片文件路径
            
        Returns:
            MIME类型字符串
        """
        extension = image_file.suffix.lower()
        content_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
        }
        return content_type_map.get(extension, 'image/png')

    def save_image(self, image_key: str, image_data: bytes, metadata: Dict[str, Any] = None) -> bool:
        """
        保存图片到缓存
        
        Args:
            image_key: 图片缓存键
            image_data: 图片数据
            metadata: 可选的元数据
            
        Returns:
            是否保存成功
        """
        try:
            cache_value = {
                'data': image_data,
                'timestamp': time.time(),
                'metadata': metadata or {}
            }
            
            self.cache_mgr.set(self.namespace, image_key, cache_value, expire=self.expire_seconds)
            self.logger.debug(f"图片已缓存: {image_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"缓存图片失败: {image_key}, 错误: {e}")
            return False

    def get_image(self, image_key: str) -> Tuple[Optional[bytes], Optional[Dict[str, Any]]]:
        """
        从缓存获取图片
        
        Args:
            image_key: 图片缓存键
            
        Returns:
            (图片数据, 元数据) 的元组，如果不存在则返回 (None, None)
        """
        try:
            cache_value = self.cache_mgr.get(self.namespace, image_key)
            if cache_value:
                return cache_value.get('data'), cache_value.get('metadata', {})
            return None, None
            
        except Exception as e:
            self.logger.error(f"获取缓存图片失败: {image_key}, 错误: {e}")
            return None, None

    def delete_image(self, image_key: str) -> bool:
        """
        从缓存删除图片
        
        Args:
            image_key: 图片缓存键
            
        Returns:
            是否删除成功
        """
        try:
            if self.cache_mgr.delete(self.namespace, image_key):
                self.logger.debug(f"已删除缓存图片: {image_key}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"删除缓存图片失败: {image_key}, 错误: {e}")
            return False

    def clear_cache(self) -> bool:
        """
        清空所有缓存
        
        Returns:
            是否清空成功
        """
        try:
            self.cache_mgr.clear_namespace(self.namespace)
            self.logger.info("图片缓存已清空")
            return True
            
        except Exception as e:
            self.logger.error(f"清空图片缓存失败: {e}")
            return False


# 全局单例实例
_image_cache_manager = None

def get_image_cache_manager():
    """获取图片缓存管理器的全局单例实例"""
    global _image_cache_manager
    if _image_cache_manager is None:
        _image_cache_manager = ImageCacheManager()
    return _image_cache_manager