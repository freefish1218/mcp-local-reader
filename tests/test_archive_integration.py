#!/usr/bin/env python3
"""
压缩文件处理集成测试
测试压缩文件解析器与存储服务的完整集成
"""

import asyncio
import os
import sys
import tempfile
import zipfile
import json
from pathlib import Path
import pytest

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from file_reader.core import FileReader
from file_reader.storage import HTTPDownloadStorageClient
from file_reader.models import ReadRequest


@pytest.mark.asyncio
async def test_http_zip_url():
    """测试HTTP网络URL的ZIP文件处理"""
    print("\n" + "=" * 80)
    print("🌐 测试HTTP网络URL的ZIP文件处理")
    
    try:
        # 使用一个包含多种文件类型的真实ZIP文件URL
        # 这里使用GitHub上的示例项目ZIP文件
        test_urls = [
            # GitHub项目的ZIP下载链接（包含多种文件类型）
            "https://github.com/microsoft/vscode-extension-samples/archive/refs/heads/main.zip",
            # 另一个示例项目
            "https://codeload.github.com/microsoft/TypeScript/zip/refs/heads/main"
        ]
        
        # 创建真实的HTTP存储客户端
        storage_client = HTTPDownloadStorageClient()
        
        # 创建文件读取器，传入真实存储客户端
        file_reader = FileReader(storage_client=storage_client)
        
        for i, url in enumerate(test_urls[:1]):  # 只测试第一个URL以节省时间
            print(f"\n📄 测试HTTP URL {i+1}: {url}")
            print(f"📡 HTTP存储服务: {storage_client.download_service_url}")
            print(f"🔗 服务启用状态: {storage_client.enabled}")
            
            # 创建读取请求，直接使用HTTP URL
            request = ReadRequest(
                resource_ids=[url],
                max_size=50 * 1024 * 1024  # 50MB，考虑到网络下载的文件可能较大
            )
            
            # 执行读取
            print(f"\n🔍 开始下载和解析网络ZIP文件...")
            print(f"   - 下载URL: {url}")
            
            response = await file_reader.read_files(request)
            
            # 验证结果
            print(f"✅ 解析完成")
            print(f"   - 成功内容数: {len(response.contents)}")
            print(f"   - 失败文件数: {len(response.failed)}")
            
            # 检查是否有成功的内容
            if response.contents:
                file_content = response.contents[0]  # 获取第一个成功的内容
                print(f"\n📝 解析结果:")
                print(f"   - 资源ID: {file_content.resource_id}")
                print(f"   - 内容长度: {len(file_content.content):,} 字符")
                
                # 检查Markdown内容格式
                content = file_content.content
                print(f"\n📋 Markdown格式检查:")
                
                # 检查基本结构
                checks = [
                    ("压缩包内容" in content, "包含压缩包标题"),
                    ("文件结构" in content, "包含文件结构"),
                    ("文件列表" in content, "包含文件列表"),
                    ("##" in content, "包含Markdown标题"),
                    ("```" in content, "包含代码块"),
                    ("file:///" in content, "包含文件链接")
                ]
                
                for check_result, description in checks:
                    status = "✅" if check_result else "❌"
                    print(f"   - {status} {description}")
                
                # 显示内容预览
                print(f"\n📖 内容预览 (前500字符):")
                print("-" * 60)
                print(content[:500])
                if len(content) > 500:
                    print("...")
                print("-" * 60)
                
                # 检查元数据
                metadata = file_content.metadata if hasattr(file_content, 'metadata') else {}
                print(f"\n📊 元数据信息:")
                print(f"   - 解析器: {metadata.get('parser', 'N/A')}")
                print(f"   - 文件数量: {metadata.get('file_count', 'N/A')}")
                print(f"   - 压缩包大小: {metadata.get('archive_size', 'N/A')} 字节")
                print(f"   - 解压后大小: {metadata.get('total_extracted_size', 'N/A')} 字节")
                print(f"   - 压缩率: {metadata.get('compression_ratio', 'N/A')}%")
                print(f"   - 文件类型分布: {metadata.get('file_type_distribution', {})}")
                
                # 检查文件链接
                if storage_client.enabled:
                    import re
                    links = re.findall(r'file:///([^\)]+)', content)
                    if links:
                        print(f"\n🔗 资源链接分析:")
                        print(f"   - 链接数量: {len(links)}")
                        print(f"   - 示例链接: {links[0][:50]}...")
                        
                        # 验证链接格式
                        valid_links = sum(1 for link in links 
                                        if re.match(r'^\d{8}_[a-f0-9]{8}_[a-f0-9]{32}\.\w+$', link))
                        print(f"   - 有效链接格式: {valid_links}/{len(links)}")
                        
                        if valid_links > 0:
                            print(f"   - ✅ HTTP下载和resource_id处理正确")
                        else:
                            print(f"   - ⚠️  链接格式不符合预期")
                else:
                    print(f"   - ⚠️  HTTP存储服务未启用")
                
                print(f"\n✅ HTTP ZIP文件处理成功")
                return True
                
            # 检查失败的文件
            elif response.failed:
                print(f"\n❌ HTTP ZIP文件处理失败:")
                for failed in response.failed:
                    print(f"   - {failed.resource_id}: {failed.type}")
                    print(f"     错误: {failed.error_message}")
                return False
            else:
                print(f"❌ 没有返回任何内容或错误信息")
                return False
                
    except Exception as e:
        print(f"❌ HTTP ZIP测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 80)
    print("🧪 测试错误处理")

    # 使用真实的HTTP存储客户端
    storage_client = HTTPDownloadStorageClient()
    file_reader = FileReader(storage_client=storage_client)

    # 测试损坏的ZIP文件
    print("\n1. 测试损坏的ZIP文件")

    # 创建一个损坏的ZIP文件
    temp_corrupt = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
    temp_corrupt.write(b"PK\x03\x04invalid zip content")
    temp_corrupt.close()

    request = ReadRequest(
        resource_ids=[f"file://{temp_corrupt.name}"],
        max_size=1024 * 1024
    )

    response = await file_reader.read_files(request)

    if response.failed:
        print(f"   ✅ 正确处理损坏文件: {response.failed[0].error_message}")
    elif response.contents:
        print(f"   ❌ 应该拒绝损坏文件，但解析成功了")
    else:
        print(f"   ❌ 没有返回任何内容或错误信息")

    # 清理临时文件
    try:
        os.unlink(temp_corrupt.name)
    except:
        pass

    # 测试空ZIP文件
    print("\n2. 测试空ZIP文件")
    temp_empty = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
    temp_empty.close()  # 创建空文件

    empty_request = ReadRequest(
        resource_ids=[f"file://{temp_empty.name}"],
        max_size=1024 * 1024
    )

    response = await file_reader.read_files(empty_request)

    if response.failed:
        print(f"   ✅ 正确处理空文件: {response.failed[0].error_message}")
    elif response.contents:
        print(f"   ❌ 应该拒绝空文件，但解析成功了")
    else:
        print(f"   ❌ 没有返回任何内容或错误信息")

    # 清理临时文件
    try:
        os.unlink(temp_empty.name)
    except:
        pass


async def main():
    """主函数"""
    print("🎯 开始压缩文件处理集成测试\n")
    
    # 运行HTTP ZIP URL测试
    print("=" * 80)
    print("🌐 HTTP网络ZIP文件测试")
    http_success = await test_http_zip_url()
        
    # 运行错误处理测试
    await test_error_handling()
    
    print("\n" + "=" * 80)
    if http_success:
        print("🎉 HTTP ZIP测试通过，但本地集成测试失败!")
    else:
        print("❌ 测试失败!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
