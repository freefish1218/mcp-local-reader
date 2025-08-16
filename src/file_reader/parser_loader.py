"""
解析器懒加载管理器
按需加载解析器，减少启动时的资源消耗
"""

import os
import importlib
from typing import Dict, Optional, Type
from pathlib import Path

from .utils import get_logger
from .parsers.base import BaseParser


class LazyParserLoader:
    """懒加载解析器管理器"""
    
    def __init__(self):
        """初始化解析器加载器"""
        self.logger = get_logger("parser_loader")
        self._parsers: Dict[str, BaseParser] = {}
        self._parser_classes: Dict[str, Type[BaseParser]] = {}
        
        # 解析器映射配置
        self.parser_mapping = {
            # PDF
            '.pdf': ('parsers.pdf_parser', 'PDFParser'),
            
            # Office文档
            '.doc': ('parsers.office_parser', 'OfficeParser'),
            '.docx': ('parsers.office_parser', 'OfficeParser'),
            '.xls': ('parsers.office_parser', 'OfficeParser'),
            '.xlsx': ('parsers.office_parser', 'OfficeParser'),
            '.ppt': ('parsers.office_parser', 'OfficeParser'),
            '.pptx': ('parsers.office_parser', 'OfficeParser'),
            '.rtf': ('parsers.office_parser', 'OfficeParser'),
            
            # OpenDocument
            '.odt': ('parsers.office_parser', 'OfficeParser'),
            '.ods': ('parsers.office_parser', 'OfficeParser'),
            '.odp': ('parsers.office_parser', 'OfficeParser'),
            
            # 文本文件
            '.txt': ('parsers.text_parser', 'TextParser'),
            '.md': ('parsers.text_parser', 'TextParser'),
            '.markdown': ('parsers.text_parser', 'TextParser'),
            '.json': ('parsers.text_parser', 'TextParser'),
            '.csv': ('parsers.text_parser', 'TextParser'),
            '.epub': ('parsers.text_parser', 'TextParser'),
            
            # 图像文件
            '.jpg': ('parsers.image_parser', 'ImageParser'),
            '.jpeg': ('parsers.image_parser', 'ImageParser'),
            '.png': ('parsers.image_parser', 'ImageParser'),
            '.gif': ('parsers.image_parser', 'ImageParser'),
            '.bmp': ('parsers.image_parser', 'ImageParser'),
            '.webp': ('parsers.image_parser', 'ImageParser'),
            '.tiff': ('parsers.image_parser', 'ImageParser'),
            
            # 压缩文件
            '.zip': ('parsers.archive_parser', 'ArchiveParser'),
            '.rar': ('parsers.archive_parser', 'ArchiveParser'),
            '.7z': ('parsers.archive_parser', 'ArchiveParser'),
            '.tar': ('parsers.archive_parser', 'ArchiveParser'),
            '.gz': ('parsers.archive_parser', 'ArchiveParser'),
            '.tar.gz': ('parsers.archive_parser', 'ArchiveParser'),
            '.tgz': ('parsers.archive_parser', 'ArchiveParser'),
            '.tar.bz2': ('parsers.archive_parser', 'ArchiveParser'),
            '.tbz2': ('parsers.archive_parser', 'ArchiveParser'),
        }
        
        # 检查哪些解析器可用（基于已安装的依赖）
        self.available_parsers = self._check_available_parsers()
        self.logger.info(f"可用解析器: {list(self.available_parsers)}")
    
    def _check_available_parsers(self) -> set:
        """检查哪些解析器可用"""
        available = set()
        
        # 始终可用的基础解析器
        available.add('TextParser')
        
        # 检查PDF支持
        try:
            import pymupdf4llm
            available.add('PDFParser')
        except ImportError:
            self.logger.debug("PDFParser不可用: 缺少pymupdf4llm")
        
        # 检查Office支持
        try:
            import openpyxl
            import odfpy
            available.add('OfficeParser')
        except ImportError:
            self.logger.debug("OfficeParser部分功能不可用")
        
        # 检查图像OCR支持
        try:
            from PIL import Image
            available.add('ImageParser')
            # 检查OCR支持
            try:
                import langchain_openai
                self.logger.debug("ImageParser支持OCR功能")
            except ImportError:
                self.logger.debug("ImageParser不支持OCR: 缺少langchain_openai")
        except ImportError:
            self.logger.debug("ImageParser不可用: 缺少Pillow")
        
        # 检查压缩文件支持
        try:
            import zipfile
            import tarfile
            available.add('ArchiveParser')
        except ImportError:
            self.logger.debug("ArchiveParser不可用")
        
        return available
    
    def get_parser_for_file(self, file_path: str) -> Optional[BaseParser]:
        """
        根据文件路径获取合适的解析器
        
        Args:
            file_path: 文件路径
            
        Returns:
            合适的解析器实例，如果没有找到返回None
        """
        # 获取文件扩展名
        file_ext = self._get_file_extension(file_path).lower()
        
        # 查找对应的解析器配置
        parser_config = self.parser_mapping.get(file_ext)
        if not parser_config:
            self.logger.debug(f"未找到扩展名 {file_ext} 的解析器")
            return None
        
        module_path, class_name = parser_config
        
        # 检查解析器是否可用
        if class_name not in self.available_parsers:
            self.logger.warning(f"解析器 {class_name} 不可用（缺少依赖）")
            return None
        
        # 检查是否已加载
        if class_name in self._parsers:
            return self._parsers[class_name]
        
        # 懒加载解析器
        try:
            parser = self._load_parser(module_path, class_name)
            self._parsers[class_name] = parser
            return parser
        except Exception as e:
            self.logger.error(f"加载解析器 {class_name} 失败: {e}")
            return None
    
    def _load_parser(self, module_path: str, class_name: str) -> BaseParser:
        """
        动态加载解析器
        
        Args:
            module_path: 模块路径
            class_name: 类名
            
        Returns:
            解析器实例
        """
        self.logger.info(f"加载解析器: {class_name}")
        
        # 动态导入模块
        full_module_path = f"src.file_reader.{module_path}"
        module = importlib.import_module(full_module_path)
        
        # 获取解析器类
        parser_class = getattr(module, class_name)
        
        # 创建实例
        parser_instance = parser_class()
        
        self.logger.info(f"解析器 {class_name} 加载成功")
        return parser_instance
    
    def _get_file_extension(self, file_path: str) -> str:
        """获取文件扩展名"""
        path = Path(file_path)
        
        # 处理双扩展名（如 .tar.gz）
        if path.suffixes and len(path.suffixes) >= 2:
            double_ext = ''.join(path.suffixes[-2:])
            if double_ext in self.parser_mapping:
                return double_ext
        
        # 返回单扩展名
        return path.suffix if path.suffix else ''
    
    def is_supported(self, file_path: str) -> bool:
        """
        检查文件是否支持解析
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否支持
        """
        file_ext = self._get_file_extension(file_path).lower()
        if file_ext not in self.parser_mapping:
            return False
        
        _, class_name = self.parser_mapping[file_ext]
        return class_name in self.available_parsers
    
    def get_supported_extensions(self) -> list:
        """获取所有支持的文件扩展名"""
        supported = []
        for ext, (_, class_name) in self.parser_mapping.items():
            if class_name in self.available_parsers:
                supported.append(ext)
        return sorted(supported)
    
    def cleanup(self):
        """清理所有已加载的解析器"""
        for parser_name, parser in self._parsers.items():
            try:
                # 如果解析器有清理方法，调用它
                if hasattr(parser, 'cleanup'):
                    parser.cleanup()
            except Exception as e:
                self.logger.error(f"清理解析器 {parser_name} 失败: {e}")
        
        self._parsers.clear()
        self.logger.info("所有解析器已清理")


# 全局解析器加载器实例
parser_loader = LazyParserLoader()