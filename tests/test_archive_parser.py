#!/usr/bin/env python3
"""
压缩文件解析器测试
测试ZIP、RAR、7Z等压缩文件的解析功能
"""

import asyncio
import os
import sys
import tempfile
import zipfile
from pathlib import Path
import pytest

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from file_reader.parsers.archive_parser import ArchiveParser


async def create_test_zip():
    """创建测试用的ZIP文件"""
    print("📦 创建测试ZIP文件...")
    
    # 创建临时目录和文件
    temp_dir = tempfile.mkdtemp()
    
    # 创建一些测试文件
    test_files = {
        'README.md': '# 项目说明\n\n这是一个测试项目。\n\n## 功能特性\n\n- 功能1\n- 功能2',
        'config.json': '{\n  "name": "test-project",\n  "version": "1.0.0",\n  "description": "测试项目配置"\n}',
        'docs/guide.txt': '用户指南\n\n1. 安装步骤\n2. 配置说明\n3. 使用方法',
        'src/main.py': 'def main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()',
        'images/logo.txt': '这里应该是logo图片的文本描述'
    }
    
    # 创建文件
    for rel_path, content in test_files.items():
        file_path = Path(temp_dir) / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
    
    # 创建ZIP文件
    zip_path = Path(temp_dir) / 'test_project.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for rel_path in test_files.keys():
            file_path = Path(temp_dir) / rel_path
            zipf.write(file_path, rel_path)
    
    print(f"✅ 测试ZIP文件创建完成: {zip_path}")
    return zip_path


@pytest.mark.asyncio
async def test_archive_parser():
    """测试压缩文件解析器"""
    print("🚀 压缩文件解析器测试")
    print("=" * 60)
    
    try:
        # 创建测试ZIP文件
        zip_path = await create_test_zip()
        
        # 创建解析器
        parser = ArchiveParser()
        
        # 读取ZIP文件内容
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        print(f"\n📄 测试文件: {zip_path.name}")
        print(f"📊 文件大小: {len(zip_content):,} 字节")
        
        # 解析ZIP文件
        print("\n🔍 开始解析...")
        result = parser.parse(zip_content, '.zip')
        
        if result.success:
            print("✅ 解析成功!")
            print(f"\n📝 解析结果 (文档类型: {result.doc_type}):")
            print("-" * 40)
            
            # 显示Markdown内容的前500个字符
            content_preview = result.content[:500]
            print(content_preview)
            if len(result.content) > 500:
                print("...(内容已截断)")
            
            print("-" * 40)
            
            # 显示元数据
            print(f"\n📋 元数据信息:")
            metadata = result.metadata
            print(f"   - 解析器: {metadata.get('parser', 'N/A')}")
            print(f"   - 原始格式: {metadata.get('original_format', 'N/A')}")
            print(f"   - 输出格式: {metadata.get('output_format', 'N/A')}")
            print(f"   - 文件数量: {metadata.get('file_count', 'N/A')}")
            print(f"   - 压缩包大小: {metadata.get('archive_size', 'N/A')} 字节")
            print(f"   - 解压后大小: {metadata.get('total_extracted_size', 'N/A')} 字节")
            print(f"   - 压缩率: {metadata.get('compression_ratio', 'N/A')}%")
            
            if 'file_type_distribution' in metadata:
                print(f"   - 文件类型分布: {metadata['file_type_distribution']}")
            
            # 显示文件资源信息
            file_resources = metadata.get('file_resources', [])
            print(f"\n📂 文件资源: {len(file_resources)} 个")
            for i, resource in enumerate(file_resources[:5], 1):  # 只显示前5个
                print(f"   {i}. {resource.get('filename', 'N/A')} ({resource.get('format', 'N/A')})")
            if len(file_resources) > 5:
                print(f"   ... 还有 {len(file_resources) - 5} 个文件")
        
        else:
            print("❌ 解析失败!")
            print(f"错误信息: {result.error}")
    
    except Exception as e:
        print(f"❌ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理临时文件
        if 'zip_path' in locals():
            try:
                temp_dir = zip_path.parent
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"\n🧹 已清理临时文件: {temp_dir}")
            except:
                pass


@pytest.mark.asyncio
async def test_unsupported_format():
    """测试不支持的格式"""
    print("\n" + "=" * 60)
    print("🧪 测试不支持的格式")
    
    parser = ArchiveParser()
    
    # 测试不支持的扩展名
    test_content = b"fake archive content"
    result = parser.parse(test_content, '.xyz')
    
    if not result.success:
        print("✅ 正确拒绝不支持的格式")
        print(f"   错误信息: {result.error}")
    else:
        print("❌ 应该拒绝不支持的格式")


@pytest.mark.asyncio
async def test_empty_content():
    """测试空内容"""
    print("\n" + "=" * 60)
    print("🧪 测试空内容处理")
    
    parser = ArchiveParser()
    
    # 测试空内容
    result = parser.parse(b"", '.zip')
    
    if not result.success:
        print("✅ 正确处理空内容")
        print(f"   错误信息: {result.error}")
    else:
        print("❌ 应该拒绝空内容")


async def main():
    """主函数"""
    await test_archive_parser()
    await test_unsupported_format()
    await test_empty_content()
    
    print("\n" + "=" * 60)
    print("🎉 压缩文件解析器测试完成")


if __name__ == "__main__":
    asyncio.run(main())
