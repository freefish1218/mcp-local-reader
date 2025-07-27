#!/usr/bin/env python3
"""
测试运行脚本
提供便捷的测试执行和报告功能
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_path=None, verbose=True, coverage=False, parallel=False):
    """
    运行测试
    
    Args:
        test_path: 特定测试路径
        verbose: 详细输出
        coverage: 生成覆盖率报告
        parallel: 并行运行测试
    """
    # 确保在项目根目录
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # 构建pytest命令
    cmd = ['python', '-m', 'pytest']
    
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append('tests/')
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=src/file_reader', '--cov-report=html', '--cov-report=term'])
    
    if parallel:
        cmd.extend(['-n', 'auto'])  # 需要pytest-xdist
    
    # 添加其他有用的选项
    cmd.extend([
        '--tb=short',
        '--strict-markers',
        '--color=yes'
    ])
    
    print(f"运行命令: {' '.join(cmd)}")
    print("-" * 50)
    
    # 执行测试
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MCP文件读取器测试运行器')
    parser.add_argument('test_path', nargs='?', help='特定测试文件或目录路径')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('-c', '--coverage', action='store_true', help='生成覆盖率报告')
    parser.add_argument('-p', '--parallel', action='store_true', help='并行运行测试')
    parser.add_argument('--models', action='store_true', help='只运行数据模型测试')
    parser.add_argument('--utils', action='store_true', help='只运行工具函数测试')
    parser.add_argument('--parsers', action='store_true', help='只运行解析器测试')
    parser.add_argument('--core', action='store_true', help='只运行核心功能测试')
    parser.add_argument('--server', action='store_true', help='只运行服务器测试')
    
    args = parser.parse_args()
    
    # 确定测试路径
    test_path = args.test_path
    if args.models:
        test_path = 'tests/test_models.py'
    elif args.utils:
        test_path = 'tests/test_utils.py'
    elif args.parsers:
        test_path = 'tests/test_parsers.py'
    elif args.core:
        test_path = 'tests/test_core.py'
    elif args.server:
        test_path = 'tests/test_mcp_server.py'
    
    # 运行测试
    return_code = run_tests(
        test_path=test_path,
        verbose=args.verbose,
        coverage=args.coverage,
        parallel=args.parallel
    )
    
    if return_code == 0:
        print("\n✅ 所有测试通过！")
    else:
        print(f"\n❌ 测试失败，返回码: {return_code}")
    
    return return_code


if __name__ == "__main__":
    sys.exit(main()) 