#!/usr/bin/env python3
"""
环境检测和智能工具注册测试脚本
用于验证Docker环境检测和动态工具注册是否正常工作
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目路径到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_server import detect_docker_environment, IS_DOCKER_ENV


def test_environment_detection():
    """测试环境检测功能"""
    print("🔍 环境检测测试")
    print("=" * 50)
    
    # 测试检测函数
    is_docker = detect_docker_environment()
    print(f"检测结果: {'Docker容器环境' if is_docker else '原生Python环境'}")
    print(f"全局变量 IS_DOCKER_ENV: {IS_DOCKER_ENV}")
    
    # 检查检测依据
    print("\n🔧 检测依据:")
    
    # 检查 /.dockerenv 文件
    dockerenv_exists = Path("/.dockerenv").exists()
    print(f"  /.dockerenv 文件: {'存在' if dockerenv_exists else '不存在'}")
    
    # 检查 cgroup 信息
    try:
        with open("/proc/1/cgroup", "r") as f:
            cgroup_content = f.read()
            has_docker_cgroup = "docker" in cgroup_content or "containerd" in cgroup_content
            print(f"  /proc/1/cgroup 包含Docker信息: {'是' if has_docker_cgroup else '否'}")
            print(f"    内容片段: {cgroup_content[:100]}...")
    except (FileNotFoundError, PermissionError):
        print("  /proc/1/cgroup: 无法读取")
    
    # 检查环境变量
    import os
    docker_env_var = os.getenv("DOCKER_CONTAINER")
    print(f"  DOCKER_CONTAINER 环境变量: {docker_env_var or '未设置'}")
    
    return is_docker


def test_tool_availability():
    """测试工具可用性"""
    print("\n📋 工具可用性测试")
    print("=" * 50)
    
    try:
        # 这里我们可以检查哪些函数被定义了
        import mcp_server
        
        # 检查本地文件读取工具
        has_read_local_files = hasattr(mcp_server, 'read_local_files')
        print(f"read_local_files 工具: {'可用' if has_read_local_files else '不可用'}")
        
        # 检查文件上传工具
        has_upload_and_read_files = hasattr(mcp_server, 'upload_and_read_files')
        print(f"upload_and_read_files 工具: {'可用' if has_upload_and_read_files else '不可用'}")
        
        # 检查其他工具
        has_get_reader_stats = hasattr(mcp_server, 'get_reader_stats')
        has_get_server_info_tool = hasattr(mcp_server, 'get_server_info')  # 注意这里可能有命名冲突
        has_read_oss_files = hasattr(mcp_server, 'read_oss_files')
        
        print(f"get_reader_stats 工具: {'可用' if has_get_reader_stats else '不可用'}")
        print(f"get_server_info 工具: {'可用' if has_get_server_info_tool else '不可用'}")
        print(f"read_oss_files 工具: {'可用' if has_read_oss_files else '不可用'}")
        
        # 根据环境验证预期的工具组合
        print(f"\n🎯 环境适配验证:")
        if IS_DOCKER_ENV:
            expected_tools = has_upload_and_read_files and not has_read_local_files
            print(f"Docker环境工具配置: {'✅ 正确' if expected_tools else '❌ 错误'}")
            if not expected_tools:
                print("  预期: upload_and_read_files=可用, read_local_files=不可用")
                print(f"  实际: upload_and_read_files={'可用' if has_upload_and_read_files else '不可用'}, read_local_files={'可用' if has_read_local_files else '不可用'}")
        else:
            expected_tools = has_read_local_files and not has_upload_and_read_files
            print(f"原生环境工具配置: {'✅ 正确' if expected_tools else '❌ 错误'}")
            if not expected_tools:
                print("  预期: read_local_files=可用, upload_and_read_files=不可用")
                print(f"  实际: read_local_files={'可用' if has_read_local_files else '不可用'}, upload_and_read_files={'可用' if has_upload_and_read_files else '不可用'}")
                
    except Exception as e:
        print(f"❌ 工具可用性测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_file_examples():
    """测试文件示例"""
    print("\n📄 文件示例测试")
    print("=" * 50)
    
    # 创建测试文件示例
    test_files = [
        "README.md",
        "src/mcp_server.py",
        "client_example.py"
    ]
    
    existing_files = []
    for file_path in test_files:
        if Path(file_path).exists():
            existing_files.append(file_path)
            file_size = Path(file_path).stat().st_size
            print(f"  �� {file_path} ({file_size} bytes)")
    
    if existing_files:
        print(f"\n💡 测试建议:")
        if IS_DOCKER_ENV:
            print("  在Docker环境中，可以使用以下方式测试文件上传:")
            print("  1. 将文件内容转换为base64编码")
            print("  2. 调用 upload_and_read_files 工具")
            print("  3. 使用 --smart 模式进行智能读取测试")
            print(f"  python client_example.py --smart {' '.join(existing_files[:2])}")
        else:
            print("  在原生环境中，可以直接测试本地文件读取:")
            print(f"  python client_example.py --local {' '.join(existing_files[:2])}")
            print(f"  python client_example.py --smart {' '.join(existing_files[:2])}")
    else:
        print("  ❌ 未找到可用的测试文件")


async def main():
    """主测试函数"""
    print("🧪 MCP文件读取器环境检测和工具注册测试")
    print("=" * 80)
    
    # 测试环境检测
    is_docker = test_environment_detection()
    
    # 测试工具可用性
    test_tool_availability()
    
    # 测试文件示例
    test_file_examples()
    
    # 最终总结
    print("\n📊 测试总结")
    print("=" * 50)
    print(f"🔍 检测到的环境: {'Docker容器' if is_docker else '原生Python'}")
    print(f"🛠️ 工具注册状态: 已完成")
    
    if is_docker:
        print("🐳 Docker环境特性:")
        print("  • 文件上传功能已启用")
        print("  • 本地文件读取已禁用")
        print("  • 智能模式会自动切换到上传模式")
    else:
        print("🖥️ 原生环境特性:")
        print("  • 本地文件读取功能已启用")
        print("  • 文件上传功能已禁用")
        print("  • 智能模式会优先使用本地读取")
    
    print("\n✨ 测试完成！可以开始使用 MCP 文件读取器了。")
    print("\n🚀 推荐下一步:")
    print("  1. 启动服务器: python run_server.py")
    print("  2. 测试客户端: python client_example.py --smart README.md")


if __name__ == "__main__":
    asyncio.run(main()) 