#!/usr/bin/env python3
"""
MCP文件读取器客户端示例
演示如何使用MCP文件读取器服务，支持HTTP下载、本地文件读取和智能上传
"""

import asyncio
import json
import argparse
from typing import List, Tuple, Dict
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


class MCPFileReaderClient:
    """MCP文件读取器客户端"""
    
    def __init__(self, base_url: str = "http://localhost:3001/mcp"):
        """
        初始化客户端
        
        Args:
            base_url: MCP服务器基础URL
        """
        self.base_url = base_url.rstrip('/')
        self.transport = StreamableHttpTransport(self.base_url)
        self.client = Client(self.transport)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
    

    
    async def read_local_files(
        self, 
        file_paths: List[str], 
        max_size: int = None  # MB单位，为空时使用服务器端环境变量FILE_READER_MAX_FILE_SIZE_MB的默认值
    ) -> dict:
        """
        从本地文件系统读取文件内容（仅支持绝对路径）
        
        Args:
            file_paths: 本地文件绝对路径列表，必须使用完整的绝对路径
            max_size: 最大文件大小（MB），为空时使用服务器端环境变量配置
            
        Returns:
            读取结果字典
        """
        kwargs = {
            "file_paths": file_paths
        }
        if max_size is not None:
            kwargs["max_size"] = max_size
        
        result = await self.client.call_tool("read_local_files", kwargs)
        
        # 解析返回的内容
        if result and len(result) > 0 and hasattr(result[0], 'text'):
            return json.loads(result[0].text)
        
        return {"contents": [], "failed": []}
    
    async def upload_and_read_files(
        self,
        file_paths: List[str],
        max_size: int = None,
        cleanup_after: bool = True
    ) -> dict:
        """
        上传文件并读取内容（适用于Docker环境）
        
        Args:
            file_paths: 本地文件路径列表
            max_size: 最大文件大小（MB），为空时使用服务器端环境变量配置
            cleanup_after: 处理完成后是否清理临时文件
            
        Returns:
            读取结果字典
        """
        import base64
        
        # 准备结果容器
        all_contents = []
        all_failed = []
        
        for file_path in file_paths:
            try:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    print(f"⚠️  文件不存在: {file_path}")
                    all_failed.append({
                        "resource_id": file_path_obj.name,
                        "type": "file_not_found",
                        "error_message": f"文件不存在: {file_path}"
                    })
                    continue
                
                # 读取文件并编码
                with open(file_path, 'rb') as f:
                    content = base64.b64encode(f.read()).decode()
                    print(f"📤 已准备上传文件: {file_path_obj.name}")
                
                # 调用单文件上传API
                kwargs = {
                    "filename": file_path_obj.name,
                    "content": content,
                    "cleanup_after": cleanup_after
                }
                if max_size is not None:
                    kwargs["max_size"] = max_size
                
                result = await self.client.call_tool("upload_and_read_file", kwargs)
                
                # 解析单个文件的结果
                if result and len(result) > 0 and hasattr(result[0], 'text'):
                    single_result = json.loads(result[0].text)
                    
                    # 合并结果
                    all_contents.extend(single_result.get('contents', []))
                    all_failed.extend(single_result.get('failed', []))
                else:
                    all_failed.append({
                        "resource_id": file_path_obj.name,
                        "type": "api_error",
                        "error_message": "API调用返回空结果"
                    })
                    
            except Exception as e:
                print(f"❌ 处理文件失败: {file_path}, 错误: {e}")
                all_failed.append({
                    "resource_id": Path(file_path).name,
                    "type": "processing_error", 
                    "error_message": str(e)
                })
                continue
        
        return {
            "contents": all_contents,
            "failed": all_failed
        }
    
    async def read_files_smart(
        self, 
        file_paths: List[str],
        max_size: int = None,
        **kwargs
    ) -> dict:
        """
        智能文件读取 - 自动选择最佳方法
        
        先尝试本地文件读取，如果失败则自动切换到文件上传模式
        
        Args:
            file_paths: 本地文件绝对路径列表
            max_size: 最大文件大小（MB）
            **kwargs: 其他参数
            
        Returns:
            读取结果字典
        """
        print(f"🔍 智能文件读取模式 - 处理 {len(file_paths)} 个文件")
        
        try:
            # 先尝试本地文件读取
            print("🔧 尝试本地文件读取模式...")
            result = await self.read_local_files(
                file_paths, 
                max_size=max_size
            )
            print("✅ 本地文件读取成功")
            return result
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # 检查是否是工具不可用的错误
            if any(keyword in error_msg for keyword in [
                "read_local_files", 
                "tool not found", 
                "unknown tool",
                "docker",
                "container"
            ]):
                print("🐳 检测到Docker环境或本地读取不可用，切换到文件上传模式...")
                
                try:
                    result = await self.upload_and_read_files(
                        file_paths,
                        max_size=max_size,
                        cleanup_after=kwargs.get('cleanup_after', True)
                    )
                    print("✅ 文件上传读取成功")
                    return result
                    
                except Exception as upload_error:
                    print(f"❌ 文件上传读取也失败: {upload_error}")
                    raise upload_error
            else:
                # 其他类型的错误，直接抛出
                print(f"❌ 本地文件读取失败: {e}")
                raise e
    
    async def get_server_info(self) -> dict:
        """
        获取服务器信息
        """
        result = await self.client.call_tool("get_server_info", {})
        return json.loads(result[0].text)

    async def get_reader_stats(self) -> dict:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        result = await self.client.call_tool("get_reader_stats", {})
        
        if result and len(result) > 0 and hasattr(result[0], 'text'):
            return json.loads(result[0].text)
        
        return {}
    
    async def close(self):
        """关闭客户端连接"""
        if hasattr(self.client, 'close'):
            await self.client.close()

    async def read_files(
        self, 
        urls: List[Dict[str, str]], 
        default_referer: str = None,
        expires: int = None,
        max_size: int = None,  # MB单位，为空时使用服务器端环境变量FILE_READER_MAX_FILE_SIZE_MB的默认值
        use_proxy: bool = False,
        max_retries: int = 3,
        max_workers: int = 3
    ) -> dict:
        """
        通过HTTP下载链接读取文件内容
        
        Args:
            urls: 文件下载链接数组，格式: [{"url": "url1", "referer": "ref1"}, {"url": "url2"}]
            default_referer: 默认Referer，应用于所有未指定专属Referer的链接
            expires: 文件过期时长（秒），用于下载服务的缓存管理
            max_size: 最大文件大小（MB），为空时使用服务器端环境变量配置
            use_proxy: 是否使用代理下载文件
            max_retries: 最大重试次数
            max_workers: 最大并发工作线程数
            
        Returns:
            读取结果字典
        """
        kwargs = {
            "urls": urls,
            "use_proxy": use_proxy,
            "max_retries": max_retries,
            "max_workers": max_workers
        }
        if default_referer:
            kwargs["default_referer"] = default_referer
        if expires is not None:
            kwargs["expires"] = expires
        if max_size is not None:
            kwargs["max_size"] = max_size
            
        result = await self.client.call_tool("read_files", kwargs)
        
        # 解析返回的内容
        if result and len(result) > 0 and hasattr(result[0], 'text'):
            return json.loads(result[0].text)
        
        return {"contents": [], "failed": []}


