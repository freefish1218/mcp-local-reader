"""
文件读取器数据模型
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import os



class FailureType(str, Enum):
    """失败类型枚举"""
    
    # 文件和内容相关错误
    SIZE_EXCEEDED = "size_exceeded"          # 文件大小超限
    INVALID_FILE_FORMAT = "invalid_file_format"    # 无效文件格式
    UNSUPPORTED_TYPE = "unsupported_type"    # 不支持的文件类型
    
    # 解析相关错误
    PARSE_ERROR = "parse_error"              # 文件解析错误
    OCR_ERROR = "ocr_error"                  # OCR识别错误
    
    # 系统相关错误
    ERROR_RESPONSE = "error_response"        # 错误响应
    OTHER = "other"                          # 其他未分类错误
    

class FileContent(BaseModel):
    """成功读取的文件内容"""
    resource_id: str = Field(description="资源ID")
    content: str = Field(description="提取出的文件内容文本")


class FailedFile(BaseModel):
    """处理失败的文件信息"""
    resource_id: Optional[str] = Field(None, description="资源ID（如果处理阶段失败）")
    type: FailureType = Field(description="失败类型标识")
    error_message: Optional[str] = Field(None, description="详细错误信息")



class LocalReadRequest(BaseModel):
    """本地文件读取请求"""
    file_paths: List[str] = Field(description="本地文件路径数组")
    max_size: int = Field(
        default_factory=lambda: int(os.getenv("FILE_READER_MAX_FILE_SIZE_MB", "20")) * 1024 * 1024,
        description="读取文件时的最大大小限制(字节数)"
    )
    allow_absolute_paths: bool = Field(default=False, description="是否允许绝对路径")


class ReadResponse(BaseModel):
    """文件读取响应"""
    contents: List[FileContent] = Field(default_factory=list, description="成功读取内容的文件列表")
    failed: List[FailedFile] = Field(default_factory=list, description="处理失败的文件列表及原因")
    
    def add_content(self, resource_id: str, content: str):
        """添加成功读取的内容"""
        self.contents.append(FileContent(resource_id=resource_id, content=content))
    
    def add_failure(self, resource_id: str, failure_type: FailureType, error_message: str = None):
        """添加失败记录"""
        self.failed.append(FailedFile(
            resource_id=resource_id,
            type=failure_type,
            error_message=error_message
        ))


class ParseResult(BaseModel):
    """文件解析结果"""
    success: bool = Field(description="解析是否成功")
    content: Optional[str] = Field(default=None, description="解析的内容")
    doc_type: Optional[str] = Field(default=None, description="文档类型")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="文档元数据")
    error: Optional[str] = Field(default=None, description="错误信息")


class OCRRequest(BaseModel):
    """OCR请求模型"""
    image_data: bytes = Field(description="图像数据")
    image_format: str = Field(description="图像格式")
    language: str = Field(default="zh", description="识别语言")


class OCRResponse(BaseModel):
    """OCR响应模型"""
    success: bool = Field(description="识别是否成功")
    text: Optional[str] = Field(default=None, description="识别出的文本")
    confidence: Optional[float] = Field(default=None, description="识别置信度")
    error: Optional[str] = Field(default=None, description="错误信息")


