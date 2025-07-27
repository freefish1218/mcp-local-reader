#!/usr/bin/env python3
"""
测试完整的缓存和下载流程，包括资源ID映射
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from file_reader.storage.http_client import HTTPDownloadStorageClient
from file_reader.models import ReadRequest
from file_reader.core import FileReader


async def test_complete_cache_flow():
    """测试完整的缓存和文件处理流程"""
    print("测试完整的缓存和文件处理流程")
    
    # 创建客户端实例
    client = HTTPDownloadStorageClient()
    
    # 模拟场景：第一次下载 -> 缓存 -> 第二次访问命中缓存
    original_url = "https://download.ccgp.gov.cn/oss/download?uuid=74fc0400-4042-4fbd-bf17-f9ae09"
    resource_id_with_ext = "74fc0400-4042-4fbd-bf17-f9ae09.pdf"
    
    # 模拟PDF文件内容（包含PDF魔数）
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n" + b"fake pdf content for testing"
    
    print(f"\n场景1: 模拟首次下载并缓存")
    print(f"  原始URL: {original_url}")
    print(f"  带扩展名的resource_id: {resource_id_with_ext}")
    
    # 手动模拟首次下载的结果（模拟下载服务返回的数据）
    cache_key = client._get_cache_key(original_url)
    cache_data = {
        "content": pdf_content,
        "resource_id": resource_id_with_ext,
        "metadata": {
            "filename": "document.pdf",
            "content_type": "application/pdf",
            "file_type": ".pdf",
            "size": len(pdf_content),
            "cached": False,
            "download_time": 0.5
        }
    }
    
    client.cache.set(cache_key, cache_data)
    print(f"✓ 模拟数据已保存到缓存")
    
    print(f"\n场景2: 第二次访问，测试缓存命中")
    
    # 创建下载请求
    request = ReadRequest(resource_ids=[original_url])
    
    # 调用下载方法
    download_result = await client.download_files_batch(request)
    
    print(f"✓ 下载结果:")
    print(f"  成功文件数: {len(download_result.files)}")
    print(f"  resource_id映射: {download_result.resource_ids}")
    
    # 验证结果
    if original_url in download_result.files:
        content = download_result.files[original_url]
        mapped_resource_id = download_result.resource_ids[original_url]
        
        print(f"✓ 缓存命中成功")
        print(f"  原始URL: {original_url}")
        print(f"  映射的resource_id: {mapped_resource_id}")
        print(f"  文件内容大小: {len(content)} 字节")
        
        # 验证resource_id
        if mapped_resource_id == resource_id_with_ext:
            print(f"✓ 正确：resource_id映射正确")
        else:
            print(f"✗ 错误：resource_id映射错误，期望 {resource_id_with_ext}，实际 {mapped_resource_id}")
            return False
            
        # 验证内容
        if content == pdf_content:
            print(f"✓ 正确：文件内容一致")
        else:
            print(f"✗ 错误：文件内容不一致")
            return False
        
        return True
    else:
        print(f"✗ 错误：缓存未命中")
        return False


async def test_file_reader_integration():
    """测试与FileReader的集成"""
    print(f"\n场景3: 测试与FileReader的集成")
    
    # 创建FileReader实例
    file_reader = FileReader()
    
    # 确保缓存中有数据（使用前面的测试数据）
    client = file_reader.storage_client
    original_url = "https://download.ccgp.gov.cn/oss/download?uuid=74fc0400-4042-4fbd-bf17-f9ae09"
    resource_id_with_ext = "74fc0400-4042-4fbd-bf17-f9ae09.pdf"
    
    # 模拟PDF文件内容
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\nThis is a test PDF content with enough text to pass the minimum length requirement."
    
    cache_key = client._get_cache_key(original_url)
    cache_data = {
        "content": pdf_content,
        "resource_id": resource_id_with_ext,
        "metadata": {
            "filename": "document.pdf",
            "content_type": "application/pdf",
            "file_type": ".pdf",
            "size": len(pdf_content),
            "cached": False,
            "download_time": 0.5
        }
    }
    
    client.cache.set(cache_key, cache_data)
    
    # 创建读取请求
    request = ReadRequest(resource_ids=[original_url])
    
    # 调用FileReader进行文件读取
    response = await file_reader.read_files(request)
    
    print(f"✓ FileReader处理结果:")
    print(f"  成功文件数: {len(response.contents)}")
    print(f"  失败文件数: {len(response.failed)}")
    
    if response.failed:
        for failure in response.failed:
            print(f"  失败: {failure.resource_id} - {failure.failure_type}: {failure.error_message}")
    
    # 检查是否有成功的结果
    if original_url in response.contents:
        content = response.contents[original_url]
        print(f"✓ 文件处理成功")
        print(f"  提取的内容长度: {len(content)} 字符")
        print(f"  内容预览: {content[:100]}...")
        return True
    elif response.failed:
        # 检查失败原因
        for failure in response.failed:
            if failure.resource_id == original_url:
                print(f"文件处理失败: {failure.failure_type} - {failure.error_message}")
                # 如果是文件类型检测失败，说明问题仍然存在
                if "文件类型检测失败" in failure.error_message:
                    print(f"✗ 错误：文件类型检测仍然失败，说明resource_id映射有问题")
                    return False
                else:
                    print(f"✓ 信息：文件类型检测正常，失败原因是其他问题（如解析器问题）")
                    return True
        return False
    else:
        print(f"✗ 错误：没有处理结果")
        return False


async def main():
    """主测试函数"""
    print("开始测试完整的缓存和资源ID映射流程\n")
    
    # 测试1：基本缓存功能
    success1 = await test_complete_cache_flow()
    
    # 测试2：与FileReader集成
    success2 = await test_file_reader_integration()
    
    if success1 and success2:
        print(f"\n✅ 所有测试通过！缓存和资源ID映射功能正常。")
        return True
    else:
        print(f"\n❌ 测试失败！")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
