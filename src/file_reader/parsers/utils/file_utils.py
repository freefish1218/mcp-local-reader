"""
文件处理工具函数
提供临时文件管理、格式检查等通用功能
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any

from ...utils import get_logger
from ...models import ParseResult


class FileManager:
    """文件管理工具类"""

    def __init__(self):
        """初始化文件管理器"""
        self.logger = get_logger("file_manager")

    def save_temp_file(self, content: bytes, file_extension: str) -> Path:
        """
        保存内容到临时文件
        
        Args:
            content: 文件内容字节数据
            file_extension: 文件扩展名
            
        Returns:
            临时文件路径
        """
        temp_file = tempfile.NamedTemporaryFile(
            suffix=file_extension, 
            delete=False
        )
        # 确保临时文件权限为600（仅所有者可读写）
        os.chmod(temp_file.name, 0o600)
        temp_file.write(content)
        temp_file.close()
        
        return Path(temp_file.name)

    def cleanup_temp_file(self, file_path: Path):
        """
        清理临时文件
        
        Args:
            file_path: 文件路径
        """
        try:
            if file_path.exists():
                file_path.unlink()
                self.logger.debug(f"清理临时文件: {file_path}")
        except Exception as e:
            self.logger.warning(f"清理临时文件失败: {file_path}, 错误: {e}")

    def cleanup_temp_directory(self, dir_path: str):
        """
        清理临时目录
        
        Args:
            dir_path: 目录路径
        """
        try:
            if dir_path and Path(dir_path).exists():
                import shutil
                shutil.rmtree(dir_path, ignore_errors=True)
                self.logger.debug(f"清理临时目录: {dir_path}")
        except Exception as e:
            self.logger.warning(f"清理临时目录失败: {dir_path}, 错误: {e}")


class FormatChecker:
    """文件格式检查工具"""

    @staticmethod
    def is_supported_office_format(file_extension: str) -> bool:
        """
        检查是否为支持的Office文档格式
        
        Args:
            file_extension: 文件扩展名
            
        Returns:
            是否支持
        """
        supported_extensions = [
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', 
            '.odt', '.ods', '.odp', '.rtf', '.csv', '.epub'
        ]
        return file_extension.lower() in supported_extensions

    @staticmethod
    def is_old_format(file_extension: str) -> bool:
        """
        检查是否为需要转换的旧格式
        
        Args:
            file_extension: 文件扩展名
            
        Returns:
            是否为旧格式
        """
        return file_extension.lower() in ['.doc', '.xls', '.ppt']

    @staticmethod
    def needs_pandoc(file_extension: str) -> bool:
        """
        检查是否需要使用pandoc转换
        
        Args:
            file_extension: 文件扩展名
            
        Returns:
            是否需要pandoc
        """
        pandoc_formats = ['.docx', '.odt', '.rtf', '.csv', '.epub']
        return file_extension.lower() in pandoc_formats

    @staticmethod
    def needs_special_parser(file_extension: str) -> bool:
        """
        检查是否需要特殊解析器
        
        Args:
            file_extension: 文件扩展名
            
        Returns:
            是否需要特殊解析器
        """
        special_formats = ['.xlsx', '.pptx', '.ods', '.odp']
        return file_extension.lower() in special_formats


class ResultBuilder:
    """解析结果构建器"""

    @staticmethod
    def create_success_result(content: str, doc_type: str, metadata: Dict[str, Any]) -> ParseResult:
        """
        创建成功的解析结果
        
        Args:
            content: 解析内容
            doc_type: 文档类型
            metadata: 元数据
            
        Returns:
            解析结果对象
        """
        return ParseResult(
            success=True,
            content=content,
            doc_type=doc_type,
            metadata=metadata,
            error=None
        )

    @staticmethod
    def create_error_result(error_message: str) -> ParseResult:
        """
        创建错误的解析结果
        
        Args:
            error_message: 错误信息
            
        Returns:
            解析结果对象
        """
        return ParseResult(
            success=False,
            content="",
            doc_type="",
            metadata={},
            error=error_message
        ) 