"""
测试数据模型
"""

import pytest
from file_reader.models import (
    ReadRequest, ReadResponse, FileContent, FailedFile, 
    FailureType, ParseResult, OCRRequest, OCRResponse, UrlWithReferer
)


class TestReadRequest:
    """测试读取请求模型"""
    
    def test_read_request_creation(self):
        """测试读取请求创建"""
        request = ReadRequest(
            resource_ids=["file1.pdf", "file2.txt"],
            referer_map={"file1.pdf": "https://example.com"},
            max_size=1024*1024
        )
        
        assert request.resource_ids == ["file1.pdf", "file2.txt"]
        assert request.referer_map == {"file1.pdf": "https://example.com"}
        assert request.max_size == 1024*1024
    
    def test_read_request_default_values(self):
        """测试读取请求默认值"""
        request = ReadRequest(resource_ids=["file1.pdf"])
        
        assert request.resource_ids == ["file1.pdf"]
        assert request.referer_map is None
        # 默认值来自环境变量，这里不具体测试数值
    
    def test_read_request_validation(self):
        """测试读取请求验证"""
        # 空的resource_ids应该可以创建
        request = ReadRequest(resource_ids=[])
        assert request.resource_ids == []
    
    def test_per_url_referer(self):
        """测试per-URL referer功能"""
        # 测试带referer_map的请求
        request = ReadRequest(
            resource_ids=["url1", "url2", "url3"],
            referer_map={
                "url1": "https://site1.com",
                "url2": "https://site2.com"
                # url3没有指定专属referer
            }
        )
        
        # 测试get_referer_for_url方法
        assert request.get_referer_for_url("url1") == "https://site1.com"
        assert request.get_referer_for_url("url2") == "https://site2.com"
        assert request.get_referer_for_url("url3") is None  # 没有指定referer
        assert request.get_referer_for_url("url4") is None  # 不存在的URL返回None
    
    def test_per_url_referer_no_default(self):
        """测试没有默认referer的per-URL referer功能"""
        request = ReadRequest(
            resource_ids=["url1", "url2"],
            referer_map={"url1": "https://site1.com"}
        )
        
        assert request.get_referer_for_url("url1") == "https://site1.com"
        assert request.get_referer_for_url("url2") is None  # 没有默认referer
    
    def test_per_url_referer_no_map(self):
        """测试没有referer_map时的行为"""
        request = ReadRequest(
            resource_ids=["url1", "url2"]
        )
        
        assert request.get_referer_for_url("url1") is None
        assert request.get_referer_for_url("url2") is None


class TestReadResponse:
    """测试读取响应模型"""
    
    def test_read_response_creation(self):
        """测试读取响应创建"""
        response = ReadResponse()
        
        assert response.contents == []
        assert response.failed == []
    
    def test_add_content(self):
        """测试添加成功内容"""
        response = ReadResponse()
        response.add_content("file1.pdf", "这是PDF的内容")
        
        assert len(response.contents) == 1
        assert response.contents[0].resource_id == "file1.pdf"
        assert response.contents[0].content == "这是PDF的内容"
    
    def test_add_failure(self):
        """测试添加失败记录"""
        response = ReadResponse()
        response.add_failure("file1.pdf", FailureType.PARSE_ERROR, "解析失败")
        
        assert len(response.failed) == 1
        assert response.failed[0].resource_id == "file1.pdf"
        assert response.failed[0].type == FailureType.PARSE_ERROR
        assert response.failed[0].error_message == "解析失败"
    
    def test_mixed_results(self):
        """测试混合结果"""
        response = ReadResponse()
        response.add_content("file1.pdf", "PDF内容")
        response.add_failure("file2.txt", FailureType.NETWORK_ERROR, "下载失败")
        
        assert len(response.contents) == 1
        assert len(response.failed) == 1


