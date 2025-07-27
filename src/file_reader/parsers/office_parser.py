"""
Office文档解析器 - 混合策略版本
支持Word、Excel、PowerPoint、OpenDocument等Office文档的解析
统一输出 Markdown 格式，采用最佳工具组合：
- Word/ODT/RTF/CSV/EPUB: pandoc 转换
- Excel: pandas + excel解析器
- PowerPoint: python-pptx + 自定义解析器
- 旧格式: LibreOffice 转换后再处理
"""

import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from .base import BaseParser
from .mixins.image_mixin import ImageProcessingMixin
from ..models import ParseResult
from .utils.document_converter import DocumentConverter
from .utils.pandoc_converter import PandocConverter
from .utils.office_specific_parsers import ExcelParser, PowerPointParser
from .utils.file_utils import FileManager, FormatChecker, ResultBuilder


class OfficeParser(BaseParser, ImageProcessingMixin):
    """Office文档解析器，混合策略输出Markdown格式"""

    def __init__(self, storage_client=None):
        """初始化Office解析器"""
        BaseParser.__init__(self, storage_client=storage_client)
        ImageProcessingMixin.__init__(self, storage_client=storage_client)
        self.parser_version = "2.0"  # 更新解析器版本
        
        # 初始化工具类
        self.document_converter = DocumentConverter()
        self.pandoc_converter = PandocConverter()
        self.excel_parser = ExcelParser()
        self.powerpoint_parser = PowerPointParser()
        self.file_manager = FileManager()
        self.format_checker = FormatChecker()
        self.result_builder = ResultBuilder()

    def _parse_content(self, content: bytes, file_extension: str = None) -> ParseResult:
        """
        解析Office文档，返回Markdown格式内容
        
        Args:
            content: 文件内容字节数据
            file_extension: 文件扩展名
            
        Returns:
            解析结果对象，内容为Markdown格式
        """
        if not file_extension:
            return self.result_builder.create_error_result("缺少文件扩展名")
        
        file_extension = file_extension.lower()
        
        # 检查是否支持该文件类型
        if not self.format_checker.is_supported_office_format(file_extension):
            return self.result_builder.create_error_result(f"不支持的Office文档类型: {file_extension}")
        
        temp_file = None
        converted_file = None
        temp_image_dir = None
        
        try:
            self.logger.info(f"开始解析Office文档: {file_extension}")
            
            # 保存原始文件为临时文件
            temp_file = self.file_manager.save_temp_file(content, file_extension)
            
            # 对于旧格式，先转换为新格式
            if self.format_checker.is_old_format(file_extension):
                self.logger.info(f"检测到旧格式 {file_extension}，使用LibreOffice转换")
                converted_file = self.document_converter.convert_old_format_with_libreoffice(str(temp_file), file_extension)
                if not converted_file:
                    return self.result_builder.create_error_result(f"无法转换旧格式文件: {file_extension}")
                # 更新文件扩展名
                file_extension = self.document_converter.get_target_format(file_extension)
                input_file = converted_file
            else:
                input_file = str(temp_file)
            
            # 创建临时图片目录
            temp_image_dir = tempfile.mkdtemp(prefix=f"office_{file_extension[1:]}_images_")
            
            # 根据文件类型选择最佳解析策略，同时提取图片
            if self.format_checker.needs_pandoc(file_extension):
                # 使用 pandoc 解析（支持图片提取）
                markdown_content = self.pandoc_converter.convert_to_markdown(input_file, file_extension, temp_image_dir)
                parser_info = "pandoc"
            elif file_extension == '.xlsx':
                # 使用 Excel 专用解析器
                markdown_content = self.excel_parser.parse_to_markdown(input_file)
                self.excel_parser.extract_images(input_file, temp_image_dir)
                parser_info = "pandas+excel_parser"
            elif file_extension == '.pptx':
                # 使用 PowerPoint 专用解析器
                markdown_content = self.powerpoint_parser.parse_to_markdown(input_file, temp_image_dir)
                parser_info = "python-pptx+powerpoint_parser"
            elif file_extension in ['.ods', '.odp']:
                # OpenDocument 电子表格和演示文稿，使用原有方法
                if file_extension == '.ods':
                    return self._parse_ods_legacy(content, file_extension)
                else:  # .odp
                    return self._parse_odp_legacy(content, file_extension)
            else:
                return self.result_builder.create_error_result(f"内部错误：未处理的文件类型 {file_extension}")
            
            if not markdown_content:
                return self.result_builder.create_error_result("文档解析失败，内容为空")
            
            # 处理提取的图片
            processed_markdown, image_resources = self.process_document_images(
                markdown_content=markdown_content,
                temp_image_dir=temp_image_dir,
                doc_type=file_extension[1:],  # 去掉点号
                source_file_path=input_file
            )
            
            # 创建元数据
            metadata = {
                "parser": parser_info,
                "original_format": file_extension,
                "output_format": "markdown",
                "conversion_tool": f"libreoffice+{parser_info}" if converted_file else parser_info,
                "image_count": len(image_resources),
                "image_resources": image_resources
            }
            
            self.logger.info(f"Office文档解析成功: {file_extension} -> Markdown ({parser_info}), 图片: {len(image_resources)}")
            return self.result_builder.create_success_result(processed_markdown, file_extension.replace('.', ''), metadata)
            
        except Exception as e:
            self.logger.error(f"解析Office文档失败: {e}")
            return self.result_builder.create_error_result(f"解析Office文档失败: {e}")
        finally:
            # 清理临时文件
            if temp_file:
                self.file_manager.cleanup_temp_file(temp_file)
            if converted_file:
                self.file_manager.cleanup_temp_file(Path(converted_file))
            if temp_image_dir:
                self.file_manager.cleanup_temp_directory(temp_image_dir)



    def _parse_ods_legacy(self, content: bytes, file_extension: str) -> ParseResult:
        """使用原有方法解析ODS文件"""
        temp_file = None
        try:
            self.logger.info("使用odfpy解析ODS文件")
            temp_file = self.file_manager.save_temp_file(content, file_extension)
            
            try:
                from odf.opendocument import load
                from odf.table import Table, TableRow, TableCell
                from odf.teletype import extractText
                
                doc = load(str(temp_file))
                tables = doc.getElementsByType(Table)
                markdown_parts = []
                
                markdown_parts.append("# OpenDocument 电子表格")
                markdown_parts.append("")
                
                for table_idx, table in enumerate(tables):
                    sheet_name = table.getAttribute('name') or f"工作表{table_idx + 1}"
                    markdown_parts.append(f"## {sheet_name}")
                    markdown_parts.append("")
                    
                    # 提取表格数据
                    rows = table.getElementsByType(TableRow)
                    table_data = []
                    
                    for row in rows:
                        cells = row.getElementsByType(TableCell)
                        row_data = []
                        
                        for cell in cells:
                            cell_text = extractText(cell).strip()
                            row_data.append(cell_text or " ")
                        
                        if any(cell.strip() for cell in row_data):
                            table_data.append(row_data)
                    
                    if table_data:
                        # 转换为Markdown表格
                        if len(table_data) > 0:
                            # 表头
                            header = "| " + " | ".join(table_data[0]) + " |"
                            separator = "|" + "|".join([" --- " for _ in table_data[0]]) + "|"
                            markdown_parts.append(header)
                            markdown_parts.append(separator)
                            
                            # 数据行
                            for row in table_data[1:]:
                                row_md = "| " + " | ".join(row) + " |"
                                markdown_parts.append(row_md)
                    else:
                        markdown_parts.append("*此工作表无数据*")
                    
                    markdown_parts.append("")
                
                markdown_content = "\n".join(markdown_parts)
                metadata = {"parser": "odfpy+markdown", "sheets": len(tables)}
                
                return self.result_builder.create_success_result(markdown_content, "ods", metadata)
                
            except ImportError:
                return self.result_builder.create_error_result("缺少ODS解析库，请安装 odfpy")
            except Exception as e:
                return self.result_builder.create_error_result(f"ODS文档解析失败: {e}")
                
        except Exception as e:
            return self.result_builder.create_error_result(f"解析ODS文档失败: {e}")
        finally:
            if temp_file:
                self.file_manager.cleanup_temp_file(temp_file)

    def _parse_odp_legacy(self, content: bytes, file_extension: str) -> ParseResult:
        """使用原有方法解析ODP文件"""
        temp_file = None
        try:
            self.logger.info("使用odfpy解析ODP文件")
            temp_file = self.file_manager.save_temp_file(content, file_extension)
            
            try:
                from odf.opendocument import load
                from odf.draw import Page
                from odf.text import P
                from odf.teletype import extractText
                
                doc = load(str(temp_file))
                pages = doc.getElementsByType(Page)
                markdown_parts = []
                
                markdown_parts.append("# OpenDocument 演示文稿")
                markdown_parts.append("")
                
                for page_idx, page in enumerate(pages, 1):
                    markdown_parts.append(f"## 幻灯片 {page_idx}")
                    markdown_parts.append("")
                    
                    paragraphs = page.getElementsByType(P)
                    slide_content = []
                    
                    for paragraph in paragraphs:
                        text = extractText(paragraph).strip()
                        if text:
                            slide_content.append(f"- {text}")
                    
                    if slide_content:
                        markdown_parts.extend(slide_content)
                    else:
                        markdown_parts.append("*此幻灯片无文本内容*")
                    
                    markdown_parts.append("")
                
                markdown_content = "\n".join(markdown_parts)
                metadata = {"parser": "odfpy+markdown", "slides": len(pages)}
                
                return self.result_builder.create_success_result(markdown_content, "odp", metadata)
                
            except ImportError:
                return self.result_builder.create_error_result("缺少ODP解析库，请安装 odfpy")
            except Exception as e:
                return self.result_builder.create_error_result(f"ODP文档解析失败: {e}")
                
        except Exception as e:
            return self.result_builder.create_error_result(f"解析ODP文档失败: {e}")
        finally:
            if temp_file:
                self.file_manager.cleanup_temp_file(temp_file)

