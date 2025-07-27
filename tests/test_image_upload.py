"""
测试图片上传功能
验证在文档解析过程中，图片被正确缓存和上传到存储服务
"""

import os
import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from file_reader.image_cache import ImageCacheManager
from file_reader.storage import HTTPDownloadStorageClient
from file_reader.parsers import PDFParser


class MockHTTPDownloadStorageClient:
    """模拟的HTTP下载存储客户端，用于测试图片上传"""
    
    def __init__(self):
        self.uploaded_images = []
        self.upload_results = {}
        self.enabled = True
        
    async def upload_image(self, image_data: bytes, filename: str, content_type: str = None):
        """模拟上传图片"""
        # 模拟成功上传
        result = {
            "url": f"http://storage.example.com/{filename}",
            "resource_id": f"upload_{len(self.uploaded_images) + 1}_{filename}",
            "filename": filename,
            "size": len(image_data),
            "content_type": content_type or "image/png",
            "message": "上传成功"
        }
        
        self.uploaded_images.append({
            "filename": filename,
            "size": len(image_data),
            "content_type": content_type,
            "data": image_data
        })
        
        return result
    
    def get_stats(self):
        """获取存储客户端统计信息"""
        return {
            "total_uploads": len(self.uploaded_images),
            "total_upload_size": sum(img["size"] for img in self.uploaded_images)
        }


@pytest.fixture
def mock_storage_client():
    """提供模拟的存储客户端"""
    return MockHTTPDownloadStorageClient()


