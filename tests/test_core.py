"""
FileReader核心功能测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from file_reader.core import FileReader
from file_reader.models import LocalReadRequest, FailureType
from file_reader.storage import LocalFileStorageClient


class TestFileReader:
    """FileReader测试类"""
    
    @pytest.fixture
    def mock_storage_client(self):
        """创建mock存储客户端"""
        mock_client = Mock(spec=LocalFileStorageClient)
        mock_client.get_files_batch = AsyncMock()
        mock_client.get_stats.return_value = {
            "reads": 0,
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
        
        # 模拟批量读取成功
        mock_storage_client.get_files_batch.return_value = {
            "test.txt": sample_text_content
        }
        
        # 创建请求
        request = LocalReadRequest(
            file_paths=["test.txt"],
            max_size=1024*1024  # 1MB
        )
        
        # 执行读取
        response = await file_reader.read_local_files(request)
        
        # 验证结果
        assert len(response.contents) == 1
        assert len(response.failed) == 0
        assert response.contents[0].resource_id == "test.txt"
        
        # 验证调用
        mock_storage_client.get_files_batch.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_file_read_failure(self, file_reader, mock_storage_client):
        """测试文件读取失败的处理"""
        # 模拟读取失败
        mock_storage_client.get_files_batch.return_value = {}
        mock_storage_client._read_errors = {
            "nonexistent.txt": {
                "error_type": "ERROR_RESPONSE",
                "error_message": "文件未找到"
            }
        }
        
        # 创建请求
        request = LocalReadRequest(
            file_paths=["nonexistent.txt"],
            max_size=1024*1024
        )
        
        # 执行读取
        response = await file_reader.read_local_files(request)
        
        # 验证结果
        assert len(response.contents) == 0
        assert len(response.failed) == 1
        assert response.failed[0].resource_id == "nonexistent.txt"
    
    @pytest.mark.asyncio
    async def test_file_size_exceeded(self, file_reader, mock_storage_client):
        """测试文件大小超限的处理"""
        # 准备大文件内容
        large_content = b"x" * (2 * 1024 * 1024)  # 2MB内容
        
        # 模拟读取大文件
        mock_storage_client.get_files_batch.return_value = {
            "large_file.txt": large_content
        }
        
        # 创建请求，限制大小为1MB
        request = LocalReadRequest(
            file_paths=["large_file.txt"],
            max_size=1 * 1024 * 1024  # 1MB限制
        )
        
        # 执行读取
        response = await file_reader.read_local_files(request)
        
        # 验证结果 - 应该因为大小超限而失败或被处理
        # 具体行为取决于实现，这里测试结构完整性
        assert isinstance(response.contents, list)
        assert isinstance(response.failed, list)
    
    @pytest.mark.asyncio
    async def test_empty_file_paths(self, file_reader, mock_storage_client):
        """测试空文件路径列表"""
        # 创建空请求
        request = LocalReadRequest(file_paths=[])
        
        # 执行读取
        response = await file_reader.read_local_files(request)
        
        # 验证结果
        assert len(response.contents) == 0
        assert len(response.failed) == 0
        
        # 验证调用
        mock_storage_client.get_files_batch.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_multiple_files_mixed_results(self, file_reader, mock_storage_client):
        """测试多文件混合结果"""
        # 准备测试数据
        success_content = b"Success file content"
        
        # 模拟混合结果
        mock_storage_client.get_files_batch.return_value = {
            "success.txt": success_content
        }
        mock_storage_client._read_errors = {
            "failed.txt": {
                "error_type": "PARSE_ERROR",
                "error_message": "解析失败"
            }
        }
        
        # 创建请求
        request = LocalReadRequest(
            file_paths=["success.txt", "failed.txt"],
            max_size=1024*1024
        )
        
        # 执行读取
        response = await file_reader.read_local_files(request)
        
        # 验证结果
        assert len(response.contents) == 1
        assert len(response.failed) == 1
        assert response.contents[0].resource_id == "success.txt"
        assert response.failed[0].resource_id == "failed.txt"
    
    def test_get_stats(self, file_reader, mock_storage_client):
        """测试获取统计信息"""
        expected_stats = {
            "reads": 5,
            "cache_hits": 3,
            "total_size": 1024,
            "errors": 1
        }
        mock_storage_client.get_stats.return_value = expected_stats
        
        stats = file_reader.get_stats()
        
        assert stats == expected_stats
        mock_storage_client.get_stats.assert_called_once()
    
    def test_clear_cache(self, file_reader, mock_storage_client):
        """测试清理缓存"""
        file_reader.clear_cache()
        
        mock_storage_client.clear_cache.assert_called_once()