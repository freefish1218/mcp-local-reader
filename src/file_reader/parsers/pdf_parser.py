"""
PDF文档解析器
使用PyMuPDF4LLM进行PDF到Markdown的转换，并支持图片提取和缓存
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

import pymupdf4llm

from .base import BaseParser
from ..models import ParseResult


class PDFParser(BaseParser):
    """PDF文档解析器，使用PyMuPDF4LLM解析为Markdown格式，支持图片提取和缓存"""

    def __init__(self):
        """初始化PDF解析器"""
        super().__init__()
        self.parser_version = "2.2"  # 更新解析器版本
        self.pandoc_converter = PandocConverter()

    def _parse_content(self, content: bytes, file_extension: str = None) -> ParseResult:
        """
        解析PDF文档，采用两步策略：
        1. 快速解析 (PyMuPDF4LLM)
        2. 深度解析 (Pandoc)
        
        Args:
            content: PDF文件内容字节数据
            file_extension: 文件扩展名
            
        Returns:
            解析结果对象
        """
        if file_extension and file_extension.lower() != '.pdf':
            self.logger.warning(f"文件扩展名不匹配PDF: {file_extension}")

        # 第一步：使用PyMuPDF4LLM进行快速解析
        self.logger.info("第一步：使用PyMuPDF4LLM解析PDF...")
        pymupdf_result = self._parse_with_pymupdf4llm(content)

        # 检查快速解析的结果
        # 如果成功并且内容不为空，直接返回
        if pymupdf_result.success and pymupdf_result.content and pymupdf_result.content.strip():
            self.logger.info("PyMuPDF4LLM解析成功并返回有效内容。")
            return pymupdf_result

        # 如果PyMuPDF4LLM失败或内容为空，则启动第二步
        self.logger.warning("PyMuPDF4LLM未能提取有效内容，启动第二步：使用Pandoc进行深度解析。")

        # 第二步：使用Pandoc进行深度解析
        try:
            pandoc_result = self._parse_with_pandoc(content)
            if pandoc_result.success and pandoc_result.content and pandoc_result.content.strip():
                self.logger.info("Pandoc解析成功并返回有效内容。")
                return pandoc_result
            else:
                # 如果Pandoc也失败了，返回最初PyMuPDF的失败结果
                self.logger.error("Pandoc也未能提取有效内容，返回初始错误。")
                return pymupdf_result
        except Exception as e:
            self.logger.error(f"Pandoc解析过程中发生异常: {e}")
            # 如果Pandoc执行异常，同样返回最初PyMuPDF的失败结果
            return pymupdf_result

    def _parse_with_pandoc(self, content: bytes) -> ParseResult:
        """
        使用Pandoc作为后备方案解析PDF。

        Args:
            content: PDF文件内容的字节数据。

        Returns:
            解析结果对象。
        """
        temp_pdf_path = None
        try:
            # Pandoc需要一个文件路径，所以我们创建一个临时文件
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                temp_pdf.write(content)
                temp_pdf_path = temp_pdf.name

            self.logger.info(f"开始Pandoc解析: {temp_pdf_path}")
            
            # Pandoc转换PDF到Markdown
            # 注意：Pandoc处理PDF时不需要指定--from格式
            markdown_content = self.pandoc_converter.convert_to_markdown(
                file_path=temp_pdf_path,
                file_extension=".pdf" 
            )

            if not markdown_content or not markdown_content.strip():
                return self._create_error_result("Pandoc解析结果为空")

            # 对于从Pandoc获取的内容，我们目前不处理图片或复杂元数据
            metadata = {
                "parser": "pandoc",
                "format": "markdown"
            }
            
            self.logger.info(f"Pandoc解析PDF成功，内容长度: {len(markdown_content)}")
            return self._create_success_result(markdown_content, "pdf_markdown_pandoc", metadata)

        except Exception as e:
            self.logger.error(f"Pandoc解析PDF失败: {e}")
            return self._create_error_result(f"Pandoc解析PDF失败: {e}")
        finally:
            # 清理临时文件
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)

    def _parse_with_pymupdf4llm(self, content: bytes) -> ParseResult:
        """
        使用PyMuPDF4LLM解析PDF
        
        Args:
            content: PDF文件内容字节数据
            
        Returns:
            解析结果对象
        """
        temp_pdf_path = None
        temp_image_dir = None
        
        try:
            # 创建临时PDF文件
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf.write(content)
                temp_pdf_path = temp_pdf.name
            
            # 创建临时图片目录
            temp_image_dir = tempfile.mkdtemp(prefix="pdf_images_")
            
            self.logger.info(f"开始PyMuPDF4LLM解析: {temp_pdf_path}")
            
            # 使用PyMuPDF4LLM解析PDF为Markdown，并提取图片
            markdown_data = pymupdf4llm.to_markdown(
                doc=temp_pdf_path,
                page_chunks=True,  # 获取分页数据和元数据
                write_images=True,  # 提取图片
                image_path=temp_image_dir,  # 图片保存路径
                image_format="png",  # 图片格式
                dpi=150,  # 图片分辨率
                force_text=True,  # 图片中的文本也显示在Markdown中
                show_progress=True  # 显示处理进度，改善用户体验
            )
            
            if not markdown_data:
                return self._create_error_result("PDF解析结果为空")
            
            # 合并所有页面的Markdown内容
            markdown_content = ""
            total_pages = len(markdown_data)
            
            for page_idx, page_data in enumerate(markdown_data):
                if isinstance(page_data, dict) and 'text' in page_data:
                    page_text = page_data['text']
                    if page_text and page_text.strip():
                        markdown_content += f"# 第 {page_idx + 1} 页\n\n{page_text}\n\n"
                elif isinstance(page_data, str):
                    # 如果直接返回字符串而不是字典
                    markdown_content += f"# 第 {page_idx + 1} 页\n\n{page_data}\n\n"
            
            if not markdown_content.strip():
                return self._create_error_result("PDF文档无有效内容")
            
            # 使用基类的图片处理能力处理提取的图片
            processed_markdown, image_resources = self.process_document_images(
                markdown_content=markdown_content,
                temp_image_dir=temp_image_dir,
                doc_type="pdf",
                source_file_path=temp_pdf_path
            )
            
            # 创建元数据
            metadata = {
                "total_pages": total_pages,
                "parser": "pymupdf4llm",
                "format": "markdown",
                "image_count": len(image_resources),
                "image_resources": image_resources
            }
            
            # 添加原始元数据（如果可用）
            if isinstance(markdown_data[0], dict) and 'metadata' in markdown_data[0]:
                original_metadata = markdown_data[0]['metadata']
                metadata.update(original_metadata)
            
            self.logger.info(f"PDF解析成功 - 页数: {total_pages}, 图片: {len(image_resources)}, 内容长度: {len(processed_markdown)}")
            return self._create_success_result(processed_markdown, "pdf_markdown", metadata)
            
        finally:
            # 清理临时文件
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            if temp_image_dir and os.path.exists(temp_image_dir):
                shutil.rmtree(temp_image_dir, ignore_errors=True) 