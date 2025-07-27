"""
文本文件解析器
处理纯文本、RTF、Markdown等文本格式文件
使用轻量级库，移除langchain_community依赖
"""

from .base import BaseParser
from ..models import ParseResult


class TextParser(BaseParser):
    """文本文件解析器"""
    
    def __init__(self, storage_client=None):
        super().__init__(storage_client=storage_client)
        self.parser_version = "1.1"  # 更新解析器版本

    def _parse_content(self, content: bytes, file_extension: str = None) -> ParseResult:
        """
        解析文本文件
        
        Args:
            content: 文件内容字节数据
            file_extension: 文件扩展名
            
        Returns:
            解析结果对象
        """
        if not file_extension:
            # 如果没有扩展名，尝试直接解析为文本
            file_extension = '.txt'
        
        file_extension = file_extension.lower()
        
        if file_extension not in ['.txt', '.md', '.markdown', '.json']:
            return self._create_error_result(f"不支持的文本文件类型: {file_extension}")
        
        try:
            self.logger.info(f"开始解析文本文档: {file_extension}")
            
            # 根据扩展名选择适合的解析方法
            if file_extension == '.txt':
                return self._parse_text(content)
            elif file_extension in ['.md', '.markdown']:
                return self._parse_markdown(content, file_extension)
            elif file_extension == '.json':
                return self._parse_json(content)
            else:
                return self._create_error_result(f"不支持的文本文件类型: {file_extension}")
            
        except Exception as e:
            self.logger.error(f"解析文本文档失败: {e}")
            return self._create_error_result(f"解析文本文档失败: {e}")
    
    def _parse_text(self, content: bytes) -> ParseResult:
        """
        解析纯文本文件
        
        Args:
            content: 文件内容字节数据
            
        Returns:
            解析结果对象
        """
        try:
            self.logger.info("解析纯文本文件")
            
            # 尝试多种编码解码
            text_content = None
            detected_encoding = 'unknown'
            
            # 按优先级尝试编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'utf-16le', 'utf-16be', 'latin1', 'cp1252']
            
            for encoding in encodings:
                try:
                    text_content = content.decode(encoding)
                    detected_encoding = encoding
                    self.logger.info(f"成功使用编码 {encoding} 解码文本")
                    break
                except UnicodeDecodeError:
                    continue
            
            if text_content is None:
                # 最后的备用方案：使用 errors='ignore' 强制解码
                text_content = content.decode('utf-8', errors='ignore')
                detected_encoding = 'utf-8-ignore'
                self.logger.warning("使用 utf-8 强制解码，可能丢失部分字符")
            
            if not text_content or not text_content.strip():
                return self._create_error_result("文本文档内容为空")
            
            # 不使用通用的normalize_content，因为它会破坏文本的换行格式
            # 只做基本的内容清理
            import re
            # 规范化行尾和多余空行
            text_content = re.sub(r'\r\n', '\n', text_content)  # 统一换行符
            text_content = re.sub(r'\r', '\n', text_content)    # 处理老式Mac换行符
            text_content = re.sub(r'\n{3,}', '\n\n', text_content)  # 最多保留两个连续换行
            text_content = re.sub(r'[ \t]+$', '', text_content, flags=re.MULTILINE)  # 移除行尾空白
            text_content = text_content.strip()  # 移除首尾空白
            
            # 创建元数据
            metadata = {
                "encoding": detected_encoding,
                "size": len(content),
                "parser": "direct_decode"
            }
            
            self.logger.info(f"文本文档解析成功，编码: {detected_encoding}")
            return self._create_success_result(text_content, "txt", metadata)
            
        except Exception as e:
            self.logger.error(f"解析纯文本失败: {e}")
            return self._create_error_result(f"解析纯文本失败: {e}")
    
    def _parse_markdown(self, content: bytes, file_extension: str) -> ParseResult:
        """
        解析Markdown文档，直接返回Markdown格式内容
        
        Args:
            content: 文件内容
            file_extension: 文件扩展名
            
        Returns:
            解析结果对象，内容为原始Markdown格式
        """
        try:
            self.logger.info(f"开始解析Markdown文档: {file_extension}")
            
            # 尝试多种编码解码
            markdown_content = None
            detected_encoding = 'unknown'
            
            # 按优先级尝试编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'utf-16le', 'utf-16be', 'latin1', 'cp1252']
            
            for encoding in encodings:
                try:
                    markdown_content = content.decode(encoding)
                    detected_encoding = encoding
                    self.logger.info(f"成功使用编码 {encoding} 解码Markdown")
                    break
                except UnicodeDecodeError:
                    continue
            
            if markdown_content is None:
                # 最后的备用方案：使用 errors='ignore' 强制解码
                markdown_content = content.decode('utf-8', errors='ignore')
                detected_encoding = 'utf-8-ignore'
                self.logger.warning("使用 utf-8 强制解码，可能丢失部分字符")
            
            if not markdown_content or not markdown_content.strip():
                return self._create_error_result("Markdown文档内容为空")
            
            # 简单的内容规范化（保留Markdown语法）
            # 只做基本的空白字符规范化，不移除Markdown语法
            import re
            
            # 规范化行尾和多余空行
            markdown_content = re.sub(r'\r\n', '\n', markdown_content)  # 统一换行符
            markdown_content = re.sub(r'\r', '\n', markdown_content)    # 处理老式Mac换行符
            markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)  # 最多保留两个连续换行
            markdown_content = re.sub(r'[ \t]+$', '', markdown_content, flags=re.MULTILINE)  # 移除行尾空白
            markdown_content = markdown_content.strip()  # 移除首尾空白
            
            # 创建元数据
            metadata = {
                "parser": "direct_markdown",
                "encoding": detected_encoding,
                "size": len(content),
                "original_format": "markdown",
                "output_format": "markdown"
            }
            
            self.logger.info(f"Markdown文档解析成功，保留原始格式: {file_extension}")
            return self._create_success_result(markdown_content, "markdown", metadata)
            
        except Exception as e:
            self.logger.error(f"解析Markdown文档失败: {e}")
            return self._create_error_result(f"解析Markdown文档失败: {e}")
    
    def _parse_json(self, content: bytes) -> ParseResult:
        """
        解析JSON文件
        
        Args:
            content: 文件内容字节数据
            
        Returns:
            解析结果对象
        """
        try:
            self.logger.info("解析JSON文件")
            
            # 尝试多种编码解码
            json_content = None
            detected_encoding = 'unknown'
            
            # 按优先级尝试编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'utf-16le', 'utf-16be', 'latin1', 'cp1252']
            
            for encoding in encodings:
                try:
                    json_content = content.decode(encoding)
                    detected_encoding = encoding
                    self.logger.info(f"成功使用编码 {encoding} 解码JSON")
                    break
                except UnicodeDecodeError:
                    continue
            
            if json_content is None:
                # 最后的备用方案：使用 errors='ignore' 强制解码
                json_content = content.decode('utf-8', errors='ignore')
                detected_encoding = 'utf-8-ignore'
                self.logger.warning("使用 utf-8 强制解码，可能丢失部分字符")
            
            if not json_content or not json_content.strip():
                return self._create_error_result("JSON文档内容为空")
            
            # 验证JSON格式的有效性
            import json
            try:
                parsed_json = json.loads(json_content)
                self.logger.info("JSON格式验证成功")
            except json.JSONDecodeError as e:
                self.logger.warning(f"JSON格式验证失败: {e}，将作为纯文本处理")
                # 如果JSON格式无效，仍然返回原始内容，但在元数据中标记
                parsed_json = None
            
            # 简单的内容规范化
            import re
            # 规范化行尾和多余空行
            json_content = re.sub(r'\r\n', '\n', json_content)  # 统一换行符
            json_content = re.sub(r'\r', '\n', json_content)    # 处理老式Mac换行符
            json_content = re.sub(r'[ \t]+$', '', json_content, flags=re.MULTILINE)  # 移除行尾空白
            json_content = json_content.strip()  # 移除首尾空白
            
            # 创建元数据
            metadata = {
                "encoding": detected_encoding,
                "size": len(content),
                "parser": "json_parser",
                "is_valid_json": parsed_json is not None,
                "original_format": "json",
                "output_format": "json"
            }
            
            # 如果JSON有效，可以选择性地添加结构化信息到元数据
            if parsed_json is not None:
                if isinstance(parsed_json, dict):
                    metadata["json_type"] = "object"
                    metadata["json_keys"] = list(parsed_json.keys()) if len(parsed_json) <= 50 else "too_many_keys"
                elif isinstance(parsed_json, list):
                    metadata["json_type"] = "array"
                    metadata["json_length"] = len(parsed_json)
                else:
                    metadata["json_type"] = type(parsed_json).__name__
            
            self.logger.info(f"JSON文档解析成功，编码: {detected_encoding}, 有效JSON: {parsed_json is not None}")
            return self._create_success_result(json_content, "json", metadata)
            
        except Exception as e:
            self.logger.error(f"解析JSON文档失败: {e}")
            return self._create_error_result(f"解析JSON文档失败: {e}")

