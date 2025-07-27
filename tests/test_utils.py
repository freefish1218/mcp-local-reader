"""
测试工具函数
"""

import pytest
import logging
from file_reader.utils import (
    get_logger, get_file_extension, detect_file_type_from_content,
    normalize_content, extract_base_domain, format_file_size
)
from file_reader.config import SUPPORTED_DOC_TYPES


class TestGetLogger:
    """测试日志记录器功能"""
    
    def test_get_logger_default(self):
        """测试获取默认日志记录器"""
        logger = get_logger("test.logger")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.logger"
        assert logger.level == logging.INFO
    
    def test_get_logger_with_level(self):
        """测试指定级别的日志记录器"""
        logger = get_logger("test.debug", "DEBUG")
        
        assert logger.level == logging.DEBUG
    
    def test_get_logger_singleton(self):
        """测试日志记录器单例特性"""
        logger1 = get_logger("test.singleton")
        logger2 = get_logger("test.singleton")
        
        assert logger1 is logger2


class TestGetFileExtension:
    """测试文件扩展名获取功能"""
    
    def test_get_extension_from_filename(self):
        """测试从文件名获取扩展名"""
        assert get_file_extension("test.pdf") == ".pdf"
        assert get_file_extension("document.DOCX") == ".docx"  # 测试大小写
        assert get_file_extension("data.xlsx") == ".xlsx"
        assert get_file_extension("image.JPG") == ".jpg"
    
    def test_get_extension_from_content_type(self):
        """测试从MIME类型获取扩展名"""
        assert get_file_extension("", "application/pdf") == ".pdf"
        assert get_file_extension("", "text/plain") == ".txt"
        assert get_file_extension("", "application/vnd.openxmlformats-officedocument.wordprocessingml.document") == ".docx"
    
    def test_get_extension_priority(self):
        """测试扩展名获取优先级（文件名优先）"""
        result = get_file_extension("test.pdf", "text/plain")
        assert result == ".pdf"  # 文件名优先
    
    def test_get_extension_none(self):
        """测试无法获取扩展名的情况"""
        assert get_file_extension("", "") is None
        assert get_file_extension("no_extension", "") is None
        assert get_file_extension("", "unknown/type") is None


class TestDetectFileTypeFromContent:
    """测试从文件内容检测文件类型"""
    
    def test_detect_pdf(self):
        """测试PDF文件检测"""
        pdf_content = b'%PDF-1.4\n1 0 obj'
        assert detect_file_type_from_content(pdf_content) == ".pdf"
    
    def test_detect_docx(self):
        """测试DOCX文件检测"""
        # ZIP格式头部 + word/标识
        docx_content = b'PK\x03\x04' + b'\x00' * 500 + b'word/' + b'\x00' * 400
        assert detect_file_type_from_content(docx_content) == ".docx"
    
    def test_detect_xlsx(self):
        """测试XLSX文件检测"""
        xlsx_content = b'PK\x03\x04' + b'\x00' * 500 + b'xl/' + b'\x00' * 400
        assert detect_file_type_from_content(xlsx_content) == ".xlsx"
    
    def test_detect_pptx(self):
        """测试PPTX文件检测"""
        pptx_content = b'PK\x03\x04' + b'\x00' * 500 + b'ppt/' + b'\x00' * 400
        assert detect_file_type_from_content(pptx_content) == ".pptx"
    
    def test_detect_old_office(self):
        """测试旧版Office文档检测"""
        old_office_content = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + b'\x00' * 100
        assert detect_file_type_from_content(old_office_content) == ".doc"
    
    def test_detect_text(self):
        """测试文本文件检测"""
        text_content = "这是一个测试文本".encode('utf-8')
        assert detect_file_type_from_content(text_content) == ".txt"
    
    def test_detect_empty_content(self):
        """测试空内容"""
        assert detect_file_type_from_content(b'') is None
        assert detect_file_type_from_content(b'123') is None  # 太短
    
    def test_detect_unknown_content(self):
        """测试未知内容"""
        unknown_content = b'\xff\xfe\xfd\xfc' + b'\x00' * 100
        assert detect_file_type_from_content(unknown_content) is None


