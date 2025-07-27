"""
HTTP下载存储客户端
通过调用HTTP下载服务获取文件内容，支持图片上传功能
"""

import os
import hashlib
import mimetypes
import base64
import httpx
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from diskcache import Cache

from .base import BaseStorageClient
from ..utils import get_logger
from ..models import DownloadResult


class HTTPDownloadStorageClient(BaseStorageClient):
    """
    HTTP下载存储客户端
    通过调用HTTP下载服务获取文件内容
    """
    
    def __init__(
        self,
        download_service_url: Optional[str] = None,
        timeout: int = 300,
        cache_directory: Optional[str] = None,
        cache_size_mb: Optional[int] = None
    ):
        """
        初始化HTTP下载存储客户端
        
        Args:
            download_service_url: 下载服务URL
            timeout: 请求超时时间（秒）
            cache_directory: 本地缓存目录
            cache_size_mb: 缓存大小(MB)
        """
        super().__init__()
        self.logger = get_logger("storage.http_download")
        
        # 从环境变量或参数获取配置
        self.download_service_url = download_service_url or os.getenv("DOWNLOAD_SERVICE_URL", "http://localhost:8080")
        self.timeout = timeout
        
        # 检查必要配置
        if not self.download_service_url:
            self.logger.warning("下载服务URL未配置，将使用模拟模式")
            self.enabled = False
        else:
            self.enabled = True
            self.logger.info(f"HTTP下载存储客户端初始化成功 - 服务地址: {self.download_service_url}")
        
        # 获取缓存目录配置
        if cache_directory is None:
            cache_root = os.getenv("CACHE_ROOT_DIR", "cache")
            cache_directory = os.path.join(cache_root, "http_download")
        
        # 获取缓存大小配置
        if cache_size_mb is None:
            cache_size_mb = int(os.getenv("FILE_READER_CACHE_SIZE_MB", "500"))
        
        cache_size_bytes = cache_size_mb * 1024 * 1024
        
        # 初始化本地缓存
        self.cache = Cache(cache_directory, size_limit=cache_size_bytes)
        
        self.logger.info(f"HTTP下载缓存配置 - 目录: {cache_directory}, 大小: {cache_size_mb}MB")
        
        # 统计信息
        self.stats = {
            "downloads": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_size": 0,
            "errors": 0
        }
        
        # 用于存储最后一次错误信息
        self._last_error = None
        
        # 用于存储下载错误详情（URL到错误信息的映射）
        self._download_errors = {}
    
    async def download_files_batch(self, request) -> DownloadResult:
        """
        批量下载文件（支持缓存机制）
        
        Args:
            request: ReadRequest对象，包含下载参数
            
        Returns:
            DownloadResult: 包含文件内容和正确resource_id映射的结果对象
        """
        try:
            results = {}
            download_resource_ids = {} # 用于存储下载的资源ID
            urls_to_download = []
            
            # 第一步：检查缓存，分离需要下载的URL
            for url in request.resource_ids:
                cache_key = self._get_cache_key(url, request)
                try:
                    cached_data = self.cache.get(cache_key)
                    if cached_data is not None:
                        # 新的缓存格式：{'content': bytes, 'resource_id': str, 'metadata': dict}
                        if isinstance(cached_data, dict) and "content" in cached_data:
                            cached_content = cached_data["content"]
                            cached_resource_id = cached_data.get("resource_id", url)
                            cached_metadata = cached_data.get("metadata", {})
                            
                            # 保存元数据到内存中，供get_file_info方法使用
                            if not hasattr(self, '_file_metadata'):
                                self._file_metadata = {}
                            self._file_metadata[url] = cached_metadata
                            
                            results[url] = cached_content
                            download_resource_ids[url] = cached_resource_id
                            self.stats["cache_hits"] += 1
                            self.logger.debug(f"缓存命中: {url} -> {cached_resource_id}")
                            continue
                        else:
                            # 无效的缓存格式，删除并重新下载
                            self.logger.warning(f"缓存格式无效，删除并重新下载: {url}")
                            del self.cache[cache_key]
                except Exception as e:
                    self.logger.warning(f"读取缓存失败: {url}, {e}")
                
                # 缓存未命中，添加到下载列表
                urls_to_download.append(url)
                self.stats["cache_misses"] += 1
            
            # 第二步：批量下载缓存未命中的文件（仅当服务启用时）
            if urls_to_download and self.enabled:
                total_files = len(request.resource_ids)
                cache_hits = len(results)
                files_to_download = len(urls_to_download)
                
                # 优化提示信息，显示详细的缓存和下载统计
                if cache_hits > 0 and files_to_download > 0:
                    self.logger.info(f"文件处理统计: 总计{total_files}个文件，缓存命中{cache_hits}个，需要下载{files_to_download}个")
                elif cache_hits > 0:
                    self.logger.info(f"文件处理统计: 总计{total_files}个文件，全部缓存命中({cache_hits}个)")
                else:
                    self.logger.info(f"文件处理统计: 总计{total_files}个文件，全部需要下载({files_to_download}个)")
                
                # 在下载前进行文件类型检测，过滤不支持的文件类型
                filtered_urls = []
                for url in urls_to_download:
                    file_type = self._detect_file_type_simple(url)
                    if file_type is None:
                        # 未检测到文件类型，继续下载
                        filtered_urls.append(url)
                        self.logger.debug(f"未检测到文件类型，将下载: {url}")
                    elif self._is_supported_file_type(file_type):
                        # 检测到支持的文件类型，继续下载
                        filtered_urls.append(url)
                        self.logger.debug(f"检测到支持的文件类型 {file_type}，将下载: {url}")
                    else:
                        # 检测到不支持的文件类型，跳过下载
                        self.logger.info(f"检测到不支持的文件类型 {file_type}，跳过下载: {url}")
                        # 记录为错误，以便在返回结果中体现
                        if not hasattr(self, '_download_errors'):
                            self._download_errors = {}
                        self._download_errors[url] = {
                            "error_type": "unsupported_file_type",
                            "error_message": f"不支持的文件类型: {file_type}"
                        }
                        self.stats["errors"] += 1
                
                # 更新需要下载的URL列表
                urls_to_download = filtered_urls
                
                if not urls_to_download:
                    self.logger.info("文件类型检测完成，所有文件都被过滤，无需下载")
                else:
                    filtered_count = len(urls_to_download)
                    skipped_count = len(request.resource_ids) - len(results) - filtered_count
                    if skipped_count > 0:
                        self.logger.info(f"文件类型检测完成，实际需要下载{filtered_count}个文件，跳过{skipped_count}个不支持的文件")
                    else:
                        self.logger.info(f"文件类型检测完成，需要下载{filtered_count}个文件")
                
                # 构建下载请求 - 支持per-URL referer
                urls_with_referer = []
                for url in urls_to_download:
                    url_obj = {
                        "url": url,
                        "referer": request.get_referer_for_url(url)
                    }
                    urls_with_referer.append(url_obj)
                
                download_request = {
                    "urls": urls_with_referer,
                    "max_size": request.max_size,  # 已经是字节数
                    "use_proxy": request.use_proxy,
                    "max_retries": request.max_retries,
                    "max_workers": request.max_workers
                }
                
                if urls_with_referer:  # 只有在有URL需要下载时才调用服务
                    try:
                        # 调用HTTP下载服务
                        self.logger.debug(f"准备调用下载服务: {self.download_service_url}/download")
                        self.logger.debug(f"请求数据: urls={len(urls_with_referer)}个, timeout={self.timeout}秒")
                        
                        async with httpx.AsyncClient(timeout=self.timeout) as client:
                            response = await client.post(
                                f"{self.download_service_url}/download",
                                json=download_request,
                                headers={"Content-Type": "application/json"}
                            )
                            response.raise_for_status()
                            download_response = response.json()
                    except httpx.ConnectError as e:
                        self.logger.error(f"连接下载服务失败: {e}")
                        self.logger.error(f"目标地址: {self.download_service_url}")
                        self.logger.error("可能的原因:")
                        self.logger.error("  1. 下载服务未启动")
                        self.logger.error("  2. 网络配置问题 (检查Docker网络)")
                        self.logger.error("  3. 地址或端口错误")
                        raise
                    except httpx.TimeoutException as e:
                        self.logger.error(f"下载服务响应超时: {e}")
                        self.logger.error(f"当前超时设置: {self.timeout}秒")
                        raise
                    except httpx.HTTPStatusError as e:
                        self.logger.error(f"下载服务返回错误状态: {e.response.status_code}")
                        try:
                            error_detail = e.response.json()
                            self.logger.error(f"错误详情: {error_detail}")
                        except:
                            self.logger.error(f"错误响应内容: {e.response.text}")
                        raise
                    except Exception as e:
                        self.logger.error(f"调用下载服务时发生未知错误: {e}")
                        self.logger.error(f"错误类型: {type(e).__name__}")
                        raise
                    
                    # 第三步：处理下载结果并保存到缓存
                    self.logger.debug(f"处理下载响应，包含 {len(download_response.get('resources', []))} 个资源")
                    
                    for resource in download_response.get("resources", []):
                        url = resource.get("url")
                        data = resource.get("data")
                        
                        self.logger.debug(f"处理下载资源: {url}")
                        self.logger.debug(f"  数据字段存在: {data is not None}")
                        self.logger.debug(f"  数据类型: {type(data)}")
                        
                        if url and data:
                            try:
                                # 验证data是字符串类型
                                if not isinstance(data, str):
                                    self.logger.error(f"数据格式错误: {url}, 期望字符串，实际: {type(data)}")
                                    self.stats["errors"] += 1
                                    continue
                                
                                self.logger.debug(f"  Base64数据长度: {len(data)}")
                                
                                # 解码base64内容
                                content = base64.b64decode(data)
                                results[url] = content
                                
                                self.logger.debug(f"成功下载并解码文件: {url}, 大小: {len(content)}字节")

                                # 保存下载的资源ID (包含真实的文件扩展名)
                                resource_id_from_server = resource.get("resource_id", url)
                                download_resource_ids[url] = resource_id_from_server
                                
                                self.logger.debug(f"  原始URL: {url}")
                                self.logger.debug(f"  服务返回的resource_id: {resource_id_from_server}")
                                self.logger.debug(f"  是否相同: {url == resource_id_from_server}")
                                
                                self.logger.debug(f"  解码成功，文件大小: {len(content)}字节")
                                
                                # 保存文件元信息（用于get_file_info方法）
                                if not hasattr(self, '_file_metadata'):
                                    self._file_metadata = {}
                                self._file_metadata[url] = {
                                    "filename": resource.get("filename", "download"),
                                    "content_type": resource.get("content_type", "application/octet-stream"),
                                    "file_type": resource.get("file_type"),
                                    "size": len(content),
                                    "cached": resource.get("cached", False),
                                    "download_time": resource.get("download_time", 0.0)
                                }
                                
                                # 保存到缓存
                                cache_key = self._get_cache_key(url, request)
                                try:
                                    # 计算缓存过期时间
                                    expire_days = int(os.getenv("CACHE_EXPIRE_DAYS", "90"))
                                    expire_seconds = expire_days * 24 * 3600
                                    
                                    # 将文件内容和resource_id一起缓存
                                    cache_data = {
                                        "content": content,
                                        "resource_id": resource_id_from_server,
                                        "metadata": {
                                            "filename": resource.get("filename", "download"),
                                            "content_type": resource.get("content_type", "application/octet-stream"),
                                            "file_type": resource.get("file_type"),
                                            "size": len(content),
                                            "cached": resource.get("cached", False),
                                            "download_time": resource.get("download_time", 0.0)
                                        }
                                    }
                                    
                                    self.cache.set(cache_key, cache_data, expire=expire_seconds)
                                    self.logger.debug(f"文件已缓存: {url}, resource_id: {resource_id_from_server}, 过期时间: {expire_days}天")
                                except Exception as e:
                                    self.logger.warning(f"保存缓存失败: {url}, {e}")
                                
                                # 更新统计
                                self.stats["total_size"] += len(content)
                                
                                self.logger.debug(f"成功下载文件: {url}, 大小: {len(content)}字节, 类型: {resource.get('file_type', 'unknown')}")
                                
                            except Exception as e:
                                self.logger.error(f"解码文件内容失败: {url}, 错误: {e}")
                                self.logger.error(f"  数据类型: {type(data)}")
                                self.logger.error(f"  数据内容预览: {str(data)[:200] if data else 'None'}")
                                self.stats["errors"] += 1
                        else:
                            # 资源数据不完整，记录为错误
                            self.logger.warning(f"资源数据不完整: url={url}, data存在={data is not None}")
                            if not url:
                                self.logger.warning("  缺少URL字段")
                            if not data:
                                self.logger.warning("  缺少data字段")
                                
                            # 将数据不完整的资源记录为下载错误
                            if url:
                                if not hasattr(self, '_download_errors'):
                                    self._download_errors = {}
                                self._download_errors[url] = {
                                    "error_type": "incomplete_data",
                                    "error_message": "资源数据不完整"
                                }
                                self.stats["errors"] += 1
                    
                    # 记录失败的文件
                    failed_resources = download_response.get("failed", [])
                    if failed_resources:
                        # 清空之前的错误记录（仅针对当前批次下载的失败）
                        if not hasattr(self, '_download_errors'):
                            self._download_errors = {}
                        
                        for failed_resource in failed_resources:
                            url = failed_resource.get("url")
                            # 注意：下载服务返回的字段是 "type"，不是 "error_type"
                            error_type = failed_resource.get("type", "other")
                            error_message = failed_resource.get("error_message", "下载失败")
                            
                            # 存储详细错误信息供FileReader使用
                            self._download_errors[url] = {
                                "error_type": error_type,  # 统一为error_type字段名
                                "error_message": error_message
                            }
                            
                            self.logger.error(f"下载失败: {url}, 类型: {error_type}, 错误: {error_message}")
                            self.stats["errors"] += 1
            elif urls_to_download and not self.enabled:
                # HTTP服务未启用，但有文件需要下载
                total_files = len(request.resource_ids)
                cache_hits = len(results)
                self.logger.warning(f"HTTP下载服务未启用，无法下载{len(urls_to_download)}个文件（总计{total_files}个文件，缓存命中{cache_hits}个）")
                if not hasattr(self, '_download_errors'):
                    self._download_errors = {}
                
                for url in urls_to_download:
                    self._download_errors[url] = {
                        "error_type": "service_disabled",
                        "error_message": "HTTP下载服务未启用"
                    }
                    self.stats["errors"] += 1
            
            # 更新统计
            self.stats["downloads"] += len(results)
            
            # 优化完成提示信息 - 修复统计逻辑
            total_files = len(request.resource_ids)
            successful_files = len(results)  # results包含所有成功获取内容的文件（缓存+下载）
            
            # 计算实际失败的文件数：应该排除已成功处理的文件
            failed_files = 0
            if hasattr(self, '_download_errors') and self._download_errors:
                # 只计算真正失败的文件，排除已经在results中的文件
                failed_files = len([url for url in self._download_errors.keys() if url not in results])
            
            # 检查是否所有请求的文件都被成功处理
            actual_failed_files = total_files - successful_files
            
            if actual_failed_files == 0:
                self.logger.info(f"批量处理完成 - 全部成功处理{total_files}个文件")
            else:
                self.logger.info(f"批量处理完成 - 成功处理{successful_files}个文件，失败{actual_failed_files}个文件")
                
                # 如果有失败的文件，显示错误统计
                if hasattr(self, '_download_errors') and self._download_errors:
                    # 只统计真正失败的错误（不在results中的）
                    failed_urls = [url for url in request.resource_ids if url not in results]
                    error_types = {}
                    
                    for url in failed_urls:
                        error_info = self._download_errors.get(url, {"error_type": "unknown"})
                        error_type = error_info.get('error_type', 'unknown')
                        error_types[error_type] = error_types.get(error_type, 0) + 1
                    
                    if error_types:  # 只有在有错误时才显示详情
                        error_summary = []
                        for error_type, count in error_types.items():
                            error_desc = {
                                'unsupported_file_type': '不支持的文件类型',
                                'service_disabled': '服务未启用',
                                'download_failed': '下载失败',
                                'incomplete_data': '数据不完整',
                                'not_found': '文件未找到',
                                'other': '其他错误'
                            }.get(error_type, error_type)
                            error_summary.append(f"{error_desc}({count}个)")
                        
                        self.logger.info(f"失败详情: {', '.join(error_summary)}")
            
            # 添加最终结果的关键调试信息（仅在出现问题时输出）
            if len(results) != len(request.resource_ids):
                self.logger.warning(f"URL匹配检查 - 请求{len(request.resource_ids)}个文件，返回{len(results)}个文件")
                self.logger.debug(f"  请求的URLs: {request.resource_ids}")
                self.logger.debug(f"  返回文件的URLs: {list(results.keys())}")
                
                # 检查URL匹配情况
                for req_url in request.resource_ids:
                    if req_url in results:
                        self.logger.debug(f"  ✓ URL匹配: {req_url}")
                    else:
                        self.logger.warning(f"  ✗ URL不匹配: {req_url}")
                        # 寻找可能的匹配
                        for result_url in results.keys():
                            if req_url in result_url or result_url in req_url:
                                self.logger.info(f"    可能的匹配: {result_url}")
            
            return DownloadResult(files=results, resource_ids=download_resource_ids)
            
        except Exception as e:
            # 增强错误诊断信息
            error_type = type(e).__name__
            self.logger.error(f"批量下载失败: {e}")
            self.logger.error(f"错误类型: {error_type}")
            self.logger.error(f"下载服务URL: {self.download_service_url}")
            
            # 特殊处理网络连接错误
            if "connection" in str(e).lower() or "network" in str(e).lower():
                self.logger.error("网络连接诊断:")
                self.logger.error(f"  - 检查下载服务是否运行在: {self.download_service_url}")
                self.logger.error(f"  - 检查Docker网络配置 (如果在容器中运行)")
                self.logger.error(f"  - 检查防火墙设置")
                
                # 如果在Docker环境中，提供额外的诊断信息
                import os
                if os.getenv("DOCKER_CONTAINER") == "true":
                    self.logger.error("Docker环境诊断建议:")
                    self.logger.error("  - 确保storage-server容器在同一网络中运行")
                    self.logger.error("  - 检查容器间网络连通性: docker exec <container> ping storage-server")
                    self.logger.error("  - 检查端口映射配置")
            
            self.stats["errors"] += len(request.resource_ids)
            return DownloadResult(files={}, resource_ids={})
    
    def _get_cache_key(self, url: str, request=None) -> str:
        """
        生成缓存键，清理URL跟踪参数以提高缓存命中率
        
        Args:
            url: 原始URL
            request: 请求对象（当前仅用URL生成缓存键）
            
        Returns:
            MD5缓存键
        """
        # 清理跟踪参数，提高缓存命中率
        cleaned_url = self._clean_tracking_params(url)
        return hashlib.md5(cleaned_url.encode()).hexdigest()
    
    def _is_resource_id_format(self, resource_id: str) -> bool:
        """
        检查是否为resource_id格式（而非URL）
        
        Args:
            resource_id: 资源标识符
            
        Returns:
            如果是resource_id格式返回True，否则返回False
        """
        # resource_id格式通常不包含协议前缀，且包含特定前缀
        if resource_id.startswith(('http://', 'https://', 'ftp://', 'file://')):
            return False
        
        # 检查是否包含特殊的resource_id前缀
        resource_id_prefixes = [
            'upload_',       # 上传文件
            'cached_',       # 缓存文件
            'temp_',         # 临时文件
        ]
        
        for prefix in resource_id_prefixes:
            if resource_id.startswith(prefix):
                return True
        
        # 如果不包含URL路径分隔符，可能是resource_id
        return '/' not in resource_id and '.' not in resource_id
    
    def _clean_tracking_params(self, url: str) -> str:
        """
        清理URL中的跟踪参数，提高缓存命中率
        
        Args:
            url: 原始URL
            
        Returns:
            清理后的URL
        """
        try:
            parsed = urlparse(url)
            if not parsed.query:
                return url
            
            # 常见的跟踪参数列表
            tracking_params = {
                # Google Analytics
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'utm_id', 'utm_source_platform', 'utm_creative_format', 'utm_marketing_tactic',
                
                # Facebook
                'fbclid', 'fb_action_ids', 'fb_action_types', 'fb_ref', 'fb_source',
                
                # Google Ads
                'gclid', 'gclsrc', 'dclid', 'wbraid', 'gbraid',
                
                # Microsoft/Bing
                'msclkid', 'mc_cid', 'mc_eid',
                
                # Amazon
                'tag', 'linkcode', 'creativeASIN', 'linkId', 'ref_', 'pf_rd_',
                
                # 其他常见跟踪参数
                '_ga', '_gl', 'igshid', 'feature', 'source', 'medium', 'campaign',
                'content', 'term', 'hsCtaTracking', 'hsLang', 'hsCta',
                
                # 社交媒体
                'share', 'sr_share', 'recruitmentid', 'trackingid',
                
                # 邮件营销
                'vero_conv', 'vero_id', 'nr_email_referer',
                
                # 移动应用
                'app', 'deep_link_value', 'match_type',
                
                # 其他
                'ref', 'referer', 'referrer', 'from', 'via'
            }
            
            # 解析查询参数
            params = parse_qs(parsed.query, keep_blank_values=True)
            
            # 过滤掉跟踪参数（不区分大小写）
            cleaned_params = {}
            for key, values in params.items():
                key_lower = key.lower()
                is_tracking = False
                
                # 检查是否为跟踪参数
                for tracking_param in tracking_params:
                    if key_lower == tracking_param.lower():
                        is_tracking = True
                        break
                
                if not is_tracking:
                    cleaned_params[key] = values
            
            # 重新构建查询字符串
            if cleaned_params:
                # 保持参数顺序一致性，按字母排序
                sorted_params = []
                for key in sorted(cleaned_params.keys()):
                    for value in cleaned_params[key]:
                        sorted_params.append((key, value))
                
                new_query = urlencode(sorted_params, doseq=True)
                cleaned_parsed = parsed._replace(query=new_query)
            else:
                # 没有有效参数，移除查询字符串
                cleaned_parsed = parsed._replace(query='')
            
            cleaned_url = urlunparse(cleaned_parsed)
            
            if cleaned_url != url:
                self.logger.debug(f"URL跟踪参数已清理: {url} -> {cleaned_url}")
            
            return cleaned_url
            
        except Exception as e:
            self.logger.warning(f"清理URL跟踪参数失败: {url}, 错误: {e}")
            return url
    
    def get_file_info(self, resource_id: str, headers: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            resource_id: 资源ID（URL或其他标识符）
            headers: HTTP头部信息
            
        Returns:
            文件信息字典，失败返回None
        """
        try:
            # 首先检查是否有缓存的元数据
            if hasattr(self, '_file_metadata') and resource_id in self._file_metadata:
                cached_metadata = self._file_metadata[resource_id]
                self.logger.debug(f"返回缓存的文件信息: {resource_id}")
                return cached_metadata
            
            # 对于URL，尝试从缓存中获取新格式的元数据
            if resource_id.startswith(('http://', 'https://')):
                cache_key = self._get_cache_key(resource_id)
                try:
                    cached_data = self.cache.get(cache_key)
                    if cached_data and isinstance(cached_data, dict) and "metadata" in cached_data:
                        # 从新格式缓存中获取元数据
                        metadata = cached_data["metadata"]
                        self.logger.debug(f"从缓存获取文件信息: {resource_id}")
                        return metadata
                except Exception as e:
                    self.logger.debug(f"从缓存获取文件信息失败: {resource_id}, {e}")
            
            # 对于resource_id格式，尝试从缓存中获取信息
            if self._is_resource_id_format(resource_id):
                # 这种情况下，我们无法直接获取文件信息，返回基本信息
                return {
                    "filename": resource_id,
                    "content_type": "application/octet-stream",
                    "size": None,
                    "source": "resource_id"
                }
            
            # 对于URL，如果没有缓存信息，可以尝试HEAD请求（但通常我们依赖下载时获取的信息）
            if resource_id.startswith(('http://', 'https://')):
                # 返回基本的URL信息
                from urllib.parse import urlparse
                parsed_url = urlparse(resource_id)
                filename = os.path.basename(parsed_url.path) or "download"
                
                return {
                    "filename": filename,
                    "content_type": "application/octet-stream",
                    "size": None,
                    "url": resource_id,
                    "source": "url_analysis"
                }
            
            # 其他情况返回None
            return None
            
        except Exception as e:
            self.logger.error(f"获取文件信息失败: {resource_id}, 错误: {e}")
            return None
    
    async def upload_images_batch(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量上传图片到存储服务
        
        注意：此方法虽然是async def，但在image_cache.py中通过新的事件循环同步调用
        
        Args:
            images: 图片信息列表，每个元素包含：
                   {
                       "data": bytes,  # 图片字节数据
                       "filename": str,  # 文件名（包含扩展名）
                       "content_type": str (可选)  # 内容类型
                   }
            
        Returns:
            上传结果列表，每个元素包含url、resource_id等信息，失败的返回error信息
        """
        if not self.enabled:
            self.logger.warning("HTTP下载服务未启用，无法批量上传图片")
            return [{"error": "HTTP下载服务未启用", "filename": img.get("filename", "unknown")} for img in images]
        
        if not images:
            return []
        
        try:
            # 检查批量上传数量限制
            max_batch_size = int(os.getenv("MAX_BATCH_UPLOAD_SIZE", "20"))
            if len(images) > max_batch_size:
                self.logger.error(f"批量上传图片数量超过限制: {len(images)} > {max_batch_size}")
                return [{"error": f"批量上传数量超过限制({max_batch_size})", "filename": img.get("filename", "unknown")} for img in images]
            
            # 准备批量上传请求
            files = []
            for i, image_info in enumerate(images):
                image_data = image_info.get("data")
                filename = image_info.get("filename", f"image_{i}.png")
                content_type = image_info.get("content_type")
                
                if not image_data:
                    continue
                
                # 如果没有提供content_type，尝试根据文件扩展名推断
                if not content_type:
                    content_type, _ = mimetypes.guess_type(filename)
                    if not content_type:
                        # 根据文件扩展名手动设置
                        ext = Path(filename).suffix.lower()
                        if ext in ['.png']:
                            content_type = 'image/png'
                        elif ext in ['.jpg', '.jpeg']:
                            content_type = 'image/jpeg'
                        elif ext in ['.gif']:
                            content_type = 'image/gif'
                        elif ext in ['.webp']:
                            content_type = 'image/webp'
                        else:
                            content_type = 'application/octet-stream'
                
                # 添加到文件列表
                files.append(('files', (filename, image_data, content_type)))
            
            if not files:
                self.logger.warning("批量上传图片: 没有有效的图片数据可以上传")
                return [{"error": "没有有效的图片数据", "filename": img.get("filename", "unknown")} for img in images]
            
            total_size = sum(len(img['data']) for img in images)
            size_mb = total_size / (1024 * 1024)
            self.logger.info(f"开始批量上传图片: {len(files)}个文件，总大小: {size_mb:.2f}MB")
            
            # 发送批量上传请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.download_service_url}/batch_upload",
                    files=files
                )
                response.raise_for_status()
                upload_response = response.json()
            
            # 处理批量上传结果
            results = []
            successful_uploads = upload_response.get("successful", [])
            failed_uploads = upload_response.get("failed", [])
            
            # 处理成功的上传
            for success_info in successful_uploads:
                result = {
                    "url": success_info.get("url"),
                    "resource_id": success_info.get("resource_id"),
                    "filename": success_info.get("filename"),
                    "size": success_info.get("size"),
                    "content_type": success_info.get("content_type"),
                    "message": success_info.get("message", "上传成功"),
                    "success": True
                }
                results.append(result)
                self.logger.debug(f"图片上传成功: {result['filename']} -> {result['resource_id']}")
            
            # 处理失败的上传
            for failed_info in failed_uploads:
                result = {
                    "filename": failed_info.get("filename"),
                    "error": failed_info.get("error", "上传失败"),
                    "success": False
                }
                results.append(result)
                self.logger.warning(f"图片上传失败: {result['filename']}, 原因: {result['error']}")
            
            # 优化批量上传完成提示信息
            total_images = len(images)
            successful_count = len(successful_uploads)
            failed_count = len(failed_uploads)
            
            if failed_count == 0:
                self.logger.info(f"批量上传完成 - 全部成功上传{total_images}个图片")
            else:
                self.logger.info(f"批量上传完成 - 成功上传{successful_count}个图片，失败{failed_count}个图片")
            
            return results
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"批量上传HTTP错误: {e.response.status_code} - {e.response.text}")
            return [{"error": f"HTTP错误: {e.response.status_code}", "filename": img.get("filename", "unknown")} for img in images]
        except httpx.TimeoutException:
            self.logger.error("批量上传超时")
            return [{"error": "上传超时", "filename": img.get("filename", "unknown")} for img in images]
        except Exception as e:
            self.logger.error(f"批量上传失败: {e}")
            return [{"error": str(e), "filename": img.get("filename", "unknown")} for img in images]
    
    async def upload_files_batch(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量上传文件到存储服务（用于压缩包中的文件）
        
        Args:
            files: 文件信息列表，每个元素包含：
                   {
                       "data": bytes,  # 文件字节数据
                       "filename": str,  # 文件名（包含扩展名）
                       "content_type": str (可选)  # 内容类型
                   }
            
        Returns:
            上传结果列表，每个元素包含url、resource_id等信息，失败的返回error信息
        """
        if not self.enabled:
            self.logger.warning("HTTP下载服务未启用，无法批量上传文件")
            return [{"error": "HTTP下载服务未启用", "filename": file.get("filename", "unknown")} for file in files]
        
        if not files:
            return []
        
        try:
            # 检查批量上传数量限制
            max_batch_size = int(os.getenv("MAX_BATCH_UPLOAD_SIZE", "20"))
            if len(files) > max_batch_size:
                self.logger.error(f"批量上传文件数量超过限制: {len(files)} > {max_batch_size}")
                return [{"error": f"批量上传数量超过限制({max_batch_size})", "filename": file.get("filename", "unknown")} for file in files]
            
            # 准备批量上传请求
            upload_files = []
            for i, file_info in enumerate(files):
                file_data = file_info.get("data")
                filename = file_info.get("filename", f"file_{i}.bin")
                content_type = file_info.get("content_type")
                
                if not file_data:
                    continue
                
                # 如果没有提供content_type，尝试根据文件扩展名推断
                if not content_type:
                    content_type, _ = mimetypes.guess_type(filename)
                    if not content_type:
                        content_type = 'application/octet-stream'
                
                # 添加到文件列表
                upload_files.append(('files', (filename, file_data, content_type)))
            
            if not upload_files:
                self.logger.warning("批量上传文件: 没有有效的文件数据可以上传")
                return [{"error": "没有有效的文件数据", "filename": file.get("filename", "unknown")} for file in files]
            
            total_size = sum(len(file['data']) for file in files)
            size_mb = total_size / (1024 * 1024)
            self.logger.info(f"开始批量上传文件: {len(upload_files)}个文件，总大小: {size_mb:.2f}MB")
            
            # 发送批量上传请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.download_service_url}/batch_upload",
                    files=upload_files
                )
                response.raise_for_status()
                upload_response = response.json()
            
            # 处理批量上传结果
            results = []
            successful_uploads = upload_response.get("successful", [])
            failed_uploads = upload_response.get("failed", [])
            
            # 处理成功的上传
            for success_info in successful_uploads:
                result = {
                    "url": success_info.get("url"),
                    "resource_id": success_info.get("resource_id"),
                    "filename": success_info.get("filename"),
                    "size": success_info.get("size"),
                    "content_type": success_info.get("content_type"),
                    "message": success_info.get("message", "上传成功"),
                    "success": True
                }
                results.append(result)
                self.logger.debug(f"文件上传成功: {result['filename']} -> {result['resource_id']}")
            
            # 处理失败的上传
            for failed_info in failed_uploads:
                result = {
                    "filename": failed_info.get("filename"),
                    "error": failed_info.get("error", "上传失败"),
                    "success": False
                }
                results.append(result)
                self.logger.warning(f"文件上传失败: {result['filename']}, 原因: {result['error']}")
            
            # 批量上传完成提示信息
            total_files = len(files)
            successful_count = len(successful_uploads)
            failed_count = len(failed_uploads)
            
            if failed_count == 0:
                self.logger.info(f"批量文件上传完成 - 全部成功上传{total_files}个文件")
            else:
                self.logger.info(f"批量文件上传完成 - 成功上传{successful_count}个文件，失败{failed_count}个文件")
            
            return results
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"批量文件上传HTTP错误: {e.response.status_code} - {e.response.text}")
            return [{"error": f"HTTP错误: {e.response.status_code}", "filename": file.get("filename", "unknown")} for file in files]
        except httpx.TimeoutException:
            self.logger.error("批量文件上传超时")
            return [{"error": "上传超时", "filename": file.get("filename", "unknown")} for file in files]
        except Exception as e:
            self.logger.error(f"批量文件上传失败: {e}")
            return [{"error": str(e), "filename": file.get("filename", "unknown")} for file in files]

    def get_stats(self) -> Dict[str, Any]:
        """
        获取HTTP下载存储统计信息
        
        Returns:
            统计信息字典
        """
        try:
            cache_stats = {
                "size": len(self.cache),
                "volume": self.cache.volume(),
                "hits": getattr(self.cache, 'stats', {}).get('hits', 0),
                "misses": getattr(self.cache, 'stats', {}).get('misses', 0)
            }
        except Exception:
            cache_stats = {"error": "无法获取缓存统计"}
        
        return {
            "storage_type": "http_download",
            "download_operations": self.stats,
            "cache": cache_stats,
            "configuration": {
                "download_service_url": self.download_service_url,
                "timeout": self.timeout,
                "enabled": self.enabled
            }
        }
    
    def clear_cache(self):
        """清除HTTP下载缓存"""
        try:
            self.cache.clear()
            # 同时清空文件元数据缓存
            if hasattr(self, '_file_metadata'):
                self._file_metadata.clear()
            self.logger.info("HTTP下载缓存已清空")
        except Exception as e:
            self.logger.error(f"清空HTTP下载缓存失败: {e}")
    
    def clear_url_cache(self, url: str, request=None):
        """
        清除特定URL的缓存
        
        Args:
            url: 要清除缓存的URL
            request: 请求对象（用于生成缓存键）
        """
        try:
            cache_key = self._get_cache_key(url, request)
            if cache_key in self.cache:
                del self.cache[cache_key]
                self.logger.info(f"已清除URL缓存: {url}")
            else:
                self.logger.info(f"URL未缓存: {url}")
            
            # 同时清空文件元数据
            if hasattr(self, '_file_metadata') and url in self._file_metadata:
                del self._file_metadata[url]
                
        except Exception as e:
            self.logger.error(f"清除URL缓存失败: {url}, 错误: {e}")
    
    def close(self):
        """关闭HTTP客户端并清理资源"""
        try:
            # HTTP客户端在每次请求时创建和关闭，这里主要是清理其他资源
            if hasattr(self, 'cache'):
                # 不需要关闭缓存，只是标记
                pass
            self.logger.info("HTTP下载存储客户端已关闭")
        except Exception as e:
            self.logger.error(f"关闭客户端失败: {e}")
    
    def _detect_file_type_simple(self, url: str) -> Optional[str]:
        """
        简化的文件类型检测：仅从URL提取扩展名
        类似于 core.py 中的 _detect_file_type_simple 方法
        
        Args:
            url: 资源URL
            
        Returns:
            文件扩展名（如果检测到），否则返回None
        """
        try:
            from pathlib import Path
            
            # 处理可能的查询参数情况：file.pdf?version=1
            url_clean = url.split('?')[0] if '?' in url else url
            
            ext = Path(url_clean).suffix.lower()
            
            if ext and len(ext) > 1:  # 确保不是只有一个点
                self.logger.debug(f"从URL检测到文件类型: {ext} (URL: {url})")
                return ext
            
            self.logger.debug(f"无法从URL提取有效扩展名: {url}")
            return None
            
        except Exception as e:
            self.logger.debug(f"从URL提取扩展名失败: {url}, 错误: {e}")
            return None
    
    def _is_supported_file_type(self, file_type: str) -> bool:
        """
        检查文件类型是否支持
        
        Args:
            file_type: 文件扩展名（如 '.pdf', '.jpg'）
            
        Returns:
            如果支持返回True，否则返回False
        """
        try:
            # 导入配置中的支持文件类型列表
            from ..config import SUPPORTED_DOC_TYPES, IGNORED_TYPES
            
            # 标准化扩展名格式
            if not file_type.startswith('.'):
                file_type = f'.{file_type}'
            file_type = file_type.lower()
            
            # 检查是否在支持列表中
            if file_type in SUPPORTED_DOC_TYPES:
                return True
            
            # 检查是否在忽略列表中
            if file_type in IGNORED_TYPES:
                return False
            
            # 既不在支持列表也不在忽略列表中，返回False（不支持）
            return False
            
        except Exception as e:
            self.logger.error(f"检查文件类型支持状态失败: {file_type}, 错误: {e}")
            # 出错时默认不支持，避免下载可能无法处理的文件
            return False