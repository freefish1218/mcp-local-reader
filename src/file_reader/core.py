"""
文件读取器核心类
负责协调各个组件完成文件内容提取
"""

from typing import Optional

from .models import ReadResponse, FailureType
from .storage import LocalFileStorageClient, BaseStorageClient
from .parsers import PDFParser, OfficeParser, TextParser, ImageParser, ArchiveParser
from .utils import get_logger, format_file_size
from .config import SUPPORTED_DOC_TYPES, IGNORED_TYPES
from .parsed_cache import get_parsed_cache


class FileReader:
    """
    文件读取器核心类
    负责本地文件读取并提取文本内容
    """
    
    def __init__(
        self,
        storage_client: Optional[BaseStorageClient] = None,
        max_file_size: int = None,  # 已简化，不再处理环境变量，依赖模型层默认值
        min_content_length: int = 10
    ):
        """
        初始化文件读取器
        
        Args:
            storage_client: 存储客户端（本地文件）
            max_file_size: 最大文件大小限制（字节），为None时不设置额外限制
            min_content_length: 最小内容长度
        """
        self.logger = get_logger("file_reader.core")
        
        # 初始化存储客户端，默认使用本地文件存储
        self.storage_client = storage_client or LocalFileStorageClient()
        
        # 配置参数
        self.max_file_size = max_file_size  # 可以为None，由请求级别的max_size控制
        self.min_content_length = min_content_length
        
        # 初始化解析缓存
        self.parsed_cache = get_parsed_cache()
        
        # 初始化解析器
        self.parsers = {
            'pdf': PDFParser(),
            'office': OfficeParser(),
            'text': TextParser(),
            'image': ImageParser(),
            'archive': ArchiveParser()
        }
        
        # 文件类型到解析器的映射
        self.file_type_mapping = {
            '.pdf': 'pdf',
            '.doc': 'office',
            '.docx': 'office',
            '.xls': 'office', 
            '.xlsx': 'office',
            '.ppt': 'office',
            '.pptx': 'office',
            '.rtf': 'office',
            '.odt': 'office',
            '.ods': 'office',
            '.odp': 'office',
            '.csv': 'office',
            '.epub': 'office',
            '.txt': 'text',
            '.md': 'text',   # Markdown文档使用TextParser，支持多种解析方式
            '.markdown': 'text',  # Markdown文档的完整扩展名
            '.json': 'text',  # JSON文档使用TextParser
            '.jpg': 'image',
            '.jpeg': 'image',
            '.png': 'image',
            '.gif': 'image',
            '.bmp': 'image',
            '.webp': 'image',
            '.tiff': 'image',
            # 压缩文件
            '.zip': 'archive',
            '.rar': 'archive', 
            '.7z': 'archive',
            '.tar': 'archive',
            '.gz': 'archive',
            '.tar.gz': 'archive',
            '.tgz': 'archive',
            '.tar.bz2': 'archive',
            '.tbz2': 'archive'
        }
        
        
        max_file_size_str = format_file_size(self.max_file_size) if self.max_file_size else "由请求控制"
        self.logger.info(f"文件读取器初始化完成 - 本地文件模式, 最大文件大小: {max_file_size_str}")
    
    def _normalize_and_validate_path(self, file_path: str) -> tuple[str, Optional[str]]:
        """
        标准化和验证文件路径

        Args:
            path: 原始路径字符串
            
        Returns:
            tuple: (normalized_path, error_message)
                  如果验证失败，normalized_path为None，error_message包含错误信息
        """
        if not file_path:
            return None, "路径为空"
        
        # 去除首尾空格
        normalized_path = file_path.strip()
        
        if not normalized_path:
            return None, "路径去除空格后为空"
        
        # 验证路径是否有效
        from pathlib import Path
        try:
            # 尝试创建Path对象来验证路径格式
            Path(normalized_path)
            self.logger.debug(f"检测到有效的本地文件路径: {normalized_path}")
            return normalized_path, None
        except Exception as e:
            return None, f"无效的文件路径: {e}"

    async def read_file(self, request) -> ReadResponse:
        """
        读取单个文件内容
        
        Args:
            request: 文件读取请求（LocalReadRequest）
            
        Returns:
            读取响应结果
        """
        file_path = request.file_paths[0]
        self.logger.info(f"开始处理文件读取请求: {file_path}")
        
        response = ReadResponse()
        
        # 路径标准化和验证
        normalized_path, error_message = self._normalize_and_validate_path(file_path)
        if error_message:
            self.logger.warning(f"无效的路径: {file_path}, 错误: {error_message}")
            response.add_failure(file_path, FailureType.INVALID_URL, error_message)
            return response
        
        # 检查解析缓存
        cached_content = await self._check_parsed_cache(normalized_path, request)
        if cached_content is not None:
            self.logger.info(f"解析缓存命中: {file_path}")
            # 检查缓存内容的长度
            if len(cached_content) < self.min_content_length:
                self.logger.error(f"缓存内容过短: {file_path}, 内容长度: {len(cached_content)}, 最小要求: {self.min_content_length}")
                response.add_failure(file_path, FailureType.PARSE_ERROR, "提取的内容过短")
            else:
                response.add_content(file_path, cached_content)
            return response
            
        self.logger.info(f"解析缓存未命中，需要读取和解析: {file_path}")
        
        # 读取文件
        try:
            with open(normalized_path, 'rb') as f:
                file_content = f.read()
            self.logger.debug(f"成功读取本地文件: {normalized_path}, 大小: {len(file_content)}字节")
        except Exception as e:
            self.logger.error(f"读取本地文件失败: {normalized_path}, 错误: {e}")
            response.add_failure(file_path, FailureType.OTHER, f"文件读取失败: {e}")
            return response
            
        # 处理文件内容
        max_size = getattr(request, 'max_size', 20 * 1024 * 1024)
        success, content_or_error, error_type = await self._process_file_content(
            normalized_path, file_content, max_size
        )
        
        if success:
            response.add_content(file_path, content_or_error)
        else:
            response.add_failure(file_path, error_type, content_or_error)
            
        return response
    
    async def _process_file_content(self, resource_id: str, file_content: bytes, max_size: int) -> Optional[tuple]:
        """
        异步处理已下载的文件内容
        
        Args:
            resource_id: 资源ID
            file_content: 文件内容字节数据
            max_size: 最大文件大小
            
        Returns:
            (成功标志, 内容或错误信息, 错误类型)
        """
        try:
            self.logger.debug(f"开始处理文件内容: {resource_id}")
            
            # 检查文件大小
            if len(file_content) > max_size:
                size_mb = len(file_content) / (1024 * 1024)
                limit_mb = max_size / (1024 * 1024)
                error_msg = f"文件过大: {size_mb:.1f}MB，超过请求大小限制 {limit_mb:.0f}MB"
                self.logger.error(f"文件大小检查失败: {resource_id}, {error_msg}")
                return (False, error_msg, FailureType.SIZE_EXCEEDED)
            
            # 简化的文件类型检测（只从URL提取扩展名）
            file_extension = self._detect_file_type(resource_id)
            if not file_extension:
                self.logger.error(f"文件类型检测失败: {resource_id}, 无法从URL提取扩展名")
                return (False, "无法识别文件类型", FailureType.UNSUPPORTED_TYPE)
            
            # 检查是否为忽略的文件类型
            if file_extension in IGNORED_TYPES:
                self.logger.error(f"忽略的文件类型: {resource_id}, 扩展名: {file_extension}")
                return (False, f"忽略的文件类型: {file_extension}", FailureType.UNSUPPORTED_TYPE)
            
            # 选择合适的解析器
            parser_type = self.file_type_mapping.get(file_extension)
            if not parser_type:
                self.logger.error(f"不支持的文件类型: {resource_id}, 扩展名: {file_extension}")
                return (False, f"不支持的文件类型: {file_extension}", FailureType.UNSUPPORTED_TYPE)
            
            parser = self.parsers.get(parser_type)
            if not parser:
                self.logger.error(f"解析器未找到: {resource_id}, parser_type: {parser_type}")
                return (False, f"解析器未找到: {parser_type}", FailureType.PARSE_ERROR)
            
            # 解析文件内容（支持异步和同步解析器）
            self.logger.debug(f"使用 {parser_type} 解析器解析文件: {resource_id}")
            
            # 检查解析器是否是异步的
            if parser_type == 'image':
                # 图像解析器是异步的，使用parse_async方法
                parse_result = await parser.parse_async(file_content, file_extension)
            else:
                # 其他解析器是同步的
                parse_result = parser.parse(file_content, file_extension)
            
            if not parse_result.success:
                error_type = FailureType.OCR_ERROR if parser_type == 'image' else FailureType.PARSE_ERROR
                self.logger.error(f"解析失败: {resource_id}, parser_type: {parser_type}, 错误: {parse_result.error}")
                return (False, parse_result.error or "解析失败", error_type)
            
            # 检查内容长度
            content = parse_result.content or ""
            if len(content) < self.min_content_length:
                self.logger.error(f"提取的内容过短: {resource_id}, 内容长度: {len(content)}, 最小要求: {self.min_content_length}")
                return (False, "提取的内容过短", FailureType.PARSE_ERROR)
            
            self.logger.debug(f"文件处理成功: {resource_id} (类型: {file_extension}), 内容长度: {len(content)}")
            return (True, content, None)
            
        except Exception as e:
            self.logger.error(f"处理文件失败: {resource_id}, 错误: {e}")
            return (False, f"处理异常: {str(e)}", FailureType.OTHER)
    
    def _detect_file_type(self, resource_id: str) -> Optional[str]:
        """
        简化的文件类型检测：仅从URL/resource_id提取扩展名
        
        Args:
            resource_id: 资源ID（URL或文件路径）
            
        Returns:
            文件扩展名（如果支持），否则返回None
        """
        try:
            # 使用Path提取扩展名
            from pathlib import Path
            
            ext = Path(resource_id).suffix.lower()
            
            if ext and len(ext) > 1:  # 确保不是只有一个点
                # 只返回支持的文件类型
                if ext in SUPPORTED_DOC_TYPES:
                    self.logger.debug(f"从resource_id检测到支持的文件类型: {ext} (resource_id: {resource_id})")
                    return ext
                else:
                    self.logger.debug(f"从resource_id检测到不支持的文件类型: {ext} (resource_id: {resource_id})")
            
            self.logger.debug(f"无法从resource_id提取有效扩展名: {resource_id}")
            return None
            
        except Exception as e:
            self.logger.debug(f"从resource_id提取扩展名失败: {resource_id}, 错误: {e}")
            return None
    
    
    def clear_cache(self):
        """清除缓存"""
        self.storage_client.clear_cache()
        self.logger.info("缓存已清空")
    
    async def _check_parsed_cache(self, path: str, request) -> Optional[str]:
        """
        检查文件路径对应的解析缓存

        Args:
            path: 文件路径
            request: 请求对象，用于生成缓存键

        Returns:
            缓存的解析内容，如果没有缓存则返回None
        """
        try:
            # 获取文件内容用于生成解析缓存键
            try:
                with open(path, 'rb') as f:
                    file_content = f.read()
                self.logger.debug(f"直接读取本地文件内容: {path}")
            except Exception as e:
                self.logger.debug(f"直接读取本地文件失败: {path}, 错误: {e}")
                return None

            # 检测文件类型
            file_extension = self._detect_file_type(path)
            if not file_extension:
                self.logger.debug(f"无法检测文件类型: {path}")
                return None

            # 选择合适的解析器
            parser_type = self.file_type_mapping.get(file_extension)
            if not parser_type:
                self.logger.debug(f"不支持的文件类型: {path}, 扩展名: {file_extension}")
                return None

            parser = self.parsers.get(parser_type)
            if not parser:
                self.logger.debug(f"解析器未找到: {path}, parser_type: {parser_type}")
                return None

            # 生成解析缓存键
            parse_cache_key = self.parsed_cache.get_cache_key(
                file_content, 
                parser.parser_name, 
                parser.parser_version,
                None  # 暂时不包含额外参数
            )

            # 检查解析缓存
            cached_result = self.parsed_cache.get_cached_result(parse_cache_key)
            if cached_result:
                self.logger.debug(f"解析缓存命中: {path}, 解析器: {parser_type}")
                return cached_result["content"]
            else:
                self.logger.debug(f"解析缓存未命中: {path}, 解析器: {parser_type}")
                return None

        except Exception as e:
            self.logger.debug(f"检查解析缓存失败: {path}, 错误: {e}")
            return None