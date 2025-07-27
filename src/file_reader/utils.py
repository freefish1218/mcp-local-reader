"""
文件读取器工具函数
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from urllib.parse import urlparse


def get_logger(name: str, level: str = None) -> logging.Logger:
    """
    获取日志记录器，自动配置控制台和文件输出
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 设置日志级别
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 创建日志目录
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # 创建日志文件名（按日期和模块名）
    current_date = datetime.now().strftime('%Y-%m-%d')
    module_name = name.split('.')[-1]  # 获取最后一个点后的名称
    log_filename = logs_dir / f"{current_date}_{module_name}.log"
    
    # 创建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logger.level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 创建文件处理器
    try:
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logger.level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # 如果文件处理器创建失败，至少保证控制台输出可用
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logger.level)
        console_handler.setFormatter(formatter)
        print(f"警告: 无法创建日志文件 {log_filename}: {e}")
    
    return logger


def normalize_content(content: str) -> str:
    """
    规范化文本内容
    
    Args:
        content: 原始文本内容
        
    Returns:
        规范化后的文本内容
    """
    if not content:
        return ""
    
    # 替换常见的Unicode空白字符
    content = content.replace('\u00a0', ' ')  # 非断开空格
    content = content.replace('\u2000', ' ')  # en quad
    content = content.replace('\u2001', ' ')  # em quad
    content = content.replace('\u2002', ' ')  # en space
    content = content.replace('\u2003', ' ')  # em space
    content = content.replace('\u2004', ' ')  # three-per-em space
    content = content.replace('\u2005', ' ')  # four-per-em space
    content = content.replace('\u2006', ' ')  # six-per-em space
    content = content.replace('\u2007', ' ')  # figure space
    content = content.replace('\u2008', ' ')  # punctuation space
    content = content.replace('\u2009', ' ')  # thin space
    content = content.replace('\u200a', ' ')  # hair space
    content = content.replace('\u3000', ' ')  # ideographic space
    
    # 规范化换行符
    content = content.replace('\r\n', '\n')
    content = content.replace('\r', '\n')
    
    # 删除多余的空白行（连续超过2个换行符的情况）
    import re
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # 删除行尾空白
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]
    content = '\n'.join(lines)
    
    # 删除首尾空白
    content = content.strip()
    
    return content


def extract_base_domain(url: str) -> Optional[str]:
    """
    从URL中提取基础域名
    
    Args:
        url: 完整URL
        
    Returns:
        基础域名，如果无法提取则返回None
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if not domain:
            return None
        
        # 移除端口号
        if ':' in domain:
            domain = domain.split(':')[0]
        
        return domain
        
    except Exception:
        return None


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小为人类可读的字符串
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        格式化后的文件大小字符串
    """
    if size_bytes is None:
        return "未知"
    
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"


def extract_error_details(error_message: str) -> tuple[str, str]:
    """
    从错误信息中提取错误类型和详细信息
    支持中英文错误信息的解析
    
    Args:
        error_message: 完整的错误信息
        
    Returns:
        (错误类型, 详细信息) 的元组
    """
    # 常见错误模式匹配（中英文）
    error_patterns = [
        # 403 错误
        (r'403|forbidden|禁止访问|访问被拒绝', 'FORBIDDEN'),
        # 404 错误  
        (r'404|not found|文件不存在|资源未找到', 'NOT_FOUND'),
        # 500 错误
        (r'5\d\d|server error|服务器错误|内部错误', 'SERVER_ERROR'),
        # 网络错误
        (r'connection|network|网络|连接', 'NETWORK_ERROR'),
        # 超时错误
        (r'timeout|超时', 'TIMEOUT'),
        # SSL错误
        (r'ssl|tls|证书', 'SSL_ERROR'),
        # 文件过大
        (r'too large|文件过大|大小超限|size exceeded', 'SIZE_EXCEEDED'),
        # 不支持的类型
        (r'unsupported|不支持|invalid format', 'UNSUPPORTED_TYPE'),
        # 解析错误
        (r'parse|解析|格式错误', 'PARSE_ERROR')
    ]
    
    import re
    error_message_lower = error_message.lower()
    
    for pattern, error_type in error_patterns:
        if re.search(pattern, error_message_lower):
            return error_type, error_message
    
    # 默认返回OTHER类型
    return 'OTHER', error_message
