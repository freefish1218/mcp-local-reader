"""
PDF解析器重构的pytest测试
"""

import pytest
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from file_reader.core import FileReader
from file_reader.parsers.pdf_parser import PDFParser
from file_reader.image_cache import ImageCacheManager


def test_pdf_parser_creation():
    """测试PDF解析器创建"""
    pdf_parser = PDFParser()
    assert pdf_parser is not None
    assert hasattr(pdf_parser, 'process_document_images')
    assert hasattr(pdf_parser, 'get_cached_image')


def test_image_cache_manager_creation():
    """测试图片缓存管理器创建"""
    cache_manager = ImageCacheManager()
    assert cache_manager is not None
    
    # 测试缓存统计
    stats = cache_manager.get_cache_stats()
    assert isinstance(stats, dict)


def test_file_reader_integration():
    """测试FileReader集成"""
    file_reader = FileReader()
    assert file_reader is not None
    
    # 检查解析器
    parsers = file_reader.parsers
    assert 'pdf' in parsers
    assert 'office' in parsers
    assert 'text' in parsers
    assert 'image' in parsers
    
    # 检查PDF解析器包含图片处理混入
    pdf_parser = parsers.get('pdf')
    assert pdf_parser is not None
    assert hasattr(pdf_parser, 'process_document_images')


def test_resource_id_detection():
    """测试resource_id检测逻辑"""
    test_cases = [
        ("doc_img_pdf_1234abcd_5678efgh_p1_i0.png", True),
        ("doc_img_docx_abcd1234_efgh5678_i1.png", True),
        ("doc_img_xlsx_abcd1234_efgh5678_s0_i1.jpg", True),
        ("regular_file_123.pdf", False),
    ]
    
    for resource_id, expected_is_doc_image in test_cases:
        # 现在resource_id本身就包含扩展名，只需检查前缀
        is_doc_image = resource_id.startswith('doc_img_')
        assert is_doc_image == expected_is_doc_image, f"Failed for {resource_id}"


def test_environment_variables():
    """测试环境变量"""
    # 如果未设置，应该有默认值
    cache_size = os.getenv("IMAGE_FILE_CACHE_SIZE_MB", "1000")
    assert cache_size.isdigit()
    
    cache_root = os.getenv("CACHE_ROOT_DIR", "cache")
    assert isinstance(cache_root, str)


@pytest.mark.asyncio
async def test_pdf_parser_basic_functionality():
    """测试PDF解析器基本功能（如果有测试文件）"""
    pdf_parser = PDFParser()
    
    # 创建一个简单的PDF内容进行测试（这里只是测试解析器不会崩溃）
    # 实际的PDF解析测试需要真实的PDF文件
    try:
        # 测试空内容处理
        result = pdf_parser.parse(b"", ".pdf")
        assert not result.success  # 空内容应该失败
        assert result.error is not None
    except Exception as e:
        # 这是预期的，因为空内容不是有效的PDF
        assert "PDF" in str(e) or "解析" in str(e)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 