def print_file_results(result: dict, file_type: str = "文件", detailed: bool = False):
    """
    打印文件读取结果
    
    Args:
        result: 读取结果字典
        file_type: 文件类型描述
        detailed: 是否显示详细内容
    """
    success_count = len(result.get('contents', []))
    failed_count = len(result.get('failed', []))
    total_count = success_count + failed_count
    
    print(f"   📊 读取结果统计:")
    print(f"   总计{file_type}数: {total_count}")
    print(f"   成功{file_type}数: {success_count}")
    print(f"   失败{file_type}数: {failed_count}")
    if total_count > 0:
        success_rate = (success_count / total_count) * 100
        print(f"   成功率: {success_rate:.1f}%")
    
    # 显示成功读取的内容
    for i, content in enumerate(result.get('contents', []), 1):
        resource_id = content.get('resource_id', '')
        text_content = content.get('content', '')
        file_extension = Path(resource_id).suffix.lower()
        print(f"\n   ✅ [{i}] {resource_id} ({file_extension})")
        print(f"      内容长度: {len(text_content):,} 字符")
        
        if detailed and text_content:
            # 详细模式显示更多内容
            if len(text_content) > 500:
                preview = text_content[:500] + "..."
            else:
                preview = text_content
            print(f"      内容预览: {preview}")
        elif text_content:
            # 简要模式只显示开头
            if len(text_content) > 100:
                preview = text_content[:100] + "..."
            else:
                preview = text_content
            print(f"      内容预览: {preview}")
    
    # 显示失败的文件
    for i, failed in enumerate(result.get('failed', []), 1):
        resource_id = failed.get('resource_id', '')
        failure_type = failed.get('type', '')
        error_message = failed.get('error_message', '')
        file_extension = Path(resource_id).suffix.lower()
        print(f"\n   ❌ [{i}] {resource_id} ({file_extension})")
        print(f"      失败类型: {failure_type}")
        print(f"      错误信息: {error_message}")


