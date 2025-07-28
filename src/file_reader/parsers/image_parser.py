"""
图像文件解析器
使用多模态LLM进行OCR文字识别，输出Markdown格式
"""

import os
import base64
import re

from .base import BaseParser
from ..models import ParseResult
from ..llm_util import get_llm


class ImageParser(BaseParser):
    """图像文件解析器，使用多模态LLM进行OCR，输出Markdown格式"""

    def __init__(self):
        super().__init__()
        self.parser_version = "1.3"  # 更新解析器版本：支持Markdown输出
        
        # 初始化LLM客户端
        self.llm = None
        self._initialized = False

    async def _initialize_llm(self):
        """异步初始化LLM客户端"""
        if self._initialized:
            return
            
        try:
            self.llm = await get_llm()
            self._initialized = True
            self.logger.info("LLM客户端初始化成功")
        except Exception as e:
            self.logger.error(f"LLM客户端初始化失败: {e}")
            raise

    def get_prompt(self, image_base64: str, mime_type: str) -> list:
        """
        构建图像OCR识别的多模态请求消息
        
        Args:
            image_base64: base64编码的图像数据
            mime_type: 图像的MIME类型
            
        Returns:
            构建好的消息列表，用于LLM调用
        """
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """请识别图像中的所有文字内容，并按照以下要求输出Markdown格式：

1. **保持原始布局结构**：尽可能保持文字在图像中的层次和布局关系
2. **标题处理**：如果识别到标题文字（通常字体较大或加粗），使用 # ## ### 等标题标记
3. **列表处理**：如果识别到列表项或要点，使用 - 或 1. 等列表标记
4. **表格处理**：如果识别到表格数据，使用Markdown表格语法 | 列1 | 列2 |
5. **段落分隔**：不同段落之间用空行分隔
6. **强调处理**：如果文字有明显的强调（如加粗），使用 **文字** 标记
7. **代码识别**：如果识别到代码片段，使用 ``` 代码块标记

请直接输出Markdown格式的内容，不要添加额外的解释或描述。"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ]

    async def _parse_content_async(self, content: bytes, file_extension: str = None, temperature: float = 0.1) -> ParseResult:
        """
        解析图像文件，使用多模态LLM进行OCR识别，输出Markdown格式
        
        Args:
            content: 图像文件内容字节数据
            file_extension: 文件扩展名
            temperature: 生成温度参数
            
        Returns:
            解析结果对象，内容为Markdown格式
        """
        # 确保LLM已初始化
        if not self._initialized:
            await self._initialize_llm()
            
        if not self.llm:
            return self._create_error_result("OCR服务未配置，无法识别图像文字")
        
        if not file_extension:
            return self._create_error_result("缺少图像文件扩展名")
        
        file_extension = file_extension.lower()
        
        # 检查是否为支持的图像格式
        supported_formats = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        if file_extension not in supported_formats:
            return self._create_error_result(f"不支持的图像格式: {file_extension}")
        
        try:
            self.logger.info(f"开始使用多模态LLM识别图像文字并格式化为Markdown: {file_extension}")
            
            # 将图像内容编码为base64
            image_base64 = base64.b64encode(content).decode('utf-8')
            
            # 确定MIME类型
            mime_type = self._get_mime_type(file_extension)
            
            # 构建多模态请求消息
            messages = self.get_prompt(image_base64, mime_type)

            # 调用 LLM 进行 OCR 识别和Markdown格式化
            response = await self.llm.ainvoke(messages, temperature=temperature)
            
            # 提取识别结果
            if hasattr(response, 'content'):
                markdown_content = response.content.strip()
            else:
                markdown_content = str(response).strip()
            
            # 检查识别结果
            if not markdown_content:
                self.logger.warning("图像OCR识别结果为空")
                return self._create_error_result("图像OCR识别结果为空")
            
            # 检查是否为无文字内容的标准回复
            if self._is_no_text_response(markdown_content):
                self.logger.warning("图像中未识别到文字内容")
                return self._create_error_result("图像中未识别到文字内容")
            
            # 后处理：确保Markdown格式规范
            processed_markdown = self._post_process_markdown(markdown_content)
            
            # 不使用通用的normalize_content，因为它会破坏Markdown的换行格式
            # processed_markdown = self._normalize_content(processed_markdown)
            
            # 创建元数据
            metadata = {
                "ocr_method": "multimodal_llm_markdown",
                "image_format": file_extension,
                "image_size": len(content),
                "temperature": temperature,
                "output_format": "markdown"
            }
            
            self.logger.info(f"图像OCR识别成功，生成Markdown内容长度: {len(processed_markdown)}")
            return self._create_success_result(processed_markdown, "image_markdown", metadata)
            
        except Exception as e:
            self.logger.error(f"图像OCR识别失败: {e}")
            return self._create_error_result(f"图像OCR识别失败: {e}")
    
    def _is_no_text_response(self, content: str) -> bool:
        """
        检查是否为无文字内容的响应
        
        Args:
            content: 识别内容
            
        Returns:
            是否为无文字响应
        """
        content_lower = content.lower().strip()
        no_text_patterns = [
            '无文字内容',
            'no text found',
            'no text',
            '*此图像中未识别到文字内容*',
            '未识别到文字',
            'no content found',
            'empty',
            '空白',
            '没有文字'
        ]
        
        return any(pattern in content_lower for pattern in no_text_patterns)
    
    def _post_process_markdown(self, content: str) -> str:
        """
        后处理Markdown内容，确保格式规范
        
        Args:
            content: 原始Markdown内容
            
        Returns:
            处理后的Markdown内容
        """
        # 如果内容没有以标题开头，添加一个默认标题
        if not content.startswith('#'):
            content = "# 图像内容识别\n\n" + content
        
        # 修复表格行之间的连接问题（如果表格行被连在一起）
        # 匹配形如 "| cell1 | cell2 | | cell3 | cell4 |" 的情况
        content = re.sub(r'(\|[^|\n]*\|)\s*(\|[^|\n]*\|)', r'\1\n\2', content)
        
        # 修复标题之间的连接问题（如果标题被连在一起）
        # 匹配形如 "# title1 ## title2" 或 "## title1 ### title2" 的情况
        content = re.sub(r'(#+\s[^#\n]*?)\s+(#+\s)', r'\1\n\n\2', content)
        
        # 修复标题和表格混合的情况
        # 匹配形如 "### title | table |" 的情况
        content = re.sub(r'(#+\s[^#\n|]*?)\s*(\|[^|\n]*\|)', r'\1\n\n\2', content)
        
        # 规范化空行：连续的空行最多保留两个
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 确保标题前后有适当的空行
        content = re.sub(r'(\n|^)(#+\s)', r'\1\n\2', content)
        content = re.sub(r'(#+\s.*?)\n([^#\n])', r'\1\n\n\2', content)
        
        # 确保列表项格式正确
        content = re.sub(r'\n([-*+])\s', r'\n\1 ', content)
        content = re.sub(r'\n(\d+\.)\s', r'\n\1 ', content)
        
        # 确保表格前后有空行
        content = re.sub(r'(\n|^)(\|.*?\|)\n', r'\1\n\2\n', content)
        
        # 移除行尾多余空格
        content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
        
        # 移除行内多余空格（但保留单个空格和表格分隔符）
        content = re.sub(r'(?<![\|\s])\s{2,}(?![\|\s])', ' ', content)
        
        # 确保文档末尾只有一个换行
        content = content.strip() + '\n'
        
        return content
    
    def _get_mime_type(self, file_extension: str) -> str:
        """
        根据文件扩展名获取MIME类型
        
        Args:
            file_extension: 文件扩展名
            
        Returns:
            MIME类型字符串
        """
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }
        
        return mime_types.get(file_extension, 'image/jpeg')

    def _parse_content(self, content: bytes, file_extension: str = None, **kwargs) -> ParseResult:
        """
        同步解析图像文件，使用nest_asyncio避免事件循环冲突
        
        Args:
            content: 图像文件内容字节数据
            file_extension: 文件扩展名
            **kwargs: 其他解析参数
            
        Returns:
            解析结果对象，内容为Markdown格式
        """
        import asyncio
        
        try:
            # 尝试安装并使用nest_asyncio来处理嵌套事件循环
            try:
                import nest_asyncio
                nest_asyncio.apply()
            except ImportError:
                # 如果没有nest_asyncio，尝试创建新的事件循环
                pass
            
            # 获取或创建事件循环
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果当前循环正在运行，创建新的事件循环
                    import concurrent.futures
                    import threading
                    
                    # 在新线程中运行异步方法
                    result = None
                    exception = None
                    
                    def run_async():
                        nonlocal result, exception
                        try:
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            result = new_loop.run_until_complete(
                                self._parse_content_async(content, file_extension, **kwargs)
                            )
                            new_loop.close()
                        except Exception as e:
                            exception = e
                    
                    thread = threading.Thread(target=run_async)
                    thread.start()
                    thread.join()
                    
                    if exception:
                        raise exception
                    return result
                else:
                    # 当前循环未运行，直接使用
                    return loop.run_until_complete(
                        self._parse_content_async(content, file_extension, **kwargs)
                    )
            except RuntimeError:
                # 没有事件循环，创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self._parse_content_async(content, file_extension, **kwargs)
                    )
                finally:
                    loop.close()
                    
        except Exception as e:
            self.logger.error(f"同步图像解析失败: {e}")
            return self._create_error_result(f"图像解析失败: {e}") 