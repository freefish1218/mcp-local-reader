#!/usr/bin/env python3
"""
DOC文件解析内容质量检查脚本
使用新的LibreOffice+python-docx方案
"""

import asyncio
import sys
import subprocess
from pathlib import Path
from src.file_reader.parsers.office_parser import OfficeParser


def check_dependencies():
    """检查新方案的依赖库和工具"""
    print("🔍 检查依赖库和工具状态:")
    print("-" * 40)
    
    dependencies = {
        'docx': 'Word文档解析库 (python-docx)',
        'pptx': 'PowerPoint解析库 (python-pptx)'
    }
    
    all_available = True
    
    for lib, desc in dependencies.items():
        try:
            if lib == 'docx':
                import docx
            elif lib == 'pptx':
                import pptx
            else:
                __import__(lib)
            print(f"  ✅ {lib} - {desc}")
        except ImportError:
            print(f"  ❌ {lib} - {desc} (未安装)")
            all_available = False
    
    # 检查LibreOffice命令行工具
    libreoffice_commands = ['libreoffice', 'soffice', '/Applications/LibreOffice.app/Contents/MacOS/soffice']
    libreoffice_found = False
    
    for cmd in libreoffice_commands:
        try:
            result = subprocess.run([cmd, '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0] if result.stdout else 'LibreOffice'
                print(f"  ✅ {cmd} - 文档转换工具 ({version_line})")
                libreoffice_found = True
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        except Exception:
            continue
    
    if not libreoffice_found:
        print(f"  ❌ LibreOffice - 文档转换工具 (未安装)")
        all_available = False
    
    return all_available


def test_new_methods():
    """测试新的DOC解析方法"""
    print("\n🔧 测试新的DOC解析方法:")
    print("-" * 40)
    
    parser = OfficeParser()
    
    # 检查新增的方法
    new_methods = [
        '_convert_doc_to_docx_with_libreoffice',
        '_parse_docx_file',
        '_parse_docx_content'
    ]
    
    all_methods_exist = True
    for method in new_methods:
        if hasattr(parser, method):
            print(f"  ✅ {method}")
        else:
            print(f"  ❌ {method} - 未找到")
            all_methods_exist = False
    
    # 检查移除的旧方法
    removed_methods = [
        '_convert_doc_to_docx',  # 旧的pypandoc方法
        '_parse_doc_file',
        '_parse_doc_with_oletools',
        '_extract_text_from_ole_data'
    ]
    
    print("\n  已移除的旧方法:")
    for method in removed_methods:
        if hasattr(parser, method):
            print(f"  ⚠️  {method} - 仍然存在（应该已移除）")
        else:
            print(f"  ✅ {method} - 已正确移除")
    
    return all_methods_exist


def check_doc_content():
    """检查DOC文件解析内容的质量"""
    parser = OfficeParser()
    
    test_files = [
        "tests/files/test1.doc",
        "tests/files/test2.doc"
    ]
    
    for test_file in test_files:
        file_path = Path(test_file)
        if not file_path.exists():
            print(f"⚠️  文件不存在: {test_file}")
            continue
            
        print(f"\n{'='*60}")
        print(f"📄 检查文件: {test_file}")
        print(f"{'='*60}")
        
        # 读取文件并解析
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # 解析文件
        result = parser.parse(content, file_path.suffix)
        
        if not result.success:
            print(f"❌ 解析失败: {result.error}")
            continue
        
        # 分析文本内容
        text = result.content
        print(f"✅ 解析成功")
        print(f"📊 文本长度: {len(text)} 字符")
        
        # 显示使用的解析器信息
        if result.metadata:
            parser_info = result.metadata.get('parser', '未知')
            conversion_info = result.metadata.get('conversion', '无')
            print(f"🔧 解析器: {parser_info}")
            if conversion_info != '无':
                print(f"🔄 转换过程: {conversion_info}")
        
        # 检查字符编码质量
        print(f"\n🔍 字符编码质量分析:")
        
        # 统计中文字符
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        print(f"   中文字符数量: {chinese_chars}")
        
        # 统计ASCII字符
        ascii_chars = sum(1 for char in text if ord(char) < 128)
        print(f"   ASCII字符数量: {ascii_chars}")
        
        # 统计控制字符和可能的乱码
        control_chars = sum(1 for char in text if ord(char) < 32 and char not in '\n\r\t')
        print(f"   控制字符数量: {control_chars}")
        
        # 统计高位字符（可能的乱码指示）
        high_chars = sum(1 for char in text if ord(char) > 65535)
        print(f"   高位字符数量: {high_chars}")
        
        # 检查常见乱码模式
        garbled_patterns = ['�', '\ufffd']
        garbled_count = sum(text.count(pattern) for pattern in garbled_patterns)
        print(f"   乱码字符数量: {garbled_count}")
        
        # 显示前500字符样本
        print(f"\n📝 文本内容样本（前500字符）:")
        print("-" * 50)
        sample = text[:500]
        print(repr(sample))
        
        # 显示可读文本样本
        print(f"\n📖 可读文本样本（前500字符）:")
        print("-" * 50)
        readable_sample = ''.join(char if char.isprintable() or char in '\n\r\t' else '□' for char in sample)
        print(readable_sample)
        
        # 文本质量评估
        print(f"\n📈 文本质量评估:")
        total_chars = len(text)
        if total_chars > 0:
            chinese_ratio = chinese_chars / total_chars * 100
            ascii_ratio = ascii_chars / total_chars * 100
            control_ratio = control_chars / total_chars * 100
            garbled_ratio = garbled_count / total_chars * 100
            
            print(f"   中文字符占比: {chinese_ratio:.2f}%")
            print(f"   ASCII字符占比: {ascii_ratio:.2f}%")
            print(f"   控制字符占比: {control_ratio:.2f}%")
            print(f"   乱码字符占比: {garbled_ratio:.2f}%")
            
            # 质量判断
            if garbled_ratio > 5:
                print(f"   🚨 质量评估: 严重乱码 (乱码率 {garbled_ratio:.2f}%)")
            elif garbled_ratio > 1:
                print(f"   ⚠️  质量评估: 轻微乱码 (乱码率 {garbled_ratio:.2f}%)")
            elif control_ratio > 10:
                print(f"   ⚠️  质量评估: 控制字符过多 (控制字符率 {control_ratio:.2f}%)")
            else:
                print(f"   ✅ 质量评估: 文本质量良好")


def main():
    """主函数"""
    print("🚀 DOC文件解析测试 - 新LibreOffice+python-docx方案")
    print("=" * 60)
    
    # 检查依赖
    deps_ok = check_dependencies()
    if not deps_ok:
        print("\n❌ 依赖库检查失败，请安装缺失的库和工具:")
        print("   pip install python-docx python-pptx")
        print("   # 安装LibreOffice:")
        print("   brew install --cask libreoffice  # macOS")
        print("   sudo apt-get install libreoffice  # Ubuntu/Debian")
        print("   # 或从官网下载: https://www.libreoffice.org/download/")
        return
    
    # 测试新方法
    methods_ok = test_new_methods()
    if not methods_ok:
        print("\n❌ 某些新方法未正确实现")
        return
    
    print("\n✅ 依赖和方法检查通过，开始文档解析测试")
    
    # 检查DOC文件内容
    check_doc_content()
    
    print(f"\n{'='*60}")
    print("🎉 DOC文件解析测试完成!")
    print("\n📋 新方案优势:")
    print("   • 使用LibreOffice专业转换工具，支持复杂格式")
    print("   • python-docx纯Python解析，稳定性更好")
    print("   • 移除复杂的OLE二进制解析，代码更简洁")
    print("   • 支持表格、段落等丰富格式提取")
    print("   • 兼容性强，LibreOffice支持多种Office格式")


if __name__ == "__main__":
    main() 