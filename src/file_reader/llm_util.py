"""
MCP-Scraper LLM 工具模块
提供LLM实例和工具的获取功能
"""

import os
import json
import re

from typing import Dict, Any, Optional, List, Callable, Awaitable, Union
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

from file_reader.config import McpServerInstance, get_config
from file_reader.utils import get_logger

from dotenv import load_dotenv
load_dotenv(override=True)

logger = get_logger(__name__)

# 从环境变量获取默认配置
DEFAULT_LLM_PLATFORM = os.getenv("LLM_VISION_PLATFORM", "")
DEFAULT_LLM_MODEL = os.getenv("LLM_VISION_MODEL", "")
VERBOSE = os.getenv("VERBOSE", "").lower() in ("true", "1")

async def get_llm(agent_name: Optional[str] = None) -> ChatOpenAI:
    """
    获取配置的LLM实例
    
    Args:
        agent_name: 可选的代理名称，用于获取特定代理的配置
        
    Returns:
        ChatOpenAI: 配置好的ChatOpenAI实例
    """
    prefix = f"{agent_name}_" if agent_name else ""
    platform = os.getenv(f"{prefix}AGENT_LLM_PLATFORM", DEFAULT_LLM_PLATFORM)
    model = os.getenv(f"{prefix}AGENT_LLM_MODEL", DEFAULT_LLM_MODEL)
    
    platform_info = await get_config(f"{platform}_MODEL")
    
    return ChatOpenAI(
        verbose=VERBOSE,
        model=platform_info.get(model, model),
        openai_api_base=platform_info.get("BASE_URL"),
        openai_api_key=platform_info.get("API_KEY"),
    )

async def get_tools(
    servers: Dict[str, McpServerInstance],
    patch: Optional[Dict[str, Callable[[Any], Awaitable[Any]]]] = None
) -> List[Any]:
    """
    获取工具列表
    
    Args:
        servers: MCP服务器实例字典
        patch: 可选的工具补丁函数字典
        
    Returns:
        List[Any]: 工具列表
    """
    tools = []
    
    # 为每个服务器创建客户端并获取工具
    for key, server in servers.items():
        try:
            # 创建传输层
            transport = StreamableHttpTransport(url=server["endpoints"])
            
            # 使用 fastmcp Client 获取工具列表
            async with Client(transport) as client:
                mcp_tools = await client.list_tools()
                
                for mcp_tool in mcp_tools:
                    tool_name = f"{key}_{mcp_tool.name}"
                    tool_description = mcp_tool.description
                    tool_schema = mcp_tool.inputSchema
                    tool_actual_name = mcp_tool.name
                    
                    # 为每个工具创建一个闭包函数，捕获必要的变量
                    async def create_tool_func(server_info=server, actual_name=tool_actual_name, t_name=tool_name):
                        async def tool_func(**args):
                            logger.info(f"----------- call tools: {t_name}, args: {json.dumps(args, ensure_ascii=False)}")
                            
                            # 每次调用工具时创建新的客户端
                            transport = StreamableHttpTransport(url=server_info["endpoints"])
                            async with Client(transport) as client:
                                # 使用 fastmcp 调用工具
                                result = await client.call_tool(
                                    name=actual_name,
                                    arguments=args
                                )
                                
                                # 应用补丁函数（如果存在）
                                if patch and t_name in patch:
                                    return await patch[t_name](result)
                                
                                return result
                        return tool_func
                    
                    # 创建工具函数并添加到工具列表
                    tool_function = await create_tool_func()
                    tools.append(tool(
                        tool_function,
                        name=tool_name,
                        description=tool_description,
                        args_schema=tool_schema
                    ))
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Error getting tools for {key}: {str(e)}\nException type: {type(e).__name__}\nTraceback: {error_traceback}")
            continue
    
    return tools

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