class TestFailureType:
    """测试失败类型枚举"""
    
    def test_failure_types(self):
        """测试失败类型值"""
        assert FailureType.NOT_FOUND == "not_found"
        assert FailureType.NETWORK_ERROR == "network_error"
        assert FailureType.PARSE_ERROR == "parse_error"
        assert FailureType.OCR_ERROR == "ocr_error"
        assert FailureType.UNSUPPORTED_TYPE == "unsupported_type"
        assert FailureType.SIZE_EXCEEDED == "size_exceeded"
        assert FailureType.TIMEOUT == "timeout"
        assert FailureType.FORBIDDEN == "forbidden"
        assert FailureType.SERVER_ERROR == "server_error"
        assert FailureType.OTHER == "other"


class TestParseResult:
    """测试解析结果模型"""
    
    def test_success_result(self):
        """测试成功解析结果"""
        result = ParseResult(
            success=True,
            content="解析的内容",
            doc_type="pdf",
            metadata={"pages": 3}
        )
        
        assert result.success is True
        assert result.content == "解析的内容"
        assert result.doc_type == "pdf"
        assert result.metadata["pages"] == 3
        assert result.error is None
    
    def test_failure_result(self):
        """测试失败解析结果"""
        result = ParseResult(
            success=False,
            error="解析失败"
        )
        
        assert result.success is False
        assert result.content is None
        assert result.doc_type is None
        assert result.error == "解析失败"
    
    def test_default_values(self):
        """测试默认值"""
        result = ParseResult(success=True)
        
        assert result.success is True
        assert result.content is None
        assert result.doc_type is None
        assert result.metadata == {}
        assert result.error is None


class TestOCRModels:
    """测试OCR相关模型"""
    
    def test_ocr_request(self):
        """测试OCR请求模型"""
        request = OCRRequest(
            image_data=b"image_bytes",
            image_format="jpg",
            language="zh"
        )
        
        assert request.image_data == b"image_bytes"
        assert request.image_format == "jpg"
        assert request.language == "zh"
    
    def test_ocr_request_default_language(self):
        """测试OCR请求默认语言"""
        request = OCRRequest(
            image_data=b"image_bytes",
            image_format="png"
        )
        
        assert request.language == "zh"  # 默认中文
    
    def test_ocr_response_success(self):
        """测试OCR成功响应"""
        response = OCRResponse(
            success=True,
            text="识别的文本",
            confidence=0.95
        )
        
        assert response.success is True
        assert response.text == "识别的文本"
        assert response.confidence == 0.95
        assert response.error is None
    
    def test_ocr_response_failure(self):
        """测试OCR失败响应"""
        response = OCRResponse(
            success=False,
            error="识别失败"
        )
        
        assert response.success is False
        assert response.text is None
        assert response.confidence is None
        assert response.error == "识别失败"


class TestUrlWithReferer:
    """测试URL和Referer模型"""
    
    def test_url_with_referer_creation(self):
        """测试UrlWithReferer创建"""
        url_obj = UrlWithReferer(
            url="https://example.com/file.pdf",
            referer="https://example.com"
        )
        
        assert url_obj.url == "https://example.com/file.pdf"
        assert url_obj.referer == "https://example.com"
    
    def test_url_without_referer(self):
        """测试没有referer的URL"""
        url_obj = UrlWithReferer(url="https://example.com/file.pdf")
        
        assert url_obj.url == "https://example.com/file.pdf"
        assert url_obj.referer is None
    
    def test_url_with_referer_integration(self):
        """测试UrlWithReferer与ReadRequest的集成"""
        # 模拟工具函数中的处理逻辑
        urls = [
            UrlWithReferer(url="https://site1.com/file1.pdf", referer="https://site1.com"),
            UrlWithReferer(url="https://site2.com/file2.pdf", referer="https://site2.com"),
            UrlWithReferer(url="https://site3.com/file3.pdf")  # 没有referer
        ]
        
        # 提取URL列表和构建referer映射
        url_list = [item.url for item in urls]
        referer_map = {}
        for item in urls:
            if item.referer:
                referer_map[item.url] = item.referer
        
        # 创建ReadRequest
        request = ReadRequest(
            resource_ids=url_list,
            referer_map=referer_map if referer_map else None
        )
        
        # 验证结果
        assert request.get_referer_for_url("https://site1.com/file1.pdf") == "https://site1.com"
        assert request.get_referer_for_url("https://site2.com/file2.pdf") == "https://site2.com"
        assert request.get_referer_for_url("https://site3.com/file3.pdf") is None 