class TestNormalizeContent:
    """测试内容规范化功能"""
    
    def test_normalize_spaces(self):
        """测试空格规范化"""
        content = "这是   一个    测试   文本"
        normalized = normalize_content(content)
        assert normalized == "这是 一个 测试 文本"
    
    def test_normalize_newlines(self):
        """测试换行符规范化"""
        content = "第一行\n\n\n\n第二行\n\n\n第三行"
        normalized = normalize_content(content)
        # normalize_content会将所有空白字符（包括换行符）替换为单个空格
        assert normalized == "第一行 第二行 第三行"
    
    def test_normalize_mixed_whitespace(self):
        """测试混合空白字符规范化"""
        content = "  \t这是\n\n一个  \t测试\n\n\n文本  \t"
        normalized = normalize_content(content)
        assert "这是" in normalized
        assert "一个" in normalized
        assert "测试" in normalized
        assert "文本" in normalized
    
    def test_normalize_empty_content(self):
        """测试空内容规范化"""
        assert normalize_content("") == ""
        assert normalize_content("   ") == ""


class TestExtractBaseDomain:
    """测试域名提取功能"""
    
    def test_extract_basic_domain(self):
        """测试基本域名提取"""
        assert extract_base_domain("https://example.com/path") == "example.com"
        assert extract_base_domain("http://test.org") == "test.org"
    
    def test_extract_www_domain(self):
        """测试带www的域名提取"""
        assert extract_base_domain("https://www.example.com") == "example.com"
        assert extract_base_domain("http://www.test.org/page") == "test.org"
    
    def test_extract_subdomain(self):
        """测试子域名提取"""
        assert extract_base_domain("https://api.example.com") == "api.example.com"
        assert extract_base_domain("http://cdn.test.org") == "cdn.test.org"
    
    def test_extract_invalid_url(self):
        """测试无效URL"""
        # 无效URL会返回空字符串（因为netloc为空）而不是None
        assert extract_base_domain("not-a-url") == ""
        assert extract_base_domain("") == ""
        assert extract_base_domain("://invalid") == ""


class TestFormatFileSize:
    """测试文件大小格式化功能"""
    
    def test_format_bytes(self):
        """测试字节格式化"""
        assert format_file_size(0) == "0B"
        assert format_file_size(100) == "100.0B"
        assert format_file_size(1023) == "1023.0B"
    
    def test_format_kilobytes(self):
        """测试KB格式化"""
        assert format_file_size(1024) == "1.0KB"
        assert format_file_size(1536) == "1.5KB"
        assert format_file_size(1024 * 1023) == "1023.0KB"
    
    def test_format_megabytes(self):
        """测试MB格式化"""
        assert format_file_size(1024 * 1024) == "1.0MB"
        assert format_file_size(1024 * 1024 * 2.5) == "2.5MB"
    
    def test_format_gigabytes(self):
        """测试GB格式化"""
        gb = 1024 * 1024 * 1024
        assert format_file_size(gb) == "1.0GB"
        assert format_file_size(int(gb * 1.5)) == "1.5GB"
    
    def test_format_terabytes(self):
        """测试TB格式化"""
        tb = 1024 * 1024 * 1024 * 1024
        assert format_file_size(tb) == "1.0TB"


class TestConstants:
    """测试常量定义"""
    
    def test_supported_doc_types(self):
        """测试支持的文档类型"""
        assert '.pdf' in SUPPORTED_DOC_TYPES
        assert '.docx' in SUPPORTED_DOC_TYPES
        assert '.xlsx' in SUPPORTED_DOC_TYPES
        assert '.txt' in SUPPORTED_DOC_TYPES
        assert '.rtf' in SUPPORTED_DOC_TYPES
    
    def test_image_types_in_supported(self):
        """测试图像类型已包含在支持的文档类型中"""
        assert '.jpg' in SUPPORTED_DOC_TYPES
        assert '.jpeg' in SUPPORTED_DOC_TYPES
        assert '.png' in SUPPORTED_DOC_TYPES
        assert '.gif' in SUPPORTED_DOC_TYPES
        assert '.bmp' in SUPPORTED_DOC_TYPES
        assert '.webp' in SUPPORTED_DOC_TYPES 