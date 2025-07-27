#!/usr/bin/env python3
"""
文件解析测试依赖库安装脚本
自动安装文件解析测试所需的依赖库
"""

import subprocess
import sys
import importlib


def check_library(import_name: str, lib_name: str) -> bool:
    """检查库是否已安装"""
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def install_library(lib_name: str) -> bool:
    """安装指定的库"""
    try:
        print(f"📦 正在安装 {lib_name}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", lib_name], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {lib_name} 安装成功")
            return True
        else:
            print(f"❌ {lib_name} 安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {lib_name} 安装出错: {e}")
        return False


def main():
    """主函数"""
    print("🚀 文件解析测试依赖库安装工具")
    print("=" * 50)
    
    # 定义需要安装的库
    required_libs = [
        ("docx2txt", "docx2txt", "DOC/DOCX文件解析 - 必需"),
        ("unstructured", "unstructured", "Excel文件解析 - 推荐"),
        ("striprtf", "striprtf", "RTF文件解析 - 推荐（无系统依赖）"),
        ("odf", "odfpy", "ODT文档解析 - 推荐（无系统依赖）")
    ]
    
    optional_libs = [
        ("pptx", "python-pptx", "PowerPoint文件解析 - 可选"),
        ("pypdf", "pypdf", "PDF备用解析器 - 可选"),
        ("PIL", "Pillow", "图像处理 - 可选")
    ]
    
    # 检查当前状态
    print("🔍 检查当前依赖库状态...")
    print("-" * 30)
    
    missing_required = []
    missing_optional = []
    
    for import_name, lib_name, description in required_libs:
        if check_library(import_name, lib_name):
            print(f"✅ {lib_name}: 已安装 ({description})")
        else:
            print(f"❌ {lib_name}: 未安装 ({description})")
            missing_required.append((import_name, lib_name, description))
    
    for import_name, lib_name, description in optional_libs:
        if check_library(import_name, lib_name):
            print(f"✅ {lib_name}: 已安装 ({description})")
        else:
            print(f"⚪ {lib_name}: 未安装 ({description})")
            missing_optional.append((import_name, lib_name, description))
    
    # 安装缺失的必需库
    if missing_required:
        print(f"\n🔧 安装必需的依赖库 ({len(missing_required)} 个)...")
        print("-" * 30)
        
        for import_name, lib_name, description in missing_required:
            success = install_library(lib_name)
            if not success:
                print(f"⚠️  {lib_name} 安装失败，可能影响文件解析测试")
    else:
        print(f"\n🎉 所有必需的依赖库都已安装！")
    
    # 询问是否安装可选库
    if missing_optional:
        print(f"\n❓ 是否安装可选的依赖库 ({len(missing_optional)} 个)？")
        print("   可选库可以扩展支持的文件格式")
        
        for import_name, lib_name, description in missing_optional:
            print(f"   - {lib_name}: {description}")
        
        response = input("\n是否安装可选库？(y/N): ").strip().lower()
        
        if response in ['y', 'yes']:
            print(f"\n🔧 安装可选的依赖库...")
            print("-" * 30)
            
            for import_name, lib_name, description in missing_optional:
                install_library(lib_name)
        else:
            print("⏭️  跳过可选库安装")
    
    # 验证安装结果
    print(f"\n🧪 验证安装结果...")
    print("-" * 30)
    
    all_libs = required_libs + optional_libs
    installed_count = 0
    
    for import_name, lib_name, description in all_libs:
        if check_library(import_name, lib_name):
            print(f"✅ {lib_name}: 已安装")
            installed_count += 1
        else:
            print(f"❌ {lib_name}: 未安装")
    
    print(f"\n📊 安装总结:")
    print(f"   总库数: {len(all_libs)}")
    print(f"   已安装: {installed_count}")
    print(f"   安装率: {(installed_count/len(all_libs))*100:.1f}%")
    
    # 运行测试建议
    print(f"\n💡 下一步:")
    print("   运行以下命令测试文件解析功能:")
    print("   python tests/test_real_files.py")
    
    if installed_count >= len(required_libs):
        print("\n🎉 核心依赖已安装，可以开始测试！")
        return 0
    else:
        print(f"\n⚠️  仍有 {len(required_libs)-(installed_count-len(optional_libs))} 个必需库未安装")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n❌ 安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 安装过程中发生错误: {e}")
        sys.exit(1) 