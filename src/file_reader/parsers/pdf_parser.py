"""
PDF文档解析器
使用PyMuPDF4LLM进行PDF到Markdown的转换，并支持图片提取和缓存
"""

import os
import tempfile
import shutil

import pymupdf4llm

from .base import BaseParser
from ..models import ParseResult


class PDFParser(BaseParser):
    """PDF文档解析器，使用PyMuPDF4LLM解析为Markdown格式，支持图片提取和缓存"""

    def __init__(self):
        """初始化PDF解析器"""
        super().__init__()
        self.parser_version = "2.1"  # 更新解析器版本

    def _parse_content(self, content: bytes, file_extension: str = None) -> ParseResult:
        """
        解析PDF文档
        
        Args:
            content: PDF文件内容字节数据
            file_extension: 文件扩展名
            
        Returns:
            解析结果对象
        """
        if file_extension and file_extension.lower() != '.pdf':
            self.logger.warning(f"文件扩展名不匹配PDF: {file_extension}")
        
        try:
            self.logger.info("使用PyMuPDF4LLM解析PDF为Markdown")
            return self._parse_with_pymupdf4llm(content)
                
        except Exception as e:
            self.logger.error(f"解析PDF文档失败: {e}")
            return self._create_error_result(f"解析PDF文档失败: {e}")

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