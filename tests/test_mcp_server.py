"""
测试MCP服务器功能
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock

from file_reader.models import ReadRequest, ReadResponse, FileContent, FailedFile, FailureType


class TestMCPServerConfiguration:
    """测试MCP服务器配置"""
    
    def test_server_config_import(self):
        """测试服务器配置导入"""
        # 测试能否正常导入MCP服务器模块
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
            from mcp_server import SERVER_CONFIG
            
            assert "name" in SERVER_CONFIG
            assert "instructions" in SERVER_CONFIG
            assert "host" in SERVER_CONFIG
            assert "port" in SERVER_CONFIG
            assert "base_path" in SERVER_CONFIG
            
            assert SERVER_CONFIG["name"] == "MCPFileReaderServer"
            assert SERVER_CONFIG["host"] == "0.0.0.0"
            assert SERVER_CONFIG["base_path"] == "/mcp"
            
        except ImportError as e:
            pytest.skip(f"无法导入MCP服务器模块: {e}")


class TestMCPServerTools:
    """测试MCP服务器工具函数"""
    
    def test_get_file_reader_singleton(self):
        """测试文件读取器单例模式"""
        try:
            import sys
            import os
            from unittest.mock import patch
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
            
            # 使用clean环境变量
            clean_env = {k: v for k, v in os.environ.items() 
                        if not k.startswith('FILE_READER_')}
            
            with patch.dict(os.environ, clean_env, clear=True):
                # 清理全局状态
                import mcp_server
                mcp_server.file_reader = None
                
                from mcp_server import get_file_reader
                
                # 获取两次实例，应该是同一个对象
                reader1 = get_file_reader()
                reader2 = get_file_reader()
                
                assert reader1 is reader2
                assert reader1 is not None
            
        except ImportError as e:
            pytest.skip(f"无法导入MCP服务器模块: {e}")
    
    @pytest.mark.asyncio
    async def test_get_content_tool_structure(self):
        """测试get_content工具的基本结构"""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
            from mcp_server import get_content
            
            # 检查函数签名
            import inspect
            sig = inspect.signature(get_content)
            params = list(sig.parameters.keys())
            
            assert 'resource_ids' in params
            assert 'referer' in params
            assert 'max_size' in params
            
        except ImportError as e:
            pytest.skip(f"无法导入MCP服务器模块: {e}")
    
    @pytest.mark.asyncio 
    async def test_get_content_tool_mock(self):
        """测试get_content工具（使用Mock）"""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
            from mcp_server import get_content, get_file_reader
            
            # 创建Mock响应
            mock_response = ReadResponse()
            mock_response.add_content("test.txt", "这是测试内容")
            
            # Mock文件读取器
            with patch('mcp_server.get_file_reader') as mock_get_reader:
                mock_reader = Mock()
                mock_reader.read_files = AsyncMock(return_value=mock_response)
                mock_get_reader.return_value = mock_reader
                
                # 调用工具函数
                result = await get_content(["test.txt"])
                
                assert len(result) == 1  # 应该返回一个TextContent对象
                
                # 解析返回的JSON
                response_text = result[0].text
                response_data = json.loads(response_text)
                
                assert "contents" in response_data
                assert "failed" in response_data
                assert len(response_data["contents"]) == 1
                assert response_data["contents"][0]["resource_id"] == "test.txt"
                assert response_data["contents"][0]["content"] == "这是测试内容"
                
        except ImportError as e:
            pytest.skip(f"无法导入MCP服务器模块: {e}")
    
    @pytest.mark.asyncio
    async def test_get_content_tool_error_handling(self):
        """测试get_content工具错误处理"""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
            from mcp_server import get_content
            
            # Mock文件读取器抛出异常
            with patch('mcp_server.get_file_reader') as mock_get_reader:
                mock_reader = Mock()
                mock_reader.read_files = AsyncMock(side_effect=Exception("测试异常"))
                mock_get_reader.return_value = mock_reader
                
                # 调用工具函数
                result = await get_content(["test.txt"])
                
                assert len(result) == 1
                
                # 解析返回的JSON，应该包含错误信息
                response_text = result[0].text
                response_data = json.loads(response_text)
                
                assert "failed" in response_data
                assert len(response_data["failed"]) == 1
                assert response_data["failed"][0]["resource_id"] == "test.txt"
                assert "测试异常" in response_data["failed"][0]["error_message"]
                
        except ImportError as e:
            pytest.skip(f"无法导入MCP服务器模块: {e}")
    
    @pytest.mark.asyncio
    async def test_get_stats_tool(self):
        """测试get_stats工具"""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
            from mcp_server import get_stats
            
            # Mock文件读取器
            with patch('mcp_server.get_file_reader') as mock_get_reader:
                mock_reader = Mock()
                mock_stats = {
                    "file_reader": {
                        "total_requests": 10,
                        "successful_reads": 8,
                        "failed_reads": 2,
                        "success_rate": 0.8
                    },
                    "storage": {
                        "downloads": 10,
                        "cache_hits": 5,
                        "cache_hit_rate": 0.5
                    }
                }
                mock_reader.get_stats.return_value = mock_stats
                mock_get_reader.return_value = mock_reader
                
                # 调用工具函数
                result = await get_stats()
                
                assert len(result) == 1
                
                # 解析返回的JSON
                stats_text = result[0].text
                stats_data = json.loads(stats_text)
                
                assert "file_reader" in stats_data
                assert "storage" in stats_data
                assert stats_data["file_reader"]["total_requests"] == 10
                assert stats_data["storage"]["cache_hits"] == 5
                
        except ImportError as e:
            pytest.skip(f"无法导入MCP服务器模块: {e}")


class TestMCPServerIntegration:
    """测试MCP服务器集成功能"""
    
    def test_environment_variables_handling(self):
        """测试环境变量处理"""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
            
            # 测试环境变量的默认值处理
            with patch.dict(os.environ, {}, clear=True):
                from mcp_server import get_file_reader
                reader = get_file_reader()
                
                # 应该使用默认值成功创建
                assert reader is not None
                assert reader.max_workers == 3  # 默认值
            
        except ImportError as e:
            pytest.skip(f"无法导入MCP服务器模块: {e}")
    
    def test_server_basic_functionality(self):
        """测试服务器基本功能"""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
            from mcp_server import mcp
            
            # 检查FastMCP实例是否正确创建
            assert mcp is not None
            assert hasattr(mcp, 'name')
            
        except (ImportError, AttributeError) as e:
            pytest.skip(f"无法测试服务器基本功能: {e}") 