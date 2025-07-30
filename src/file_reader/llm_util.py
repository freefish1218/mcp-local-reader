"""
MCP-Scraper LLM 工具模块
提供LLM实例和工具的获取功能
"""

import os
import json
import re

from typing import Dict, Union, List
from langchain_openai import ChatOpenAI
from .utils import get_logger

from dotenv import load_dotenv
load_dotenv(override=True)

logger = get_logger(__name__)

# 从环境变量获取默认配置
LLM_BASE_URL = os.getenv("LLM_VISION_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_VISION_API_KEY", "")
LLM_MODEL = os.getenv("LLM_VISION_MODEL", "")
VERBOSE = os.getenv("LLM_VERBOSE", "").lower() in ("true", "1")

async def get_llm() -> ChatOpenAI:
    """
    获取配置的LLM实例

    Returns:
        ChatOpenAI: 配置好的ChatOpenAI实例
    """
    base_url = LLM_BASE_URL
    api_key = LLM_API_KEY
    model = LLM_MODEL
    
    if not api_key:
        raise ValueError("LLM_API_KEY environment variable is required")

    kwargs = {
        "model": model,
        "api_key": api_key,
        "verbose": VERBOSE,
    }
    
    if base_url:
        kwargs["base_url"] = base_url
    
    return ChatOpenAI(**kwargs)


def parse_json(json_str: str) -> Union[Dict, List]:
    """
    解析JSON字符串，支持包含JSON的markdown代码块
    
    Args:
        json_str: 要解析的字符串
        
    Returns:
        Union[Dict, List]: 解析后的JSON对象或数组
        
    Raises:
        ValueError: 当无法解析有效的JSON时抛出
    """
    # 如果输入是已经解析的对象，直接返回
    if isinstance(json_str, (dict, list)):
        return json_str
        
    # 如果是字符串，尝试解析
    if isinstance(json_str, str):
        try:
            # 尝试直接解析
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 移除markdown代码块和多余空白
            clean_str = re.sub(r'```(?:json)?\s*([\s\S]*?)\s*```', '\\1', json_str).strip()
            
            # 查找JSON对象或数组的边界
            obj_match = re.search(r'\{.*\}|\[.*\]', clean_str, re.DOTALL)
            if obj_match:
                try:
                    return json.loads(obj_match.group(0))
                except json.JSONDecodeError:
                    pass
                    
    # 如果所有尝试都失败
    raise ValueError("无法从字符串中提取有效的JSON")
