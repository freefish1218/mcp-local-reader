"""
测试数据模型
"""

import pytest
from file_reader.models import (
    LocalReadRequest, ReadResponse, FileContent, FailedFile, 
    FailureType, ParseResult
)


class TestLocalReadRequest:
    """测试本地读取请求模型"""
    
    def test_local_read_request_creation(self):
        """测试本地读取请求创建"""
        request = LocalReadRequest(
            file_paths=["file1.pdf", "file2.txt"],
            max_size=1024*1024
        )
        
        assert request.file_paths == ["file1.pdf", "file2.txt"]
        assert request.max_size == 1024*1024
    
    def test_local_read_request_default_values(self):
        """测试本地读取请求默认值"""
        request = LocalReadRequest(file_paths=["file1.pdf"])
        
        assert request.file_paths == ["file1.pdf"]
        # 默认值来自环境变量，这里不具体测试数值
    
    def test_local_read_request_validation(self):
        """测试本地读取请求验证"""
        # 空的file_paths应该可以创建
        request = LocalReadRequest(file_paths=[])
        assert request.file_paths == []
    
    def test_local_read_request_absolute_paths(self):
        """测试绝对路径支持"""
        request = LocalReadRequest(
            file_paths=["/absolute/path/file.pdf"]
        )
        
        assert request.file_paths == ["/absolute/path/file.pdf"]


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
        response.add_failure("file2.txt", FailureType.PARSE_ERROR, "解析失败")
        
        assert len(response.contents) == 1
        assert len(response.failed) == 1


class TestFailureType:
    """测试失败类型枚举"""
    
    def test_failure_types(self):
        """测试失败类型值"""
        assert FailureType.SIZE_EXCEEDED == "size_exceeded"
        assert FailureType.INVALID_FILE_FORMAT == "invalid_file_format"
        assert FailureType.UNSUPPORTED_TYPE == "unsupported_type"
        assert FailureType.PARSE_ERROR == "parse_error"
        assert FailureType.OCR_ERROR == "ocr_error"
        assert FailureType.ERROR_RESPONSE == "error_response"
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