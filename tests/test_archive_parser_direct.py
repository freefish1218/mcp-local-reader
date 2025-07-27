#!/usr/bin/env python3
"""
压缩文件解析器直接测试
直接测试解析器功能，不依赖完整的文件读取流程
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

from file_reader.parsers.archive_parser import ArchiveParser


class MockStorageClient:
    """模拟存储客户端"""
    
    def __init__(self):
        self.uploaded_files = []
        self.enabled = True

    async def upload_files_batch(self, files):
        """模拟文件批量上传"""
        results = []
        for i, file_info in enumerate(files):
            filename = file_info.get('filename', f'file_{i}')
            file_data = file_info.get('data', b'')
            
            # 模拟resource_id生成
            resource_id = f"archive_file_{len(self.uploaded_files):04d}_{filename}"
            file_url = f"file:///{resource_id}"
            
            # 记录上传
            self.uploaded_files.append({
                'filename': filename,
                'size': len(file_data),
                'resource_id': resource_id
            })
            
            # 返回成功结果
            results.append({
                'success': True,
                'url': file_url,
                'resource_id': resource_id,
                'filename': filename,
                'size': len(file_data),
                'content_type': file_info.get('content_type', 'application/octet-stream')
            })
        
        return results


async def create_test_zip():
    """创建测试ZIP文件"""
    print("📦 创建测试ZIP文件...")
    
    temp_dir = tempfile.mkdtemp()
    
    # 创建测试文件内容
    test_files = {
        'README.md': '''# 测试项目

这是一个压缩文件解析测试项目。

## 包含文件类型

- Markdown文档
- JSON配置
- Python代码
- 纯文本文件

## 目录结构

参见下方的文件列表。
''',
        'config.json': json.dumps({
            "name": "test-archive",
            "version": "1.0.0",
            "description": "压缩文件解析测试",
            "settings": {
                "debug": True,
                "port": 8080
            }
        }, indent=2),
        'src/main.py': '''#!/usr/bin/env python3
"""
主程序入口
"""

def main():
    print("Hello from archive!")
    print("这是从压缩包中提取的Python文件")
    
if __name__ == "__main__":
    main()
''',
        'docs/usage.txt': '''使用说明文档

1. 解压压缩包
2. 阅读README.md
3. 运行src/main.py
4. 查看配置文件config.json

注意：这是一个测试文件。
''',
        'data/sample.csv': '''id,name,type
1,文件A,文档
2,文件B,图片
3,文件C,视频
''',
    }
    
    # 创建文件
    for rel_path, content in test_files.items():
        file_path = Path(temp_dir) / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
    
    # 创建ZIP文件
    zip_path = Path(temp_dir) / 'test_archive.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for rel_path in test_files.keys():
            file_path = Path(temp_dir) / rel_path
            zipf.write(file_path, rel_path)
    
    print(f"✅ 测试ZIP创建完成: {zip_path}")
    print(f"   包含 {len(test_files)} 个文件")
    print(f"   大小: {zip_path.stat().st_size} 字节")
    
    return zip_path, test_files


@pytest.mark.asyncio
async def test_archive_parser_direct():
    """直接测试压缩文件解析器"""
    print("🚀 压缩文件解析器直接测试")
    print("=" * 60)
    
    try:
        # 创建测试ZIP
        zip_path, expected_files = await create_test_zip()
        
        # 创建模拟存储客户端
        mock_storage = MockStorageClient()
        
        # 创建解析器并设置存储客户端
        parser = ArchiveParser(storage_client=mock_storage)
        
        # 读取ZIP内容
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        print(f"\n📄 解析文件: {zip_path.name}")
        print(f"📊 文件大小: {len(zip_content):,} 字节")
        
        # 直接调用解析器
        print("\n🔍 开始解析...")
        result = parser.parse(zip_content, '.zip')
        
        if result.success:
            print("✅ 解析成功!")
            
            # 验证基本信息
            print(f"\n📝 解析结果:")
            print(f"   - 文档类型: {result.doc_type}")
            print(f"   - 内容长度: {len(result.content):,} 字符")
            
            # 检查Markdown内容结构
            content = result.content
            required_sections = [
                "压缩包内容",
                "压缩包信息", 
                "文件结构",
                "文件列表"
            ]
            
            for section in required_sections:
                if section in content:
                    print(f"   ✅ 包含 '{section}' 部分")
                else:
                    print(f"   ❌ 缺少 '{section}' 部分")
            
            # 检查文件名
            missing_files = []
            for filename in expected_files.keys():
                if filename in content:
                    print(f"   ✅ 找到文件: {filename}")
                else:
                    missing_files.append(filename)
            
            if missing_files:
                print(f"   ❌ 缺少文件: {missing_files}")
            
            # 检查元数据
            metadata = result.metadata
            print(f"\n📋 元数据验证:")
            print(f"   - 解析器: {metadata.get('parser')}")
            print(f"   - 文件数量: {metadata.get('file_count')} (期望: {len(expected_files)})")
            print(f"   - 压缩包大小: {metadata.get('archive_size')} 字节")
            print(f"   - 解压后大小: {metadata.get('total_extracted_size')} 字节")
            print(f"   - 压缩率: {metadata.get('compression_ratio')}%")
            
            # 验证文件资源
            file_resources = metadata.get('file_resources', [])
            print(f"   - 文件资源: {len(file_resources)} 个")
            
            # 检查上传结果
            print(f"\n📤 上传验证:")
            print(f"   - 上传文件数: {len(mock_storage.uploaded_files)}")
            
            if mock_storage.uploaded_files:
                print("   - 上传的文件:")
                for uploaded in mock_storage.uploaded_files[:3]:
                    print(f"     • {uploaded['filename']} ({uploaded['size']} 字节)")
                if len(mock_storage.uploaded_files) > 3:
                    print(f"     ... 还有 {len(mock_storage.uploaded_files) - 3} 个")
            
            # 检查file://链接
            file_links = content.count('file:///')
            print(f"   - file:///链接数: {file_links}")
            
            # 显示部分内容样例
            print(f"\n📄 内容样例 (前500字符):")
            print("-" * 40)
            print(content[:500])
            if len(content) > 500:
                print("...(内容已截断)")
            print("-" * 40)
            
            return True
            
        else:
            print(f"❌ 解析失败: {result.error}")
            return False
    
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理
        if 'zip_path' in locals():
            try:
                temp_dir = zip_path.parent
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"\n🧹 已清理临时文件")
            except:
                pass


@pytest.mark.asyncio
async def test_error_cases():
    """测试错误情况"""
    print("\n" + "=" * 60)
    print("🧪 测试错误情况")
    
    parser = ArchiveParser()
    
    # 1. 测试不支持的格式
    print("\n1. 测试不支持的格式")
    result = parser.parse(b"test content", '.xyz')
    if not result.success:
        print(f"   ✅ 正确拒绝: {result.error}")
    else:
        print(f"   ❌ 应该拒绝不支持的格式")
    
    # 2. 测试空内容
    print("\n2. 测试空内容")
    result = parser.parse(b"", '.zip')
    if not result.success:
        print(f"   ✅ 正确拒绝: {result.error}")
    else:
        print(f"   ❌ 应该拒绝空内容")
    
    # 3. 测试损坏的ZIP
    print("\n3. 测试损坏的ZIP")
    result = parser.parse(b"PK\x03\x04invalid", '.zip')
    if not result.success:
        print(f"   ✅ 正确处理损坏文件: {result.error}")
    else:
        print(f"   ❌ 应该拒绝损坏文件")


@pytest.mark.asyncio
async def test_file_types():
    """测试支持的文件类型"""
    print("\n" + "=" * 60)
    print("🧪 测试支持的文件类型")
    
    parser = ArchiveParser()
    
    supported_formats = ['.zip', '.rar', '.7z', '.tar', '.gz', '.tar.gz', '.tgz']
    
    for fmt in supported_formats:
        # 只检查是否进入解析逻辑（会失败但不是因为格式不支持）
        result = parser.parse(b"fake content", fmt)
        if "不支持的压缩文件类型" not in str(result.error):
            print(f"   ✅ 支持格式: {fmt}")
        else:
            print(f"   ❌ 不支持格式: {fmt}")


async def main():
    """主函数"""
    print("🎯 压缩文件解析器直接测试\n")
    
    # 运行主要测试
    success = await test_archive_parser_direct()
    
    # 运行错误测试
    await test_error_cases()
    
    # 运行格式测试
    await test_file_types()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 压缩文件解析器测试通过!")
    else:
        print("❌ 压缩文件解析器测试失败!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
