"""
文件读取器核心类
负责协调各个组件完成文件内容提取
"""

import asyncio
from typing import List, Dict, Any, Optional

from .models import ReadRequest, ReadResponse, FailureType
from .storage import HTTPDownloadStorageClient, BaseStorageClient
from .parsers import PDFParser, OfficeParser, TextParser, ImageParser, ArchiveParser
from .utils import get_logger, format_file_size
from .config import SUPPORTED_DOC_TYPES, IGNORED_TYPES
from .parsed_cache import get_parsed_cache


class FileReader:
    """
    文件读取器核心类
    负责批量下载文件并提取文本内容，支持HTTP下载和本地文件模式
    """
    
    def __init__(
        self,
        storage_client: Optional[BaseStorageClient] = None,
        max_workers: int = 5,
        max_file_size: int = None,  # 已简化，不再处理环境变量，依赖模型层默认值
        min_content_length: int = 10
    ):
        """
        初始化文件读取器
        
        Args:
            storage_client: 存储客户端（HTTP下载或本地文件）
            max_workers: 最大并发工作线程数
            max_file_size: 最大文件大小限制（字节），为None时不设置额外限制
            min_content_length: 最小内容长度
        """
        self.logger = get_logger("file_reader.core")
        
        # 初始化存储客户端，默认使用HTTP下载
        self.storage_client = storage_client or HTTPDownloadStorageClient()
        
        # 配置参数
        self.max_workers = max_workers
        self.max_file_size = max_file_size  # 可以为None，由请求级别的max_size控制
        self.min_content_length = min_content_length
        
        # 初始化解析缓存
        self.parsed_cache = get_parsed_cache()
        
        # 初始化解析器（传递存储客户端，用于图片上传）
        self.parsers = {
            'pdf': PDFParser(storage_client=self.storage_client),
            'office': OfficeParser(storage_client=self.storage_client),
            'text': TextParser(storage_client=self.storage_client),
            'image': ImageParser(storage_client=self.storage_client),
            'archive': ArchiveParser(storage_client=self.storage_client)
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
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_reads": 0,
            "failed_reads": 0,
            "total_files_processed": 0,
            "total_content_size": 0,
            "cache_hits": 0
        }
        
        max_file_size_str = format_file_size(self.max_file_size) if self.max_file_size else "由请求控制"
        self.logger.info(f"文件读取器初始化完成 - HTTP批量下载模式, 最大并发: {max_workers}, 最大文件大小: {max_file_size_str}")
    
    def _normalize_and_validate_url(self, url: str) -> tuple[str, Optional[str]]:
        """
        标准化和验证URL
        
        Args:
            url: 原始URL字符串
            
        Returns:
            tuple: (normalized_url, error_message)
                  如果验证失败，normalized_url为None，error_message包含错误信息
        """
        if not url:
            return None, "URL为空"
        
        # 去除首尾空格
        normalized_url = url.strip()
        
        if not normalized_url:
            return None, "URL去除空格后为空"
        
        # 检查URL协议
        supported_protocols = ['http://', 'https://', 'file://']
        has_protocol = any(normalized_url.lower().startswith(protocol) for protocol in supported_protocols)
        
        # 如果没有协议，检查是否为本地文件路径
        if not has_protocol:
            # 允许普通文件路径（相对路径或绝对路径）
            from pathlib import Path
            try:
                # 尝试创建Path对象来验证路径格式
                path_obj = Path(normalized_url)
                # 如果是相对路径或绝对路径都可以接受
                self.logger.debug(f"检测到本地文件路径: {normalized_url}")
                return normalized_url, None
            except Exception as e:
                return None, f"无效的文件路径: {e}"
        
        # 对于HTTP/HTTPS URL，清理跟踪参数以提高缓存命中率
        if normalized_url.lower().startswith(('http://', 'https://')):
            if hasattr(self.storage_client, '_clean_tracking_params'):
                cleaned_url = self.storage_client._clean_tracking_params(normalized_url)
                if cleaned_url != normalized_url:
                    self.logger.debug(f"URL跟踪参数已清理: {normalized_url} -> {cleaned_url}")
                normalized_url = cleaned_url
        
        return normalized_url, None

    async def read_files(self, request: ReadRequest) -> ReadResponse:
        """
        批量读取文件内容
        
        Args:
            request: 文件读取请求
            
        Returns:
            读取响应结果
        """
        self.stats["total_requests"] += 1
        self.stats["total_files_processed"] += len(request.resource_ids)
        
        self.logger.info(f"开始批量处理文件读取请求，包含 {len(request.resource_ids)} 个文件")
        
        response = ReadResponse()
        
        # 第一步：URL标准化和验证
        normalized_urls = []
        url_mapping = {}  # 原始URL到标准化URL的映射
        
        for original_url in request.resource_ids:
            normalized_url, error_message = self._normalize_and_validate_url(original_url)
            
            if error_message:
                self.logger.warning(f"无效的URL: {original_url}, 错误: {error_message}")
                response.add_failure(original_url, FailureType.INVALID_URL, error_message)
                self.stats["failed_reads"] += 1
                continue
            
            normalized_urls.append(normalized_url)
            url_mapping[normalized_url] = original_url
            
            # 如果URL被标准化了（去除了空格、跟踪参数等），记录日志
            if normalized_url != original_url:
                self.logger.debug(f"URL标准化: '{original_url}' -> '{normalized_url}'")
        
        if not normalized_urls:
            self.logger.warning("所有URL都无效，返回空结果")
            return response
        
        # 第二步：检查解析缓存，分离需要下载的URL
        cached_results = {}
        urls_need_download = []
        
        for url in normalized_urls:
            cached_content = await self._check_parsed_cache(url, request)
            if cached_content:
                cached_results[url] = cached_content
                self.stats["cache_hits"] += 1
                self.logger.debug(f"解析缓存命中: {url}")
            else:
                urls_need_download.append(url)
                self.logger.debug(f"解析缓存未命中，需要下载: {url}")
        
        # 如果所有文件都有缓存，直接返回
        if not urls_need_download:
            self.logger.info(f"所有 {len(normalized_urls)} 个文件都有解析缓存，无需下载")
            for url, content in cached_results.items():
                original_url = url_mapping[url]  # 使用原始URL作为响应key
                response.add_content(original_url, content)
                self.stats["successful_reads"] += 1
                self.stats["total_content_size"] += len(content)
            return response
        
        # 创建新的请求对象，只包含需要下载的URL
        download_request = ReadRequest(
            resource_ids=urls_need_download,
            referer_map=request.referer_map,
            max_size=request.max_size,
            use_proxy=request.use_proxy,
            max_retries=request.max_retries,
            max_workers=request.max_workers
        )
        
        self.logger.info(f"解析缓存命中: {len(cached_results)} 个，需要下载: {len(urls_need_download)} 个")
        
        # 第二步：下载缓存未命中的文件
        if hasattr(self.storage_client, 'download_files_batch'):
            # HTTP下载模式
            self.logger.debug("使用HTTP批量下载模式")
            
            # 预处理：检查file://格式的URL是否在HTTP下载缓存中
            file_urls_to_check = []
            remaining_urls = []
            
            for url in urls_need_download:
                if url.startswith('file://'):
                    file_urls_to_check.append(url)
                else:
                    remaining_urls.append(url)
            
            # 创建初始下载结果
            from .models import DownloadResult
            download_result = DownloadResult(files={}, resource_ids={})
            
            # 处理file://格式的URL
            if file_urls_to_check:
                self.logger.debug(f"检查 {len(file_urls_to_check)} 个file://格式URL的缓存")
                
                for url in file_urls_to_check:
                    resource_id = url[8:] if url.startswith('file:///') else url[7:]  # 正确移除 'file:///' 或 'file://' 前缀
                    file_content = None
                    
                    # 在HTTP下载缓存中查找
                    if hasattr(self.storage_client, 'cache'):
                        for cache_key in self.storage_client.cache:
                            try:
                                cached_data = self.storage_client.cache.get(cache_key)
                                if cached_data and isinstance(cached_data, dict):
                                    cached_resource_id = cached_data.get("resource_id", "")
                                    if cached_resource_id == resource_id:
                                        file_content = cached_data.get("content")
                                        self.logger.debug(f"从HTTP下载缓存找到file://资源: {resource_id}")
                                        break
                            except:
                                continue
                    
                    if file_content:
                        download_result.files[url] = file_content
                        download_result.resource_ids[url] = resource_id
                        self.logger.debug(f"成功从缓存获取file://资源: {url}, 大小: {len(file_content)}字节")
                    else:
                        # 如果缓存中没有找到，添加到需要下载的列表
                        remaining_urls.append(url)
                        self.logger.debug(f"缓存中未找到file://资源: {resource_id}，将尝试下载")
            
            # 对于剩余的URL（非file://或缓存中未找到的file://），使用正常的下载流程
            if remaining_urls:
                download_request_remaining = ReadRequest(
                    resource_ids=remaining_urls,
                    referer_map=download_request.referer_map,
                    max_size=download_request.max_size,
                    use_proxy=download_request.use_proxy,
                    max_retries=download_request.max_retries,
                    max_workers=download_request.max_workers
                )
                
                remaining_download_result = await self.storage_client.download_files_batch(download_request_remaining)
                
                # 合并下载结果
                download_result.files.update(remaining_download_result.files)
                download_result.resource_ids.update(remaining_download_result.resource_ids)
        else:
            # 本地文件模式 - 创建简单的下载结果
            self.logger.debug("使用本地文件模式")
            from .models import DownloadResult
            
            download_result = DownloadResult(files={}, resource_ids={})
            
            # 对每个URL直接读取本地文件
            for url in urls_need_download:
                try:
                    # 特殊处理：如果是file://格式的resource_id，尝试从HTTP下载服务缓存查找
                    if url.startswith('file://'):
                        resource_id = url[8:] if url.startswith('file:///') else url[7:]  # 正确移除 'file:///' 或 'file://' 前缀
                        
                        # 检查是否有HTTP下载存储客户端的缓存
                        file_content = None
                        if hasattr(self.storage_client, 'cache') and hasattr(self.storage_client, '_get_cache_key'):
                            # 尝试通过所有可能的缓存键查找
                            for cache_key in self.storage_client.cache:
                                try:
                                    cached_data = self.storage_client.cache.get(cache_key)
                                    if cached_data and isinstance(cached_data, dict):
                                        cached_resource_id = cached_data.get("resource_id", "")
                                        # 检查resource_id是否匹配
                                        if cached_resource_id == resource_id:
                                            file_content = cached_data.get("content")
                                            self.logger.debug(f"从HTTP下载缓存找到file://资源: {resource_id}")
                                            break
                                except:
                                    continue
                        
                        if file_content is None:
                            # 作为fallback，尝试直接读取文件路径
                            file_path = resource_id
                            try:
                                with open(file_path, 'rb') as f:
                                    file_content = f.read()
                                self.logger.debug(f"直接读取file://资源: {file_path}")
                            except Exception as fallback_e:
                                self.logger.debug(f"直接读取file://资源失败: {file_path}, 错误: {fallback_e}")
                                raise FileNotFoundError(f"无法找到资源 {resource_id}，既不在缓存中也不在文件系统中")
                    else:
                        # 普通文件路径处理
                        file_path = url
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                    
                    download_result.files[url] = file_content
                    download_result.resource_ids[url] = url
                    self.logger.debug(f"成功读取本地文件: {url}, 大小: {len(file_content)}字节")
                    
                except Exception as e:
                    self.logger.error(f"读取本地文件失败: {url}, 错误: {e}")
                    # 本地文件读取失败，不添加到结果中
        
        self.logger.debug(f"下载结果统计: 成功={len(download_result.files)}, 请求={len(urls_need_download)}")
        self.logger.debug(f"下载的文件列表: {list(download_result.files.keys())}")
        self.logger.debug(f"Resource ID映射: {download_result.resource_ids}")
        
        # 第三步：将缓存结果添加到响应中
        for url, content in cached_results.items():
            original_url = url_mapping[url]  # 使用原始URL作为响应key
            response.add_content(original_url, content)
            self.stats["successful_reads"] += 1
            self.stats["total_content_size"] += len(content)
        
        # 第四步：并发处理下载的文件
        tasks = []
        self.logger.debug(f"开始处理下载的文件，urls_need_download: {urls_need_download}")
        self.logger.debug(f"下载结果包含的文件: {list(download_result.files.keys())}")
        
        for normalized_url in urls_need_download:
            file_content = download_result.files.get(normalized_url)
            original_url = url_mapping[normalized_url]  # 获取对应的原始URL
            self.logger.debug(f"查找文件: {normalized_url}, 找到: {file_content is not None}")
            
            if file_content:
                # 使用下载返回的正确 resource_id 进行处理
                correct_resource_id = download_result.resource_ids.get(normalized_url, normalized_url)
                self.logger.debug(f"找到下载的文件: {normalized_url} -> {correct_resource_id}, 大小: {len(file_content)}字节")
                task = self._process_file_content(correct_resource_id, file_content, download_request.max_size)
            else:
                self.logger.warning(f"未找到下载的文件: {original_url}")
                self.logger.debug(f"  可用的下载结果: {list(download_result.files.keys())}")
                
                # 尝试进行URL比较分析
                for available_url in download_result.files.keys():
                    if original_url == available_url:
                        self.logger.debug(f"  URL完全匹配但仍未找到: {available_url}")
                    elif original_url in available_url or available_url in original_url:
                        self.logger.debug(f"  部分匹配的URL: {available_url}")
                        
                # 下载失败的文件，尝试获取精确的错误信息
                error_info = None
                if hasattr(self.storage_client, '_download_errors'):
                    error_info = self.storage_client._download_errors.get(normalized_url)
                
                if error_info:
                    # 使用精确的错误类型和信息
                    error_type_value = error_info["error_type"]
                    # 将错误类型字符串转换为对应的FailureType枚举
                    try:
                        # 下载服务返回的type字段应该是FailureType枚举值的字符串形式
                        # 首先尝试按值匹配（小写）
                        error_type = FailureType(error_type_value.lower())
                    except ValueError:
                        try:
                            # 如果按值匹配失败，尝试按枚举名称匹配（大写）
                            error_type = FailureType[error_type_value.upper()]
                        except (KeyError, AttributeError):
                            # 如果都失败，使用默认错误类型
                            self.logger.warning(f"未知的错误类型: {error_type_value}, 使用默认值 OTHER")
                            error_type = FailureType.OTHER
                    task = self._create_failed_task(original_url, error_info["error_message"], error_type)
                else:
                    # 使用通用的下载失败错误
                    task = self._create_failed_task(original_url, "文件下载失败", FailureType.NETWORK_ERROR)
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理下载结果
        for i, result in enumerate(results):
            normalized_url = urls_need_download[i]  # 获取标准化的URL
            original_url = url_mapping[normalized_url]  # 获取对应的原始URL
            
            if isinstance(result, Exception):
                self.logger.error(f"处理文件时发生异常: {original_url}, 错误: {result}")
                response.add_failure(
                    original_url,
                    FailureType.OTHER,
                    f"处理异常: {str(result)}"
                )
                self.stats["failed_reads"] += 1
            elif result is None:
                response.add_failure(
                    original_url,
                    FailureType.OTHER,
                    "处理结果为空"
                )
                self.stats["failed_reads"] += 1
            elif isinstance(result, tuple):
                success, content_or_error, error_type = result
                if success:
                    response.add_content(original_url, content_or_error)
                    self.stats["successful_reads"] += 1
                    self.stats["total_content_size"] += len(content_or_error)
                else:
                    response.add_failure(original_url, error_type, content_or_error)
                    self.stats["failed_reads"] += 1
        
        self.logger.info(f"批量文件读取完成 - 成功: {len(response.contents)} (缓存: {len(cached_results)}, 新解析: {len(response.contents) - len(cached_results)}), 失败: {len(response.failed)}")
        return response
    
    async def _create_failed_task(self, resource_id: str, error_message: str, error_type: FailureType) -> tuple:
        """
        创建一个返回失败结果的任务
        
        Args:
            resource_id: 资源ID
            error_message: 错误信息
            error_type: 错误类型
            
        Returns:
            失败结果元组
        """
        return (False, error_message, error_type)
    
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
            # 使用Path提取扩展名（兼容文件路径和URL格式）
            from pathlib import Path
            
            # 处理可能的查询参数情况：file.pdf?version=1
            resource_clean = resource_id.split('?')[0] if '?' in resource_id else resource_id
            
            ext = Path(resource_clean).suffix.lower()
            
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
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        storage_stats = self.storage_client.get_stats()
        
        # 收集图片上传统计信息
        image_upload_stats = {}
        file_upload_stats = {}
        for parser_name, parser in self.parsers.items():
            if hasattr(parser, 'get_image_upload_stats'):
                parser_upload_stats = parser.get_image_upload_stats()
                if parser_upload_stats['total_uploads'] > 0:
                    image_upload_stats[parser_name] = parser_upload_stats
            
            # 收集文件上传统计信息（压缩包文件）
            if hasattr(parser, 'get_file_upload_stats'):
                parser_file_stats = parser.get_file_upload_stats()
                if parser_file_stats['total_uploads'] > 0:
                    file_upload_stats[parser_name] = parser_file_stats
        
        stats_result = {
            "file_reader": {
                "total_requests": self.stats["total_requests"],
                "successful_reads": self.stats["successful_reads"],
                "failed_reads": self.stats["failed_reads"],
                "success_rate": (
                    self.stats["successful_reads"] / max(self.stats["total_files_processed"], 1)
                ),
                "total_files_processed": self.stats["total_files_processed"],
                "total_content_size": self.stats["total_content_size"],
                "average_content_size": (
                    self.stats["total_content_size"] / max(self.stats["successful_reads"], 1)
                )
            },
            "storage": storage_stats,
            "parsers": {
                parser_name: parser.__class__.__name__ 
                for parser_name, parser in self.parsers.items()
            }
        }
        
        # 如果有图片上传统计，添加到结果中
        if image_upload_stats:
            stats_result["image_upload"] = image_upload_stats
            
        # 如果有文件上传统计，添加到结果中
        if file_upload_stats:
            stats_result["file_upload"] = file_upload_stats
        
        return stats_result
    
    def clear_cache(self):
        """清除缓存"""
        self.storage_client.clear_cache()
        self.logger.info("缓存已清空")
    
    async def _check_parsed_cache(self, url: str, request: ReadRequest) -> Optional[str]:
        """
        检查URL对应的解析缓存
        
        Args:
            url: 文件URL
            request: 请求对象，用于生成缓存键
            
        Returns:
            缓存的解析内容，如果没有缓存则返回None
        """
        try:
            # 获取文件内容用于生成解析缓存键
            file_content = None
            
            # 对于HTTP下载，先检查HTTP下载缓存
            if hasattr(self.storage_client, '_get_cache_key') and hasattr(self.storage_client, 'cache'):
                # HTTP下载模式 - 检查下载缓存
                try:
                    cache_key = self.storage_client._get_cache_key(url, request)
                    cached_data = self.storage_client.cache.get(cache_key)
                    
                    if cached_data and isinstance(cached_data, dict) and "content" in cached_data:
                        file_content = cached_data["content"]
                        self.logger.debug(f"从HTTP下载缓存获取文件内容: {url}")
                except Exception as e:
                    self.logger.debug(f"检查HTTP下载缓存失败: {url}, 错误: {e}")
            
            # 如果HTTP下载缓存未命中，或者是本地文件，尝试直接读取
            if file_content is None:
                if url.startswith('file://'):
                    file_path = url[7:]  # 移除 'file://' 前缀
                else:
                    file_path = url
                
                # 只对本地文件路径尝试直接读取
                if not url.startswith('http://') and not url.startswith('https://'):
                    try:
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                        self.logger.debug(f"直接读取本地文件内容: {url}")
                    except Exception as e:
                        self.logger.debug(f"直接读取本地文件失败: {url}, 错误: {e}")
                        return None
                else:
                    # HTTP URL但下载缓存未命中，无法获取文件内容检查解析缓存
                    self.logger.debug(f"HTTP URL下载缓存未命中，无法检查解析缓存: {url}")
                    return None
            
            if file_content is None:
                return None
            
            # 检测文件类型
            file_extension = self._detect_file_type(url)
            if not file_extension:
                self.logger.debug(f"无法检测文件类型: {url}")
                return None
            
            # 选择合适的解析器
            parser_type = self.file_type_mapping.get(file_extension)
            if not parser_type:
                self.logger.debug(f"不支持的文件类型: {url}, 扩展名: {file_extension}")
                return None
            
            parser = self.parsers.get(parser_type)
            if not parser:
                self.logger.debug(f"解析器未找到: {url}, parser_type: {parser_type}")
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
                self.logger.debug(f"解析缓存命中: {url}, 解析器: {parser_type}")
                return cached_result["content"]
            else:
                self.logger.debug(f"解析缓存未命中: {url}, 解析器: {parser_type}")
                return None
                
        except Exception as e:
            self.logger.debug(f"检查解析缓存失败: {url}, 错误: {e}")
            return None