def get_all_test_files() -> List[Tuple[str, str]]:
    """
    获取 tests/files 目录下的所有测试文件
    
    Returns:
        包含文件路径和描述的元组列表
    """
    test_files_dir = Path("tests/files")
    test_files = []
    
    if not test_files_dir.exists():
        return test_files
    
    # 文件扩展名到描述的映射
    extension_descriptions = {
        '.pdf': 'PDF文档',
        '.doc': 'Word文档(旧格式)',
        '.docx': 'Word文档',
        '.xls': 'Excel表格(旧格式)',
        '.xlsx': 'Excel表格',
        '.ppt': 'PowerPoint演示(旧格式)',
        '.pptx': 'PowerPoint演示',
        '.odt': 'OpenDocument文本',
        '.ods': 'OpenDocument表格',
        '.odp': 'OpenDocument演示',
        '.txt': '纯文本文件',
        '.rtf': 'RTF文档',
        '.md': 'Markdown文档',
        '.markdown': 'Markdown文档',
        '.jpg': 'JPEG图片',
        '.jpeg': 'JPEG图片',
        '.png': 'PNG图片',
        '.gif': 'GIF图片',
        '.bmp': 'BMP图片',
        '.webp': 'WebP图片',
        '.tiff': 'TIFF图片',
    }
    
    # 遍历目录中的所有文件
    for file_path in sorted(test_files_dir.iterdir()):
        if file_path.is_file():
            extension = file_path.suffix.lower()
            description = extension_descriptions.get(extension, f'{extension}文件')
            # 使用绝对路径
            absolute_path = str(file_path.resolve())
            test_files.append((absolute_path, description))
    
    return test_files


