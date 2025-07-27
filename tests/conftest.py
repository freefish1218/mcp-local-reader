"""
测试配置文件
提供测试共享的fixture和配置
"""

import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from file_reader.storage import LocalFileStorageClient, HTTPDownloadStorageClient
from file_reader import FileReader
from file_reader.models import ReadRequest, ReadResponse, FailureType
from file_reader.parsers import PDFParser, OfficeParser, TextParser

# 添加源码路径到系统路径
os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src')


@pytest.fixture
def temp_dir():
    """创建临时目录夹具"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture  
def mock_local_client():
    """创建模拟本地文件客户端夹具"""
    client = Mock(spec=LocalFileStorageClient)
    return client


@pytest.fixture
def mock_http_client():
    """创建模拟HTTP下载客户端夹具"""
    client = Mock(spec=HTTPDownloadStorageClient)
    return client


@pytest.fixture
def file_reader_local(mock_local_client):
    """创建本地文件读取器实例夹具"""
    return FileReader(
        storage_client=mock_local_client,
        max_workers=2,
        min_content_length=5
    )


@pytest.fixture
def file_reader_http(mock_http_client):
    """创建HTTP下载文件读取器实例夹具"""
    return FileReader(
        storage_client=mock_http_client,
        max_workers=2, 
        min_content_length=5
    )


@pytest.fixture
def sample_pdf_content():
    """创建示例PDF内容"""
    # 这里创建一个最小的PDF内容（实际是PDF的字节表示）
    return b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'


@pytest.fixture
def sample_text_content():
    """创建示例文本内容"""
    return "这是一个测试文本文件的内容。\n包含中文和英文 English text.\n第二行内容。".encode('utf-8')


@pytest.fixture
def sample_docx_content():
    """创建示例Word文档内容"""
    # 这里返回一个基本的docx文件字节内容
    return b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00'  # 简化的docx文件头


@pytest.fixture
def read_request():
    """创建读取请求夹具"""
    return ReadRequest(
        resource_ids=["https://example.com/test1.pdf", "https://example.com/test2.txt", "https://example.com/test3.docx"],
        referer="https://test.com",
        max_size=5 * 1024 * 1024  # 5MB
    )


@pytest.fixture
def mock_env_vars():
    """模拟环境变量"""
    env_vars = {
        'DOWNLOAD_SERVICE_URL': 'http://localhost:8080',
        'DOWNLOAD_SERVICE_TIMEOUT': '300',
        'OPENAI_API_KEY': 'test_openai_key',
        'OPENAI_BASE_URL': 'https://api.openai.com/v1',
        'OPENAI_MODEL': 'gpt-4o',
        'FILE_READER_MAX_FILE_SIZE_MB': '20',
        'FILE_READER_CACHE_SIZE_MB': '500'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def sample_json_content():
    """创建示例JSON内容"""
    json_data = {
        "name": "测试用户",
        "age": 25,
        "city": "北京",
        "languages": ["中文", "English"],
        "profile": {
            "education": "本科",
            "experience": "3年"
        },
        "active": True,
        "score": 95.5
    }
    return json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8')


@pytest.fixture
def sample_invalid_json_content():
    """创建无效JSON内容"""
    return b'{"name": "test", "incomplete": '