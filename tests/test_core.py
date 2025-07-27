"""
FileReader核心功能测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from file_reader.core import FileReader
from file_reader.models import ReadRequest, FailureType
from file_reader.storage import HTTPDownloadStorageClient


class TestFileReader:
    """FileReader测试类"""
    
    @pytest.fixture
    def mock_storage_client(self):
        """创建mock存储客户端"""
        mock_client = Mock(spec=HTTPDownloadStorageClient)
        mock_client.download_files_batch = AsyncMock()
        mock_client.get_stats.return_value = {
            "downloads": 0,
            "cache_hits": 0,
            "total_size": 0,
            "errors": 0
        }
        mock_client.clear_cache = Mock()
        return mock_client
    
    @pytest.fixture
    def file_reader(self, mock_storage_client):
        """创建FileReader实例"""
        return FileReader(storage_client=mock_storage_client)
    
    @pytest.mark.asyncio
    async def test_successful_text_file_processing(self, file_reader, mock_storage_client):
        """测试成功处理文本文件"""
        # 准备测试数据
        sample_text_content = b"Hello, this is a test text file."
        
        # 模拟批量下载成功
        mock_storage_client.download_files_batch.return_value = {
            "http://example.com/test.txt": sample_text_content
        }
        
        # 创建请求
        request = ReadRequest(
            resource_ids=["http://example.com/test.txt"],
            max_size=1024*1024  # 1MB
        )
        
        # 执行读取
        response = await file_reader.read_files(request)
        
        # 验证结果
        assert len(response.contents) == 1
        assert len(response.failed) == 0
        assert response.contents[0].resource_id == "http://example.com/test.txt"
        
        # 验证调用
        mock_storage_client.download_files_batch.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_download_failure(self, file_reader, mock_storage_client):
        """测试下载失败的处理"""
        # 模拟下载失败
        mock_storage_client.download_files_batch.return_value = {}
        mock_storage_client._download_errors = {
            "http://example.com/nonexistent.txt": {
                "error_type": "NOT_FOUND",
                "error_message": "文件未找到"
            }
        }
        
        # 创建请求
        request = ReadRequest(
            resource_ids=["http://example.com/nonexistent.txt"],
            max_size=1024*1024
        )
        
        # 执行读取
        response = await file_reader.read_files(request)
        
        # 验证结果
        assert len(response.contents) == 0
        assert len(response.failed) == 1
        assert response.failed[0].resource_id == "http://example.com/nonexistent.txt"
        assert response.failed[0].type == FailureType.NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_file_too_large(self, file_reader, mock_storage_client):
        """测试文件过大的处理"""
        # 准备大文件内容
        large_content = b"x" * (2 * 1024 * 1024)  # 2MB
        
        # 模拟下载成功但文件过大
        mock_storage_client.download_files_batch.return_value = {
            "http://example.com/large.txt": large_content
        }
        
        # 创建请求，限制1MB
        request = ReadRequest(
            resource_ids=["http://example.com/large.txt"],
            max_size=1024*1024  # 1MB
        )
        
        # 执行读取
        response = await file_reader.read_files(request)
        
        # 验证结果
        assert len(response.contents) == 0
        assert len(response.failed) == 1
        assert response.failed[0].type == FailureType.SIZE_EXCEEDED
    
    @pytest.mark.asyncio
    async def test_unsupported_file_type(self, file_reader, mock_storage_client):
        """测试不支持的文件类型"""
        # 模拟下载成功
        mock_storage_client.download_files_batch.return_value = {
            "http://example.com/test.unknown": b"unknown content"
        }
        
        # 创建请求
        request = ReadRequest(
            resource_ids=["http://example.com/test.unknown"],
            max_size=1024*1024
        )
        
        # 执行读取
        response = await file_reader.read_files(request)
        
        # 验证结果
        assert len(response.contents) == 0
        assert len(response.failed) == 1
        assert response.failed[0].type == FailureType.UNSUPPORTED_TYPE
    
    @pytest.mark.asyncio
    async def test_parse_failure(self, file_reader, mock_storage_client):
        """测试解析失败的处理"""
        # 模拟下载成功但内容无效
        mock_storage_client.download_files_batch.return_value = {
            "http://example.com/invalid.pdf": b"invalid pdf content"
        }
        
        # 创建请求
        request = ReadRequest(
            resource_ids=["http://example.com/invalid.pdf"],
            max_size=1024*1024
        )
        
        # 执行读取
        response = await file_reader.read_files(request)
        
        # 验证结果
        assert len(response.contents) == 0
        assert len(response.failed) == 1
        assert response.failed[0].type == FailureType.PARSE_ERROR
    
    def test_file_type_detection(self, file_reader):
        """测试文件类型检测"""
        # 测试PDF文件
        assert file_reader._detect_file_type_simple("http://example.com/test.pdf") == ".pdf"
        
        # 测试带查询参数的URL
        assert file_reader._detect_file_type_simple("http://example.com/test.pdf?version=1") == ".pdf"
        
        # 测试不支持的文件类型
        assert file_reader._detect_file_type_simple("http://example.com/test.xyz") is None
        
        # 测试没有扩展名的文件
        assert file_reader._detect_file_type_simple("http://example.com/test") is None
    
    def test_get_stats(self, file_reader, mock_storage_client):
        """测试统计信息获取"""
        # 设置一些统计数据
        file_reader.stats["total_requests"] = 5
        file_reader.stats["successful_reads"] = 3
        file_reader.stats["failed_reads"] = 2
        
        # 获取统计信息
        stats = file_reader.get_stats()
        
        # 验证结构
        assert "file_reader" in stats
        assert "storage" in stats
        assert "parsers" in stats
        
        # 验证数据
        assert stats["file_reader"]["total_requests"] == 5
        assert stats["file_reader"]["successful_reads"] == 3
        assert stats["file_reader"]["failed_reads"] == 2
    
    @pytest.mark.asyncio
    async def test_batch_processing_mixed_results(self, file_reader, mock_storage_client):
        """测试批量处理混合结果"""
        # 准备测试数据：一个成功，一个失败
        sample_text_content = b"Hello, this is a test text file."
        
        # 模拟批量下载：一个成功，一个失败
        mock_storage_client.download_files_batch.return_value = {
            "http://example.com/success.txt": sample_text_content
        }
        mock_storage_client._download_errors = {
            "http://example.com/failed.txt": {
                "error_type": "NETWORK_ERROR",
                "error_message": "网络连接失败"
            }
        }
        
        # 创建请求
        request = ReadRequest(
            resource_ids=["http://example.com/success.txt", "http://example.com/failed.txt"],
            max_size=1024*1024
        )
        
        # 执行读取
        response = await file_reader.read_files(request)
        
        # 验证结果
        assert len(response.contents) == 1
        assert len(response.failed) == 1
        assert response.contents[0].resource_id == "http://example.com/success.txt"
        assert response.failed[0].resource_id == "http://example.com/failed.txt"
        assert response.failed[0].type == FailureType.NETWORK_ERROR
    
    @pytest.mark.asyncio
    async def test_processing_exception_handling(self, file_reader, mock_storage_client):
        """测试处理过程中的异常处理"""
        # 模拟下载成功
        mock_storage_client.download_files_batch.return_value = {
            "http://example.com/test.txt": b"test content"
        }
        
        # 模拟解析器抛出异常
        with patch.object(file_reader.parsers['text'], 'parse') as mock_parse:
            mock_parse.side_effect = Exception("解析器内部错误")
            
            # 创建请求
            request = ReadRequest(
                resource_ids=["http://example.com/test.txt"],
                max_size=1024*1024
            )
            
            # 执行读取
            response = await file_reader.read_files(request)
            
            # 验证结果
            assert len(response.contents) == 0
            assert len(response.failed) == 1
            assert response.failed[0].type == FailureType.OTHER
            assert "解析器内部错误" in response.failed[0].error_message
    
    def test_clear_cache(self, file_reader, mock_storage_client):
        """测试缓存清除"""
        file_reader.clear_cache()
        mock_storage_client.clear_cache.assert_called_once()


class TestLocalFileStorageIntegration:
    """本地文件存储集成测试"""
    
    def test_local_file_reading_no_longer_supported(self):
        """测试本地文件读取不再受支持"""
        # 由于移除了download_file方法，本地文件存储客户端不再受支持
        from file_reader.storage import LocalFileStorageClient
        
        # 创建本地文件存储客户端
        local_client = LocalFileStorageClient()
        
        # 验证它没有download_files_batch方法（只有HTTPDownloadStorageClient支持）
        assert not hasattr(local_client, 'download_files_batch')
        
        # FileReader现在仅支持HTTPDownloadStorageClient，可以正常工作
        # 但是在实际调用read_files时会因为缺少download_files_batch方法而失败
        file_reader = FileReader(storage_client=local_client)
        assert file_reader is not None 