async def test_all_files(client: MCPFileReaderClient, detailed: bool = False):
    """全面测试 tests/files 目录下的所有文件"""
    print("\n🧪 全面文件测试模式")
    print("=" * 50)
    
    test_files = get_all_test_files()
    
    if not test_files:
        print("❌ 未找到 tests/files 目录或目录为空")
        print("   请确保存在 tests/files 目录并包含测试文件")
        return
    
    print(f"📂 发现 {len(test_files)} 个测试文件:")
    
    # 按文件类型分组显示
    file_types = {}
    for file_path, description in test_files:
        extension = Path(file_path).suffix.lower()
        if extension not in file_types:
            file_types[extension] = []
        file_types[extension].append((file_path, description))
    
    for extension, files in sorted(file_types.items()):
        print(f"   {extension}: {len(files)} 个文件")
        for file_path, description in files:
            print(f"     📄 {Path(file_path).name} - {description}")
    
    print(f"\n🚀 开始测试所有文件...")
    
    # 提取文件路径
    file_paths = [file_path for file_path, _ in test_files]
    
    # 批量处理：每次最多处理10个文件（服务器限制）
    batch_size = 10
    all_contents = []
    all_failed = []
    
    try:
        total_batches = (len(file_paths) + batch_size - 1) // batch_size
        print(f"   📦 将分 {total_batches} 批处理，每批最多 {batch_size} 个文件")
        
        for i in range(0, len(file_paths), batch_size):
            batch_files = file_paths[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            print(f"\n   🔄 处理第 {batch_num}/{total_batches} 批 ({len(batch_files)} 个文件)...")
            for j, file_path in enumerate(batch_files, 1):
                print(f"     [{j}] {Path(file_path).name}")
            
            # 处理当前批次
            batch_result = await client.read_local_files(
                batch_files, 
                max_size=50, # 本地读取文件大小限制为50MB
            )
            
            # 合并结果
            batch_contents = batch_result.get('contents', [])
            batch_failed = batch_result.get('failed', [])
            all_contents.extend(batch_contents)
            all_failed.extend(batch_failed)
            
            print(f"     ✅ 第 {batch_num} 批完成: 成功 {len(batch_contents)}, 失败 {len(batch_failed)}")
        
        # 合并所有批次的结果
        result = {
            'contents': all_contents,
            'failed': all_failed
        }
        
        print(f"\n📊 总体测试结果:")
        print_file_results(result, "测试文件", detailed=detailed)
        
        # 按文件类型统计结果
        print(f"\n📈 按文件类型统计:")
        success_by_type = {}
        failed_by_type = {}
        
        # 统计成功的文件
        for content in result.get('contents', []):
            resource_id = content.get('resource_id', '')
            extension = Path(resource_id).suffix.lower()
            success_by_type[extension] = success_by_type.get(extension, 0) + 1
        
        # 统计失败的文件
        for failed in result.get('failed', []):
            resource_id = failed.get('resource_id', '')
            extension = Path(resource_id).suffix.lower()
            failed_by_type[extension] = failed_by_type.get(extension, 0) + 1
        
        # 显示统计结果
        all_extensions = set(success_by_type.keys()) | set(failed_by_type.keys())
        for extension in sorted(all_extensions):
            success = success_by_type.get(extension, 0)
            failed = failed_by_type.get(extension, 0)
            total = success + failed
            success_rate = (success / total * 100) if total > 0 else 0
            print(f"   {extension}: {success}/{total} 成功 ({success_rate:.1f}%)")
        
    except Exception as e:
        print(f"❌ 文件测试失败: {e}")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="MCP文件读取器客户端示例",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s --local                     # 本地读取所有测试文件（仅原生环境）
  %(prog)s --local file1.txt file2.pdf # 本地读取指定文件（仅原生环境）
  %(prog)s --smart                     # 智能读取所有测试文件（推荐）
  %(prog)s --smart file1.txt file2.pdf # 智能读取指定文件（推荐）
  %(prog)s --http                      # HTTP下载读取示例文件
  %(prog)s --http url1 url2            # HTTP下载读取指定URL
  %(prog)s --port 3002 --smart         # 指定端口并智能读取
  
智能模式说明:
  --smart 模式会自动检测服务器环境：
  • 原生环境: 使用本地文件读取
  • Docker环境: 自动上传文件并读取
        """
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=3001,
        help='MCP服务器端口号 (默认: 3001)'
    )
    
    parser.add_argument(
        '--local',
        nargs='*',
        help='本地文件模式（可指定文件路径，不指定则读取所有测试文件）'
    )
    
    parser.add_argument(
        '--smart',
        nargs='*',
        help='智能文件读取模式（自动检测环境并选择最佳方法）'
    )
    
    parser.add_argument(
        '--http',
        nargs='*',
        help='HTTP下载模式（可指定URL列表，不指定则使用示例URL）'
    )
    
    args = parser.parse_args()
    
    # 验证参数：必须指定 --local、--http 或 --smart 中的一个
    specified_modes = sum([
        args.local is not None,
        args.http is not None, 
        args.smart is not None
    ])
    
    if specified_modes == 0:
        parser.error("必须指定 --local、--http 或 --smart 中的一个")
    
    if specified_modes > 1:
        parser.error("不能同时指定多个读取模式")
    
    return args


async def main():
    """主函数"""
    args = parse_arguments()
    
    # 构建服务器URL
    base_url = f"http://localhost:{args.port}/mcp"
    
    # 创建客户端并使用context manager
    async with MCPFileReaderClient(base_url) as client:
        try:
            print("🔍 MCP文件读取器客户端示例")
            print("=" * 50)
            print(f"🌐 服务器地址: {base_url}")
                        
            # 环境说明
            print("\n2.1. 环境说明...")
            print("   💡 使用建议:")
            print("     • 推荐使用 --smart 模式进行智能读取")
            print("     • 服务器会自动检测环境并选择最佳方法")
            print("     • 原生环境: 本地文件直接读取")
            print("     • Docker环境: 文件上传处理")
            
            # 根据参数执行操作
            if args.local is not None:
                # 本地文件模式
                if args.local:
                    # 指定了文件路径
                    print(f"\n3. 读取指定本地文件...")
                    print(f"   文件路径: {args.local}")
                    result = await client.read_local_files(args.local)
                    print_file_results(result, "本地文件", detailed=True)
                else:
                    # 读取所有测试文件
                    print(f"\n3. 读取所有本地测试文件...")
                    await test_all_files(client, detailed=True)
            
            elif args.smart is not None:
                # 智能文件读取模式
                if args.smart:
                    # 指定了文件路径
                    print(f"\n3. 智能读取指定文件...")
                    print(f"   文件路径: {args.smart}")
                    result = await client.read_files_smart(args.smart)
                    print_file_results(result, "智能读取", detailed=True)
                else:
                    # 智能读取测试文件（Docker环境下限制数量）
                    print(f"\n3. 智能读取测试文件...")
                    test_files = get_all_test_files()
                    if test_files:
                        # 为了避免Docker环境下文件上传过多导致超时，限制文件数量和大小
                        # 选择不同类型的代表性小文件进行测试
                        selected_files = []
                        file_types_seen = set()
                        
                        # 按文件大小排序，优先选择小文件
                        test_files_with_size = []
                        for file_path, description in test_files:
                            try:
                                file_size = Path(file_path).stat().st_size
                                test_files_with_size.append((file_path, description, file_size))
                            except OSError:
                                # 文件不存在或无法访问，跳过
                                continue
                        
                        # 按文件大小排序
                        test_files_with_size.sort(key=lambda x: x[2])
                        
                        # 优先选择不同类型的小文件（小于1MB），最多3个
                        max_file_size = 1024 * 1024  # 1MB
                        for file_path, description, file_size in test_files_with_size:
                            extension = Path(file_path).suffix.lower()
                            if (extension not in file_types_seen and 
                                len(selected_files) < 3 and 
                                file_size < max_file_size):
                                selected_files.append(file_path)
                                file_types_seen.add(extension)
                        
                        # 如果小文件类型不足3种，补充小文件到3个
                        if len(selected_files) < 3:
                            for file_path, description, file_size in test_files_with_size:
                                if (file_path not in selected_files and 
                                    len(selected_files) < 3 and 
                                    file_size < max_file_size):
                                    selected_files.append(file_path)
                        
                        if selected_files:
                            print(f"   📝 为避免Docker环境上传超时，选择 {len(selected_files)} 个小文件(<1MB):")
                            for i, file_path in enumerate(selected_files, 1):
                                extension = Path(file_path).suffix.lower()
                                file_size = Path(file_path).stat().st_size
                                size_str = f"{file_size/1024:.1f}KB" if file_size < 1024*1024 else f"{file_size/(1024*1024):.1f}MB"
                                print(f"     [{i}] {Path(file_path).name} ({extension}, {size_str})")
                            
                            print(f"   💡 如需测试大文件或所有文件，请单独指定文件路径")
                            
                            result = await client.read_files_smart(selected_files)
                            print_file_results(result, "智能读取", detailed=True)
                        else:
                            print("   ❌ 未找到合适的小文件进行测试")
                    else:
                        print("   ❌ 未找到测试文件")
            
            elif args.http is not None:
                # HTTP下载模式
                if args.http:
                    # 指定了URL
                    print(f"\n3. 读取指定HTTP文件...")
                    print(f"   下载链接: {args.http}")
                    
                    # 转换为新的格式
                    urls_with_referer = [{"url": url} for url in args.http]
                    
                    result = await client.read_files(urls_with_referer)
                    print_file_results(result, "HTTP文件", detailed=True)
                else:
                    # 使用示例URL进行演示
                    print(f"\n3. HTTP下载演示...")
                    
                    # 演示per-URL referer功能
                    urls_with_referer = [
                        {
                            "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                            "referer": "https://www.w3.org"
                        },
                        {
                            "url": "https://file-examples.com/storage/fe086c9c8dae5b8c62d4a0e/2017/10/file_example_JPG_100kB.jpg"
                        }  # 图片文件使用默认referer
                    ]
                    
                    print(f"   演示链接: {[item['url'] for item in urls_with_referer]}")
                    print(f"   💡 注意: 需要确保HTTP下载服务正常运行且能访问这些URL")
                    
                    try:
                        print(f"   🆕 使用per-URL referer功能:")
                        print(f"     • PDF文件专属referer: https://www.w3.org")
                        print(f"     • 图片文件使用默认referer")
                        
                        result = await client.read_files(
                            urls_with_referer,
                            default_referer="https://www.example.com",  # 默认referer
                            max_size=10,  # 10MB限制
                            use_proxy=False
                        )
                        print_file_results(result, "HTTP文件", detailed=True)
                    except Exception as e:
                        print(f"   ❌ HTTP下载演示失败: {e}")
                        print(f"   💡 请检查HTTP下载服务是否正常运行，或使用其他可访问的URL")
            
            print("\n✅ 示例完成")
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 