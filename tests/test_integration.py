#!/usr/bin/env python3
"""
HTTP下载服务与MCP文件读取器服务集成测试脚本
测试流程：上传文件到HTTP服务 -> 获取file:///resource_id -> 通过MCP服务读取内容
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


class IntegrationTester:
    """集成测试器"""
    
    def __init__(
        self, 
        http_service_url: str = "http://localhost:8080",
        mcp_service_url: str = "http://localhost:3001/mcp"
    ):
        """
        初始化测试器
        
        Args:
            http_service_url: HTTP下载服务URL
            mcp_service_url: MCP服务URL
        """
        self.http_service_url = http_service_url.rstrip('/')
        self.mcp_service_url = mcp_service_url.rstrip('/')
        
        # MCP客户端
        self.transport = StreamableHttpTransport(self.mcp_service_url)
        self.mcp_client = Client(self.transport)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.mcp_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.mcp_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def upload_file_to_http_service(self, file_path: str, custom_filename: str = None) -> Dict[str, Any]:
        """
        上传文件到HTTP下载服务
        
        Args:
            file_path: 本地文件路径
            custom_filename: 可选的自定义文件名
        
        Returns:
            上传响应字典
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        print(f"📤 开始上传文件到HTTP服务: {file_path}")
        
        # 准备上传数据
        with open(file_path_obj, 'rb') as f:
            file_content = f.read()
        
        files = {
            'file': (file_path_obj.name, file_content, 'application/octet-stream')
        }
        
        data = {}
        if custom_filename:
            data['filename'] = custom_filename
        
        # 发送上传请求
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.http_service_url}/upload",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                upload_result = response.json()
                
                print(f"✅ 文件上传成功!")
                print(f"   Resource ID: {upload_result.get('resource_id')}")
                print(f"   URL: {upload_result.get('url')}")
                print(f"   文件名: {upload_result.get('filename')}")
                print(f"   大小: {upload_result.get('size')} 字节")
                print(f"   内容类型: {upload_result.get('content_type')}")
                
                return upload_result
                
            except httpx.HTTPStatusError as e:
                error_text = e.response.text if hasattr(e.response, 'text') else str(e)
                print(f"❌ HTTP上传失败: {e.response.status_code} - {error_text}")
                raise
            except Exception as e:
                print(f"❌ 上传异常: {e}")
                raise
    
    async def read_file_via_mcp(self, file_url: str) -> Dict[str, Any]:
        """
        通过MCP服务读取文件内容
        
        Args:
            file_url: 文件URL (格式: file:///resource_id)
        
        Returns:
            读取结果字典
        """
        print(f"📖 开始通过MCP服务读取文件: {file_url}")
        
        # 构造读取请求
        urls = [{"url": file_url}]
        
        try:
            result = await self.mcp_client.call_tool("read_files", {
                "urls": urls,
                "max_size": 50  # 50MB限制
            })
            
            # 解析返回结果
            if result and len(result) > 0 and hasattr(result[0], 'text'):
                read_result = json.loads(result[0].text)
                
                print(f"✅ MCP文件读取成功!")
                print(f"   成功文件数: {len(read_result.get('contents', []))}")
                print(f"   失败文件数: {len(read_result.get('failed', []))}")
                
                return read_result
            else:
                print(f"❌ MCP服务返回空结果")
                return {"contents": [], "failed": []}
                
        except Exception as e:
            print(f"❌ MCP读取异常: {e}")
            raise
    
    async def run_integration_test(self, test_file_path: str) -> bool:
        """
        运行完整的集成测试
        
        Args:
            test_file_path: 测试文件路径
            
        Returns:
            测试是否成功
        """
        try:
            print(f"🔄 开始集成测试: {test_file_path}")
            print("=" * 60)
            
            # 步骤1: 上传文件到HTTP服务
            upload_result = await self.upload_file_to_http_service(test_file_path)
            
            if not upload_result.get('success'):
                print(f"❌ 上传失败: {upload_result.get('message', '未知错误')}")
                return False
            
            file_url = upload_result.get('url')
            if not file_url:
                print("❌ 上传成功但未获取到文件URL")
                return False
            
            print("\n" + "-" * 40)
            
            # 步骤2: 通过MCP服务读取文件
            read_result = await self.read_file_via_mcp(file_url)
            
            # 验证读取结果
            contents = read_result.get('contents', [])
            failed = read_result.get('failed', [])
            
            if failed:
                print(f"❌ 文件读取失败:")
                for failure in failed:
                    print(f"   - {failure.get('resource_id')}: {failure.get('error_message')}")
                return False
            
            if not contents:
                print("❌ 没有成功读取到任何内容")
                return False
            
            # 显示读取到的内容摘要
            for content_item in contents:
                resource_id = content_item.get('resource_id', '未知')
                content_text = content_item.get('content', '')
                content_type = content_item.get('content_type', '未知')
                
                print(f"📄 成功读取文件:")
                print(f"   Resource ID: {resource_id}")
                print(f"   内容类型: {content_type}")
                print(f"   内容长度: {len(content_text)} 字符")
                print(f"   内容预览: {content_text[:200]}...")
            
            print("\n" + "=" * 60)
            print("🎉 集成测试成功!")
            return True
            
        except Exception as e:
            print(f"\n❌ 集成测试失败: {e}")
            return False
    
    async def test_multiple_files(self, file_paths: list) -> Dict[str, bool]:
        """
        测试多个文件
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            每个文件的测试结果
        """
        results = {}
        
        for file_path in file_paths:
            print(f"\n{'='*80}")
            file_name = Path(file_path).name
            print(f"🧪 测试文件: {file_name}")
            
            try:
                success = await self.run_integration_test(file_path)
                results[file_name] = success
            except Exception as e:
                print(f"❌ 测试文件 {file_name} 时发生异常: {e}")
                results[file_name] = False
        
        return results


async def main():
    """主函数"""
    # 检查环境变量
    http_url = os.getenv("DOWNLOAD_SERVICE_URL", "http://localhost:8080")
    mcp_url = os.getenv("MCP_SERVICE_URL", "http://localhost:3001/mcp")
    
    print("🚀 HTTP下载服务与MCP文件读取器集成测试")
    print(f"📡 HTTP服务URL: {http_url}")
    print(f"📡 MCP服务URL: {mcp_url}")
    print()
    
    # 测试文件路径
    test_files = [
        "tests/files/test1.doc",
        "tests/files/test.docx", 
        "tests/files/test1.pdf",
        "tests/files/test.xlsx"
    ]
    
    # 检查测试文件是否存在
    available_files = []
    for file_path in test_files:
        if Path(file_path).exists():
            available_files.append(file_path)
        else:
            print(f"⚠️  测试文件不存在，跳过: {file_path}")
    
    if not available_files:
        print("❌ 没有可用的测试文件")
        return
    
    print(f"📁 找到 {len(available_files)} 个测试文件")
    
    # 运行测试
    async with IntegrationTester(http_url, mcp_url) as tester:
        if len(available_files) == 1:
            # 单文件测试
            success = await tester.run_integration_test(available_files[0])
            exit_code = 0 if success else 1
        else:
            # 多文件测试
            results = await tester.test_multiple_files(available_files)
            
            # 显示总结
            print(f"\n{'='*80}")
            print("📊 测试总结:")
            successful = 0
            for file_name, success in results.items():
                status = "✅ 成功" if success else "❌ 失败"
                print(f"   {file_name}: {status}")
                if success:
                    successful += 1
            
            print(f"\n🎯 总体结果: {successful}/{len(results)} 个文件测试成功")
            exit_code = 0 if successful == len(results) else 1
    
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main()) 