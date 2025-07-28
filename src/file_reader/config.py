"""
MCP-File-Reader 配置模块
提供文件类型定义和基本配置
"""

import os
from typing import Dict, List

from dotenv import load_dotenv
load_dotenv(override=True)

# ============================
# 文件类型定义
# ============================

# 支持解析的文档类型（包含文档、图像等所有支持的格式）
SUPPORTED_DOC_TYPES = [
    # PDF文档
    '.pdf',
    
    # Microsoft Office文档
    '.doc', '.docx',        # Word文档
    '.xls', '.xlsx',        # Excel电子表格
    '.ppt', '.pptx',        # PowerPoint演示文稿
    '.rtf',                 # 富文本格式

    # 电子表格
    '.csv',                 # CSV文件
    '.epub',                # EPUB电子书
    
    # OpenDocument格式
    '.odt',                 # OpenDocument文本
    '.ods',                 # OpenDocument电子表格
    '.odp',                 # OpenDocument演示文稿
    
    # 文本文档
    '.txt',                 # 纯文本
    '.md', '.markdown',     # Markdown文档
    '.json',                # JSON文档
    
    # 图像文件（支持OCR文字识别）
    '.jpg', '.jpeg',        # JPEG图像
    '.png',                 # PNG图像
    '.gif',                 # GIF图像
    '.bmp',                 # 位图
    '.webp',                # WebP图像
    '.tiff',                # TIFF图像
    
    # 压缩文件（解包处理）
    '.zip',                 # ZIP压缩包
    '.rar',                 # RAR压缩包  
    '.7z',                  # 7-Zip压缩包
    '.tar',                 # TAR归档文件
    '.gz',                  # GZIP压缩文件
    '.tar.gz', '.tgz',      # TAR.GZ压缩包
    '.tar.bz2', '.tbz2',    # TAR.BZ2压缩包
]

# 忽略的文件类型（不进行解析的文件格式）
IGNORED_TYPES = [
    # 磁盘镜像
    '.iso', '.img', '.dmg',
    
    # 二进制文件
    '.bin', '.exe', '.msi',
    
    # 包文件
    '.pkg', '.deb', '.rpm', '.app', '.ipa', '.apk',
]

# ============================
# Resource ID 处理配置
# ============================

# 特殊的resource_id前缀配置
SPECIAL_RESOURCE_PREFIXES = {
    'pdf_img_': {
        'type': 'pdf_image', 
        'default_extension': '.png',
        'description': 'PDF文档中提取的图片资源（resource_id已包含扩展名）'
    },
    'archive_file_': {
        'type': 'archive_file', 
        'description': '压缩包中提取的文件资源'
    }
}

# Resource ID vs URL 的检测规则
RESOURCE_ID_DETECTION_RULES = {
    'url_schemes': ['http://', 'https://', 'ftp://'],
    'resource_id_patterns': [
        r'^[a-zA-Z0-9_-]+\.[a-zA-Z0-9]+$',  # 文件名格式
        r'^[a-zA-Z_]+_[a-fA-F0-9]+.*$',      # 带前缀的ID格式
    ],
    'min_length': 3,
    'max_length': 512
}


# 基本配置
DEFAULT_OPENAI_MODEL = "gpt-4o"
