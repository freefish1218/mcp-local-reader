#!/usr/bin/env python3
"""
单文件集成测试脚本 - 专门测试test.docx文件
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


async def main():
    """主函数"""
    # 配置
    http_service_url = "http://localhost:8080"
    mcp_service_url = "http://localhost:3001/mcp"
    test_file = "tests/files/test1.pdf"
    test_file_name = "test1.pdf"
    
    print(f"📡 HTTP服务: {http_service_url}")
    print(f"📡 MCP服务: {mcp_service_url}")
    print(f"📄 测试文件: {test_file}")
    print("=" * 60)
    
    # 检查测试文件
    if not Path(test_file).exists():
        print(f"❌ 测试文件不存在: {test_file}")
        sys.exit(1)
    
    try:
        # 步骤1: 上传文件到HTTP服务
        print(f"\n📤 步骤1: 上传文件到HTTP服务")
        
        with open(test_file, 'rb') as f:
            file_content = f.read()
        
        files = {
            'file': (test_file_name, file_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{http_service_url}/upload", files=files)
            response.raise_for_status()
            upload_result = response.json()
        
        print(f"✅ 上传成功!")
        print(f"   Resource ID: {upload_result.get('resource_id')}")
        print(f"   URL: {upload_result.get('url')}")
        print(f"   文件名: {upload_result.get('filename')}")
        print(f"   大小: {upload_result.get('size')} 字节")
        
        file_url = upload_result.get('url')
        if not file_url:
            print("❌ 未获取到文件URL")
            sys.exit(1)
        
        # 步骤2: 通过MCP服务读取文件
        print(f"\n📖 步骤2: 通过MCP服务读取文件")
        print(f"   文件URL: {file_url}")
        
        transport = StreamableHttpTransport(mcp_service_url)
        async with Client(transport) as mcp_client:
            result = await mcp_client.call_tool("read_local_file", {
                "urls": [{"url": file_url}],
                "max_size": 50
            })
            
            if result and len(result) > 0 and hasattr(result[0], 'text'):
                read_result = json.loads(result[0].text)
                
                contents = read_result.get('contents', [])
                failed = read_result.get('failed', [])
                
                print(f"✅ MCP读取完成!")
                print(f"   成功文件数: {len(contents)}")
                print(f"   失败文件数: {len(failed)}")
                
                if failed:
                    print(f"\n❌ 读取失败:")
                    for failure in failed:
                        print(f"   - {failure.get('resource_id')}: {failure.get('error_message')}")
                    sys.exit(1)
                
                if contents:
                    content_item = contents[0]
                    content_text = content_item.get('content', '')
                    content_type = content_item.get('content_type', '未知')
                    
                    print(f"\n📄 文件内容:")
                    print(f"   内容类型: {content_type}")
                    print(f"   内容长度: {len(content_text)} 字符")
                    print(f"   内容预览:")
                    print(f"   {'-' * 40}")
                    print(f"   {content_text[:500]}...")
                    print(f"   {'-' * 40}")
                    
                    print(f"\n🎉 集成测试成功! 完整流程验证通过")
                    sys.exit(0)
                else:
                    print(f"\n❌ 没有读取到任何内容")
                    sys.exit(1)
            else:
                print(f"❌ MCP服务返回空结果")
                sys.exit(1)
        
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP请求失败: {e.response.status_code}")
        try:
            error_detail = e.response.json()
            print(f"   错误详情: {error_detail}")
        except:
            print(f"   错误内容: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 