@pytest.fixture
def temp_image_files():
    """创建临时图片文件用于测试"""
    temp_dir = tempfile.mkdtemp()
    image_files = []
    
    # 创建几个模拟图片文件
    for i in range(3):
        image_file = Path(temp_dir) / f"test_image_{i}.png"
        # 创建简单的PNG文件数据（模拟）
        png_data = b'\x89PNG\r\n\x1a\n' + b'test_image_data_' + str(i).encode() + b'_end'
        with open(image_file, 'wb') as f:
            f.write(png_data)
        image_files.append(image_file)
    
    yield image_files, temp_dir
    
    # 清理临时文件
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestImageUpload:
    """测试图片上传功能"""
    
    def test_image_cache_manager_initialization(self, mock_storage_client):
        """测试图片缓存管理器的初始化"""
        # 测试启用上传的情况
        os.environ["IMAGE_AUTO_UPLOAD_ENABLED"] = "true"
        manager = ImageCacheManager(storage_client=mock_storage_client)
        
        assert manager.storage_client == mock_storage_client
        assert manager.upload_enabled == True
        assert manager.upload_timeout == 60  # 默认值
        assert manager.max_concurrent_uploads == 3  # 默认值
    
    def test_image_cache_manager_disabled_upload(self, mock_storage_client):
        """测试禁用上传的情况"""
        os.environ["IMAGE_AUTO_UPLOAD_ENABLED"] = "false"
        manager = ImageCacheManager(storage_client=mock_storage_client)
        
        assert manager.upload_enabled == False
    
    def test_cache_document_images_with_upload(self, mock_storage_client, temp_image_files):
        """测试文档图片缓存和上传功能"""
        image_files, temp_dir = temp_image_files
        
        # 启用上传
        os.environ["IMAGE_AUTO_UPLOAD_ENABLED"] = "true"
        manager = ImageCacheManager(storage_client=mock_storage_client)
        
        doc_info = {
            'markdown_content': 'Test markdown content with images',
            'doc_type': 'pdf',
            'temp_image_dir': temp_dir
        }
        
        # 执行图片缓存
        processed_markdown, image_resources = manager.cache_document_images(image_files, doc_info)
        
        # 验证返回结果
        assert isinstance(processed_markdown, str)
        assert isinstance(image_resources, list)
        assert len(image_resources) == len(image_files)
        
        # 验证图片资源信息
        for i, resource in enumerate(image_resources):
            assert 'resource_id' in resource
            assert 'filename' in resource
            assert 'size' in resource
            assert 'doc_type' in resource
            assert resource['doc_type'] == 'pdf'
            assert resource['filename'] == f'test_image_{i}.png'
        
        # 等待异步上传完成（模拟）
        import time
        time.sleep(0.1)  # 给异步任务一些时间
        
        # 验证上传统计
        upload_stats = manager.get_upload_stats()
        assert 'total_uploads' in upload_stats
        assert 'successful_uploads' in upload_stats
        assert 'failed_uploads' in upload_stats
    
    def test_cache_document_images_without_upload(self, mock_storage_client, temp_image_files):
        """测试禁用上传时的图片缓存功能"""
        image_files, temp_dir = temp_image_files
        
        # 禁用上传
        os.environ["IMAGE_AUTO_UPLOAD_ENABLED"] = "false"
        manager = ImageCacheManager(storage_client=mock_storage_client)
        
        doc_info = {
            'markdown_content': 'Test markdown content with images',
            'doc_type': 'pdf',
            'temp_image_dir': temp_dir
        }
        
        # 执行图片缓存
        processed_markdown, image_resources = manager.cache_document_images(image_files, doc_info)
        
        # 验证返回结果
        assert isinstance(processed_markdown, str)
        assert isinstance(image_resources, list)
        assert len(image_resources) == len(image_files)
        
        # 验证没有上传任务被创建
        assert len(mock_storage_client.uploaded_images) == 0
    
    def test_pdf_parser_with_storage_client(self, mock_storage_client):
        """测试PDF解析器集成存储客户端"""
        parser = PDFParser(storage_client=mock_storage_client)
        
        assert parser.storage_client == mock_storage_client
        assert hasattr(parser, 'set_storage_client')
        
        # 测试设置存储客户端
        new_client = MockHTTPDownloadStorageClient()
        parser.set_storage_client(new_client)
        assert parser.storage_client == new_client
    
    @pytest.mark.asyncio
    async def test_async_upload_image(self, mock_storage_client):
        """测试异步图片上传"""
        test_image_data = b'test_image_data'
        test_filename = 'test.png'
        
        result = await mock_storage_client.upload_image(test_image_data, test_filename)
        
        assert result is not None
        assert result['filename'] == test_filename
        assert result['size'] == len(test_image_data)
        assert 'url' in result
        assert 'resource_id' in result
        
        # 验证图片被记录
        assert len(mock_storage_client.uploaded_images) == 1
        assert mock_storage_client.uploaded_images[0]['filename'] == test_filename
    
    def test_upload_configuration_from_env(self):
        """测试从环境变量读取上传配置"""
        os.environ["IMAGE_AUTO_UPLOAD_ENABLED"] = "true"
        os.environ["IMAGE_UPLOAD_TIMEOUT"] = "120"
        os.environ["IMAGE_UPLOAD_MAX_CONCURRENT"] = "5"
        
        manager = ImageCacheManager()
        
        assert manager.upload_enabled == True
        assert manager.upload_timeout == 120
        assert manager.max_concurrent_uploads == 5
    
    def test_upload_stats(self, mock_storage_client):
        """测试上传统计功能"""
        manager = ImageCacheManager(storage_client=mock_storage_client)
        
        # 初始统计
        stats = manager.get_upload_stats()
        assert stats['total_uploads'] == 0
        assert stats['successful_uploads'] == 0
        assert stats['failed_uploads'] == 0
        assert stats['upload_success_rate'] == 0
        
        # 模拟上传统计更新
        manager.upload_stats['total_uploads'] = 10
        manager.upload_stats['successful_uploads'] = 8
        manager.upload_stats['failed_uploads'] = 2
        
        stats = manager.get_upload_stats()
        assert stats['total_uploads'] == 10
        assert stats['successful_uploads'] == 8
        assert stats['failed_uploads'] == 2
        assert stats['upload_success_rate'] == 80.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 