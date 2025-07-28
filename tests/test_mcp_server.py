"""
测试MCP服务器功能
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

from file_reader.models import LocalReadRequest, ReadResponse, FileContent, FailedFile, FailureType


class TestMCPServerConfiguration:
    """测试MCP服务器配置"""
    
    def test_server_config_import(self):
        """测试服务器配置导入"""
        # 测试能否正常导入MCP服务器模块
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
            from mcp_server import SERVER_CONFIG
            
            assert "host" in SERVER_CONFIG
            assert "port" in SERVER_CONFIG
            assert "base_path" in SERVER_CONFIG
            
            assert SERVER_CONFIG["host"] == "0.0.0.0"
            assert SERVER_CONFIG["base_path"] == "/mcp"
            
        except ImportError as e:
            pytest.skip(f"无法导入MCP服务器模块: {e}")


class TestMCPServerTools:
    """测试MCP服务器工具函数"""
    
    def test_get_local_file_reader_singleton(self):
        """测试本地文件读取器单例模式"""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
            
            # 使用clean环境变量
            clean_env = {k: v for k, v in os.environ.items() 
                        if not k.startswith('FILE_READER_')}
            
            with patch.dict(os.environ, clean_env, clear=True):
                from mcp_server import get_local_file_reader
                
                # 获取两次实例，应该是同一个对象
                reader1 = get_local_file_reader()
                reader2 = get_local_file_reader()
                
                assert reader1 is reader2
                assert reader1 is not None
            
        except ImportError as e:
            pytest.skip(f"无法导入MCP服务器模块: {e}")
    
    @pytest.mark.asyncio
    async def test_read_local_files_tool_structure(self):
        """测试read_local_files工具的基本结构"""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
            from mcp_server import read_local_files
            
            # 检查函数签名
            import inspect
            sig = inspect.signature(read_local_files)
            params = list(sig.parameters.keys())
            
            assert 'file_paths' in params
            assert 'max_size' in params
            
        except ImportError as e:
            pytest.skip(f"无法导入MCP服务器模块: {e}")


class TestMCPServerIntegration:
    """测试MCP服务器集成"""
    
    @pytest.mark.asyncio
    async def test_read_local_files_mock(self):
        """测试read_local_files工具（使用Mock）"""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
            from mcp_server import read_local_files, get_local_file_reader
            
            # Mock文件读取器
            mock_reader = Mock()
            mock_response = ReadResponse()
            mock_response.add_content("test.txt", "测试内容")
            mock_reader.read_local_files.return_value = mock_response
            
            with patch('mcp_server.get_local_file_reader', return_value=mock_reader):
                result = await read_local_files(
                    file_paths=["test.txt"],
                    max_size=1024*1024
                )
                
                # 验证结果
                assert len(result) == 1
                assert result[0].text == "测试内容"
                
                # 验证调用参数
                mock_reader.read_local_files.assert_called_once()
                call_args = mock_reader.read_local_files.call_args[0][0]
                assert isinstance(call_args, LocalReadRequest)
                assert call_args.file_paths == ["test.txt"]
                assert call_args.max_size == 1024*1024
            
        except ImportError as e:
            pytest.skip(f"无法导入MCP服务器模块: {e}")
    
    @pytest.mark.asyncio
    async def test_read_local_files_failure_handling(self):
        """测试read_local_files错误处理"""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
            from mcp_server import read_local_files, get_local_file_reader
            
            # Mock文件读取器返回失败结果
            mock_reader = Mock()
            mock_response = ReadResponse()
            mock_response.add_failure("test.txt", FailureType.PARSE_ERROR, "解析失败")
            mock_reader.read_local_files.return_value = mock_response
            
            with patch('mcp_server.get_local_file_reader', return_value=mock_reader):
                result = await read_local_files(
                    file_paths=["test.txt"],
                    max_size=1024*1024
                )
                
                # 验证结果 - 应该返回空列表，但不会抛出异常
                assert len(result) == 0
            
        except ImportError as e:
            pytest.skip(f"无法导入MCP服务器模块: {e}")