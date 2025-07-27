#!/usr/bin/env python3
"""
OSS资源解析测试脚本
直接使用 OSS 上的 resource_id 测试文件解析功能
resource_id 对应 tests/files 目录下的文件名
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from file_reader import FileReader, ReadRequest
from file_reader.utils import get_logger


class OSSParsingTester:
    """OSS解析测试器"""
    
    def __init__(self):
        self.logger = get_logger("oss_parsing_tester")
        self.file_reader = FileReader()
        
        # 获取 tests/files 目录下的所有文件作为 resource_id
        self.test_files = self._get_test_files()
    
    def _get_test_files(self) -> List[str]:
        """获取测试文件列表"""
        files_dir = Path("tests/files")
        if not files_dir.exists():
            self.logger.error(f"测试文件目录不存在: {files_dir}")
            return []
        
        test_files = []
        for file_path in files_dir.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                test_files.append(file_path.name)
        
        test_files.sort()
        return test_files
    
    async def test_single_file(self, resource_id: str, max_size: int = 50 * 1024 * 1024):
        """测试单个文件解析"""
        print(f"\n{'='*60}")
        print(f"🔍 测试文件: {resource_id}")
        print(f"{'='*60}")
        
        try:
            # 创建读取请求
            request = ReadRequest(
                resource_ids=[resource_id],
                max_size=max_size
            )
            
            # 执行解析
            response = await self.file_reader.read_files(request)
            
            # 显示结果
            if response.contents:
                content = response.contents[0]
                print(f"✅ 解析成功")
                print(f"📄 资源ID: {content.resource_id}")
                print(f"📝 内容长度: {len(content.content)} 字符")
                
                # 显示内容预览
                if content.content:
                    preview = content.content[:200].replace('\n', '\\n')
                    if len(content.content) > 200:
                        preview += "..."
                    print(f"🔤 内容预览: {preview}")
                else:
                    print("⚠️  内容为空")
            
            if response.failed:
                failure = response.failed[0]
                print(f"❌ 解析失败")
                print(f"📄 资源ID: {failure.resource_id}")
                print(f"🚫 失败类型: {failure.type}")
                print(f"💭 错误信息: {failure.error_message}")
            
            return response
            
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def test_batch_files(self, resource_ids: List[str], max_size: int = 50 * 1024 * 1024):
        """批量测试文件解析"""
        print(f"\n{'='*60}")
        print(f"📦 批量测试 {len(resource_ids)} 个文件")
        print(f"{'='*60}")
        
        try:
            # 创建读取请求
            request = ReadRequest(
                resource_ids=resource_ids,
                max_size=max_size
            )
            
            # 执行解析
            response = await self.file_reader.read_files(request)
            
            # 显示统计
            success_count = len(response.contents)
            failure_count = len(response.failed)
            total_count = len(resource_ids)
            success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
            
            print(f"\n📊 批量解析结果统计:")
            print(f"   总文件数: {total_count}")
            print(f"   成功解析: {success_count}")
            print(f"   解析失败: {failure_count}")
            print(f"   成功率: {success_rate:.1f}%")
            
            # 显示成功的文件
            if response.contents:
                print(f"\n✅ 成功解析的文件:")
                total_content_length = 0
                for content in response.contents:
                    print(f"   - {content.resource_id}: {len(content.content)} 字符")
                    total_content_length += len(content.content)
                print(f"   总内容长度: {total_content_length} 字符")
            
            # 显示失败的文件
            if response.failed:
                print(f"\n❌ 解析失败的文件:")
                for failure in response.failed:
                    print(f"   - {failure.resource_id}: {failure.type} - {failure.error_message}")
            
            return response
            
        except Exception as e:
            print(f"❌ 批量测试异常: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def test_by_file_type(self):
        """按文件类型分组测试"""
        print(f"\n{'='*60}")
        print(f"📂 按文件类型分组测试")
        print(f"{'='*60}")
        
        # 按文件扩展名分组
        file_groups = {}
        for file_name in self.test_files:
            ext = Path(file_name).suffix.lower()
            if ext not in file_groups:
                file_groups[ext] = []
            file_groups[ext].append(file_name)
        
        # 逐个类型测试
        for ext, files in sorted(file_groups.items()):
            print(f"\n🔍 测试 {ext} 格式文件 ({len(files)} 个):")
            print(f"   文件: {', '.join(files)}")
            
            response = await self.test_batch_files(files)
            if response:
                success_count = len(response.contents)
                failure_count = len(response.failed)
                success_rate = (success_count / len(files)) * 100 if files else 0
                print(f"   结果: {success_count}/{len(files)} 成功 ({success_rate:.1f}%)")
    
    async def test_performance(self, max_concurrent: int = 3):
        """性能测试"""
        print(f"\n{'='*60}")
        print(f"⚡ 性能测试 (最大并发: {max_concurrent})")
        print(f"{'='*60}")
        
        import time
        
        # 测试并发处理
        start_time = time.time()
        
        # 分批处理文件
        batch_size = max_concurrent
        all_responses = []
        
        for i in range(0, len(self.test_files), batch_size):
            batch_files = self.test_files[i:i + batch_size]
            print(f"\n处理批次 {i//batch_size + 1}: {len(batch_files)} 个文件")
            
            batch_start = time.time()
            response = await self.test_batch_files(batch_files)
            batch_end = time.time()
            
            if response:
                all_responses.append(response)
                batch_time = batch_end - batch_start
                print(f"批次处理时间: {batch_time:.2f}秒")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 统计总体结果
        total_success = sum(len(resp.contents) for resp in all_responses)
        total_failure = sum(len(resp.failed) for resp in all_responses)
        total_files = len(self.test_files)
        
        print(f"\n📊 性能测试结果:")
        print(f"   总处理时间: {total_time:.2f}秒")
        print(f"   总文件数: {total_files}")
        print(f"   成功解析: {total_success}")
        print(f"   解析失败: {total_failure}")
        print(f"   平均每文件: {total_time/total_files:.2f}秒")
        print(f"   成功率: {(total_success/total_files)*100:.1f}%")
    
    def get_stats(self):
        """获取解析器统计信息"""
        print(f"\n{'='*60}")
        print(f"📈 解析器统计信息")
        print(f"{'='*60}")
        
        stats = self.file_reader.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🧪 OSS资源解析综合测试")
        print("=" * 80)
        
        if not self.test_files:
            print("❌ 未找到测试文件")
            return
        
        print(f"📂 找到 {len(self.test_files)} 个测试文件:")
        for i, file_name in enumerate(self.test_files, 1):
            print(f"   {i:2d}. {file_name}")
        
        # 1. 单文件测试（选择几个代表性文件）
        print(f"\n🔍 单文件详细测试:")
        representative_files = self.test_files[:3]  # 测试前3个文件
        for file_name in representative_files:
            await self.test_single_file(file_name)
        
        # 2. 批量测试
        await self.test_batch_files(self.test_files)
        
        # 3. 按文件类型测试
        await self.test_by_file_type()
        
        # 4. 性能测试
        await self.test_performance()
        
        # 5. 显示统计信息
        self.get_stats()
        
        print(f"\n{'='*80}")
        print("🎯 所有测试完成!")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OSS资源解析测试脚本")
    parser.add_argument("--file", "-f", help="测试指定文件")
    parser.add_argument("--batch", "-b", action="store_true", help="批量测试所有文件")
    parser.add_argument("--type", "-t", help="测试指定文件类型 (如: .pdf)")
    parser.add_argument("--performance", "-p", action="store_true", help="性能测试")
    parser.add_argument("--all", "-a", action="store_true", help="运行所有测试")
    
    args = parser.parse_args()
    
    tester = OSSParsingTester()
    
    if args.file:
        # 测试单个文件
        await tester.test_single_file(args.file)
    elif args.batch:
        # 批量测试
        await tester.test_batch_files(tester.test_files)
    elif args.type:
        # 按类型测试
        type_files = [f for f in tester.test_files if f.lower().endswith(args.type.lower())]
        if type_files:
            await tester.test_batch_files(type_files)
        else:
            print(f"未找到 {args.type} 类型的文件")
    elif args.performance:
        # 性能测试
        await tester.test_performance()
    elif args.all:
        # 运行所有测试
        await tester.run_all_tests()
    else:
        # 默认运行简单测试
        print("🧪 OSS资源解析简单测试")
        print("使用 --help 查看所有选项")
        print(f"\n📂 可用的测试文件 ({len(tester.test_files)} 个):")
        for i, file_name in enumerate(tester.test_files, 1):
            print(f"   {i:2d}. {file_name}")
        
        # 测试第一个文件
        if tester.test_files:
            await tester.test_single_file(tester.test_files[0])


if __name__ == "__main__":
    asyncio.run(main()) 