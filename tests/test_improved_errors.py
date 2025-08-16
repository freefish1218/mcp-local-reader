#!/usr/bin/env python3
"""
测试改进的错误信息
验证文件大小限制的明确提示
"""

import os
import sys
import asyncio

# 添加项目路径到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from file_reader.storage import LocalFileStorageClient
from file_reader.core import FileReader
from file_reader.models import LocalReadRequest


async def test_improved_error_messages():
    """测试改进的错误信息"""
    print("🔧 测试改进的错误信息")
    print("=" * 50)
    
    # 使用小的文件大小限制来触发错误
    test_files = [
        "tests/files/test.pptx",  # 20.5 MB
        "tests/files/test2.ppt"   # 47.5 MB
    ]
    
    # 创建本地文件存储客户端，使用10MB限制（故意设置小的限制）
    print("📏 测试场景1: 使用10MB文件大小限制")
    cwd = os.getcwd()
    client = LocalFileStorageClient(
        allowed_directories=[cwd],
        allow_absolute_paths=True,
        max_file_size=10 * 1024 * 1024  # 10MB
    )
    
    # 创建文件读取器
    reader = FileReader(
        storage_client=client,
        max_workers=1,
        max_file_size=10 * 1024 * 1024,  # 10MB
        min_content_length=10
    )
    
    # 测试第一个文件
    try:
        result = await reader._process_single_file_async("tests/files/test.pptx", 10 * 1024 * 1024)
        if result:
            success, error_msg, error_type = result
            print(f"  📄 test.pptx:")
            print(f"    成功: {success}")
            print(f"    错误类型: {error_type}")
            print(f"    错误信息: {error_msg}")
    except Exception as e:
        print(f"  ❌ test.pptx 测试异常: {e}")
    
    print(f"\n📏 测试场景2: 使用5MB请求大小限制")
    # 创建更大的本地存储限制，但使用小的请求限制
    client2 = LocalFileStorageClient(
        allowed_directories=[cwd],
        allow_absolute_paths=True,
        max_file_size=100 * 1024 * 1024  # 100MB
    )
    
    reader2 = FileReader(
        storage_client=client2,
        max_workers=1,
        max_file_size=100 * 1024 * 1024,  # 100MB
        min_content_length=10
    )
    
    # 使用异步方法测试文件读取
    request = ReadRequest(
        resource_ids=["tests/files/test.pptx"],
        max_size=5 * 1024 * 1024  # 5MB请求限制
    )
    
    try:
        response = await reader2.read_file(request)
        
        for failed in response.failed:
            print(f"  📄 {failed.resource_id}:")
            print(f"    错误类型: {failed.type}")
            print(f"    错误信息: {failed.error_message}")
    except Exception as e:
        print(f"  ❌ 请求大小限制测试异常: {e}")

    print(f"\n📏 测试场景3: 正常工作场景（100MB限制）")
    # 测试正常工作的场景
    request3 = ReadRequest(
        resource_ids=["tests/files/test.pptx"],
        max_size=100 * 1024 * 1024  # 100MB请求限制
    )
    
    try:
        response = await reader2.read_files(request3)
        
        if response.contents:
            content = response.contents[0]
            print(f"  ✅ {content.resource_id}: 成功解析 {len(content.content)} 字符")
        
        for failed in response.failed:
            print(f"  ❌ {failed.resource_id}: {failed.type} - {failed.error_message}")
    except Exception as e:
        print(f"  ❌ 正常场景测试异常: {e}")


def test_security_explanation():
    """展示安全配置的说明"""
    print(f"\n🔒 安全配置说明")
    print("=" * 50)
    
    print("📋 绝对路径限制的安全考虑:")
    print("  1. 防止路径遍历攻击:")
    print("     - 恶意访问 /etc/passwd")
    print("     - 读取 ~/.ssh/id_rsa")
    print("     - 访问 /var/log/auth.log")
    print()
    print("  2. 保护敏感文件:")
    print("     - 应用配置文件（密码、API密钥）")
    print("     - 其他用户的私人文件")
    print("     - 系统配置和环境变量")
    print()
    print("  3. 最佳实践:")
    print("     - 默认拒绝绝对路径（安全优先）")
    print("     - 通过 LOCAL_FILE_ALLOW_ABSOLUTE_PATHS=true 显式启用")
    print("     - 限制访问范围在指定目录内")
    print()
    print("📏 文件大小限制:")
    print("  - OSS文件: 默认10MB限制（可通过max_size参数调整）")
    print("  - 本地文件: 默认50MB限制（可通过环境变量配置）")
    print("  - 防止内存耗尽和超时问题")
    print("  - 现在提供明确的大小超限提示")


if __name__ == "__main__":
    test_security_explanation()
    asyncio.run(test_improved_error_messages()) 