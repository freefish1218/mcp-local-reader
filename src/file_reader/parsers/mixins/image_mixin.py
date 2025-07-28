"""
图片处理混入类
为解析器提供统一的图片处理能力
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple

from ...image_cache import ImageCacheManager


class ImageProcessingMixin:
    """图片处理混入类，为解析器提供图片缓存和处理能力"""
    
    def __init__(self):
        """
        初始化图片处理混入
        """
        # 获取或创建图片缓存管理器
        if not hasattr(self, '_image_cache_manager'):
            from ...image_cache import get_image_cache_manager
            self._image_cache_manager = get_image_cache_manager()
    
    
    def process_document_images(self, markdown_content: str, temp_image_dir: str, 
                              doc_type: str, source_file_path: str = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        处理文档中的图片，统一的图片处理接口
        
        Args:
            markdown_content: 原始Markdown内容
            temp_image_dir: 临时图片目录
            doc_type: 文档类型 (pdf, docx, pptx, etc.)
            source_file_path: 原始文档文件路径（可选）
            
        Returns:
            (处理后的Markdown内容, 图片资源列表)
        """
        # 扫描临时目录中的图片文件
        temp_image_path = Path(temp_image_dir)
        if not temp_image_path.exists():
            return markdown_content, []
        
        # 收集图片文件
        image_files = []
        for image_file in temp_image_path.glob("*"):
            if image_file.is_file() and image_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
                image_files.append(image_file)
        
        if not image_files:
            return markdown_content, []
        
        # 构建文档信息
        doc_info = {
            'markdown_content': markdown_content,
            'doc_type': doc_type,
            'temp_image_dir': temp_image_dir,
            'source_file_path': source_file_path
        }
        
        # 使用图片缓存管理器处理图片
        return self._image_cache_manager.cache_document_images(image_files, doc_info)
    

    
    
    def clear_image_cache(self):
        """清空图片缓存"""
        self._image_cache_manager.clear_cache() 