#!/usr/bin/env python3
"""
MCP-Local-Reader 缓存工具
用于查看本地文件缓存统计信息、管理缓存和分析缓存性能
"""

import os
import shutil
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

from src.file_reader.storage import LocalFileStorageClient
from src.file_reader.parsed_cache import get_parsed_cache
from src.file_reader.utils import get_logger

logger = get_logger("cache_utils")


def show_clear_warning():
    """显示清理警告信息"""
    print("⚠️  清理缓存警告")
    print("=" * 50)
    print("清理缓存将删除以下内容:")
    print("  📁  本地缓存目录中的所有文件")
    print("  💾  本地文件缓存")
    print("  📄  解析结果缓存和图像OCR缓存")
    print("  • 清理后的首次访问可能较慢")
    print()
    print("缓存清理的好处:")
    print("  🔄  释放磁盘空间")
    print("  🐛  解决缓存损坏问题")
    print("  🔧  测试和调试")
    print("  ⚡  强制重新处理最新内容")
    print()


def confirm_clear_action() -> bool:
    """确认清理操作"""
    show_clear_warning()
    
    print("\n🔐 安全确认")
    print("如果您确定要清理缓存，请输入: CLEAR CACHE CONFIRM")
    print("任何其他输入都将取消操作")
    
    user_input = input("\n请输入确认文本: ").strip()
    
    if user_input == "CLEAR CACHE CONFIRM":
        print("✅ 确认输入正确，开始清理缓存...")
        return True
    else:
        print("❌ 确认文本不匹配，取消清理操作")
        return False


def clear_local_storage_cache():
    """清理本地文件存储客户端的缓存"""
    try:
        # 使用默认配置创建本地存储客户端
        local_client = LocalFileStorageClient()
        
        # 显示清理前的缓存统计信息
        stats = local_client.get_stats()
        print(f"清理前的本地文件缓存统计:")
        print(f"  缓存项数: {stats.get('cache_size', 0)}")
        print(f"  本地缓存条目: {stats.get('local_cache_entries', 0)}")
        print(f"  缓存命中率: {stats.get('cache_hit_rate', 0):.2%}")
        print(f"  总缓存大小: {format_size(stats.get('total_cached_bytes', 0))}")
        print(f"  读取次数: {stats.get('reads', 0)}")
        print(f"  缓存命中: {stats.get('cache_hits', 0)}")
        print(f"  缓存未命中: {stats.get('cache_misses', 0)}")
        
        local_client.clear_cache()
        logger.info("本地文件存储客户端缓存已清理")
        return True
    except Exception as e:
        logger.error(f"清理本地文件存储缓存失败: {e}")
        return False




def clear_parsed_content_cache():
    """清理解析结果缓存"""
    try:
        parsed_cache = get_parsed_cache()
        
        # 显示清理前的缓存统计信息
        stats = parsed_cache.get_cache_stats()
        print(f"清理前的解析结果缓存统计:")
        print(f"  缓存项数: {stats.get('total_items', 0)}")
        print(f"  缓存命中率: {stats.get('cache_hit_rate', 0):.2%}")
        print(f"  总内容大小: {format_size(stats.get('total_content_size', 0))}")
        print(f"  缓存命中: {stats.get('cache_hits', 0)}")
        print(f"  缓存未命中: {stats.get('cache_misses', 0)}")
        print(f"  缓存写入: {stats.get('cache_writes', 0)}")
        print(f"  缓存错误: {stats.get('cache_errors', 0)}")
        print(f"  有效期: {stats.get('expire_days', 30)}天")
        
        parsed_cache.clear_cache()
        logger.info("解析结果缓存已清理")
        return True
    except Exception as e:
        logger.error(f"清理解析结果缓存失败: {e}")
        return False


def clear_directory_cache(cache_dir: str):
    """清理指定目录的缓存"""
    try:
        cache_path = Path(cache_dir)
        if cache_path.exists():
            size_before = get_cache_size(cache_dir)
            shutil.rmtree(cache_path)
            logger.info(f"目录缓存已清理: {cache_dir} (释放 {format_size(size_before)})")
            return True
        else:
            logger.info(f"缓存目录不存在: {cache_dir}")
            return True
    except Exception as e:
        logger.error(f"清理目录缓存失败 {cache_dir}: {e}")
        return False


def get_cache_size(cache_dir: str) -> int:
    """获取缓存目录大小（字节）"""
    try:
        cache_path = Path(cache_dir)
        if not cache_path.exists():
            return 0
        
        total_size = 0
        for file_path in cache_path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size
    except Exception:
        return 0


def get_cache_file_count(cache_dir: str) -> int:
    """获取缓存目录文件数量"""
    try:
        cache_path = Path(cache_dir)
        if not cache_path.exists():
            return 0
        
        file_count = 0
        for file_path in cache_path.rglob('*'):
            if file_path.is_file():
                file_count += 1
        
        return file_count
    except Exception:
        return 0


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def show_cache_stats():
    """显示缓存统计信息"""
    print("📊 MCP-Local-Reader 缓存统计信息")
    print("=" * 50)
    
    # 显示本地文件存储客户端统计
    print("\n💻 本地文件存储客户端缓存:")
    try:
        local_client = LocalFileStorageClient()
        local_stats = local_client.get_stats()
        
        local_key_stats = [
            ('总读取次数', 'reads'),
            ('缓存命中次数', 'cache_hits'),
            ('缓存未命中次数', 'cache_misses'),
            ('缓存命中率', 'cache_hit_rate'),
            ('总读取大小', 'total_size'),
            ('错误次数', 'errors'),
            ('缓存项数', 'cache_size'),
            ('本地缓存条目', 'local_cache_entries'),
            ('总缓存大小', 'total_cached_bytes'),
        ]
        
        for label, key in local_key_stats:
            if key in local_stats:
                value = local_stats[key]
                if key in ['cache_hit_rate']:
                    print(f"  {label}: {value:.2%}")
                elif key in ['total_size', 'total_cached_bytes']:
                    print(f"  {label}: {format_size(value)}")
                else:
                    print(f"  {label}: {value}")
        
        if 'cache_directory' in local_stats and local_stats['cache_directory']:
            print(f"  缓存目录: {local_stats['cache_directory']}")
        if 'cache_size_limit' in local_stats:
            print(f"  缓存大小限制: {format_size(local_stats['cache_size_limit'])}")
        if 'allowed_directories' in local_stats:
            print(f"  允许的目录数: {len(local_stats['allowed_directories'])}")
        if 'allow_absolute_paths' in local_stats:
            print(f"  允许绝对路径: {'是' if local_stats['allow_absolute_paths'] else '否'}")
        
    except Exception as e:
        logger.error(f"获取本地文件存储统计失败: {e}")
        print("  ❌ 无法获取本地文件缓存统计信息")
    
    
    # 显示解析结果缓存统计
    print("\n📄 解析结果缓存:")
    try:
        parsed_cache = get_parsed_cache()
        parsed_stats = parsed_cache.get_cache_stats()
        
        parsed_key_stats = [
            ('缓存命中次数', 'cache_hits'),
            ('缓存未命中次数', 'cache_misses'),
            ('缓存写入次数', 'cache_writes'),
            ('缓存错误次数', 'cache_errors'),
            ('缓存命中率', 'cache_hit_rate'),
            ('总缓存项数', 'total_items'),
            ('总内容大小', 'total_content_size'),
        ]
        
        for label, key in parsed_key_stats:
            if key in parsed_stats:
                value = parsed_stats[key]
                if key in ['cache_hit_rate']:
                    print(f"  {label}: {value:.2%}")
                elif key in ['total_content_size']:
                    print(f"  {label}: {format_size(value)}")
                else:
                    print(f"  {label}: {value}")
        
        if 'cache_directory' in parsed_stats and parsed_stats['cache_directory']:
            print(f"  缓存目录: {parsed_stats['cache_directory']}")
        if 'cache_size_limit' in parsed_stats:
            print(f"  缓存大小限制: {format_size(parsed_stats['cache_size_limit'])}")
        if 'expire_days' in parsed_stats:
            print(f"  缓存有效期: {parsed_stats['expire_days']}天")
        
        # 显示解析器统计
        if parsed_stats.get('parser_stats'):
            print(f"  解析器统计:")
            for parser, stats in parsed_stats['parser_stats'].items():
                print(f"    {parser}: {stats['count']}项, {format_size(stats['total_size'])}")
        
        # 显示文档类型统计
        if parsed_stats.get('doc_type_stats'):
            print(f"  文档类型统计:")
            for doc_type, stats in parsed_stats['doc_type_stats'].items():
                print(f"    {doc_type}: {stats['count']}项, {format_size(stats['total_size'])}")
        
    except Exception as e:
        logger.error(f"获取解析结果缓存统计失败: {e}")
        print("  ❌ 无法获取解析结果缓存统计信息")
    
    # 显示目录缓存大小
    cache_directories = [
        "cache/parsed_content",      # 解析结果缓存
        "cache/document_images",     # 图像缓存
        "cache/archive_files",       # 压缩文件缓存
        "cache",                     # 总缓存目录
        "__pycache__",               # Python缓存
        "src/file_reader/__pycache__",
        "src/file_reader/parsers/__pycache__",
    ]
    
    print(f"\n📁 缓存目录详情:")
    total_size = 0
    total_files = 0
    
    for cache_dir in cache_directories:
        size = get_cache_size(cache_dir)
        file_count = get_cache_file_count(cache_dir)
        total_size += size
        total_files += file_count
        
        if size > 0 or file_count > 0:
            print(f"  {cache_dir}:")
            print(f"    大小: {format_size(size)}")
            print(f"    文件数: {file_count}")
    
    print(f"\n📦 总缓存统计:")
    print(f"  总大小: {format_size(total_size)}")
    print(f"  总文件数: {total_files}")


def analyze_cache_performance():
    """分析缓存性能"""
    print("\n🔍 缓存性能分析")
    print("=" * 50)
    
    try:
        # 分析本地文件缓存性能
        local_client = LocalFileStorageClient()
        local_stats = local_client.get_stats()
        
        print("\n💻 本地文件缓存性能:")
        local_total_requests = local_stats.get('cache_hits', 0) + local_stats.get('cache_misses', 0)
        if local_total_requests > 0:
            local_hit_rate = local_stats.get('cache_hit_rate', 0)
            print(f"  缓存效率: {'优秀' if local_hit_rate > 0.8 else '良好' if local_hit_rate > 0.6 else '需要优化'}")
            print(f"  命中率: {local_hit_rate:.2%}")
            print(f"  总请求: {local_total_requests}")
            
            if local_hit_rate < 0.6:
                print("  💡 优化建议:")
                print("    - 文件可能频繁变更，这是正常现象")
                print("    - 考虑调整缓存过期时间")
                print("    - 检查文件修改模式")
        else:
            print("  📊 暂无足够数据进行分析")
            
    except Exception as e:
        logger.error(f"分析缓存性能失败: {e}")


def get_cache_info(file_path: Optional[str] = None):
    """获取特定文件的缓存信息"""
    print("\n🔎 文件缓存信息查询")
    print("=" * 50)
    
    if file_path:
        print(f"\n💻 本地文件: {file_path}")
        try:
            local_client = LocalFileStorageClient()
            cache_info = local_client.get_cache_info(file_path)
            
            if cache_info:
                print(f"  文件路径: {cache_info['file_path']}")
                print(f"  缓存键: {cache_info['cache_key']}")
                print(f"  是否缓存: {'是' if cache_info['cached'] else '否'}")
                print(f"  文件大小: {format_size(cache_info['file_size'])}")
                print(f"  修改时间: {cache_info['file_mtime']}")
                if cache_info['cached']:
                    print(f"  缓存大小: {format_size(cache_info['cache_size'])}")
            else:
                print("  ❌ 无法获取文件缓存信息（文件可能不存在或无权访问）")
                
        except Exception as e:
            logger.error(f"获取本地文件缓存信息失败: {e}")
            print(f"  ❌ 获取缓存信息失败: {e}")
    else:
        print("请指定要查询的本地文件路径")


def export_cache_stats(output_file: str):
    """导出缓存统计信息到JSON文件"""
    try:
        stats_data = {
            "timestamp": str(Path().cwd()),
            "local_cache": {},
            "parsed_cache": {},
            "directory_stats": {}
        }
        
        # 收集本地文件缓存统计
        try:
            local_client = LocalFileStorageClient()
            stats_data["local_cache"] = local_client.get_stats()
        except Exception as e:
            stats_data["local_cache"]["error"] = str(e)
        
        # 收集解析结果缓存统计
        try:
            parsed_cache = get_parsed_cache()
            stats_data["parsed_cache"] = parsed_cache.get_cache_stats()
        except Exception as e:
            stats_data["parsed_cache"]["error"] = str(e)
        
        # 收集目录缓存统计
        cache_directories = [
            "cache/parsed_content",    # 解析结果缓存
            "cache/document_images",   # 图像缓存
            "cache/archive_files",     # 压缩文件缓存
            "cache",                   # 总缓存目录
            "__pycache__"              # Python缓存
        ]
        
        for cache_dir in cache_directories:
            stats_data["directory_stats"][cache_dir] = {
                "size_bytes": get_cache_size(cache_dir),
                "file_count": get_cache_file_count(cache_dir),
                "size_formatted": format_size(get_cache_size(cache_dir))
            }
        
        # 写入JSON文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ 缓存统计信息已导出到: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"导出缓存统计失败: {e}")
        print(f"❌ 导出失败: {e}")
        return False


def perform_clear_operation(args):
    """执行清理操作"""
    if not confirm_clear_action():
        return
    
    success_count = 0
    total_count = 0
    
    if args.all or args.local:
        # 清理本地文件缓存
        print("\n🗑️  清理本地文件存储缓存...")
        total_count += 1
        if clear_local_storage_cache():
            success_count += 1
    
    
    if args.all or args.parsed:
        # 清理解析结果缓存
        print("\n🗑️  清理解析结果缓存...")
        total_count += 1
        if clear_parsed_content_cache():
            success_count += 1
    
    if args.all:
        # 清理所有缓存目录
        print("\n🗑️  清理所有缓存目录...")
        cache_directories = [
            "cache",
            "__pycache__",
            "src/file_reader/__pycache__",
            "src/file_reader/parsers/__pycache__"
        ]
        for cache_dir in cache_directories:
            total_count += 1
            if clear_directory_cache(cache_dir):
                success_count += 1
    
    if args.dir:
        # 清理指定目录
        print(f"\n🗑️  清理指定目录: {args.dir}")
        total_count += 1
        if clear_directory_cache(args.dir):
            success_count += 1
    
    print(f"\n✅ 清理完成: {success_count}/{total_count} 成功")
    
    # 清理后显示统计信息
    if success_count > 0:
        print("\n📊 清理后的缓存状态:")
        show_cache_stats()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP-Local-Reader 缓存管理工具")
    parser.add_argument("--stats", action="store_true", help="显示缓存统计信息")
    parser.add_argument("--analyze", action="store_true", help="分析缓存性能")
    parser.add_argument("--clear", action="store_true", help="进入缓存清理模式（需要确认）")
    parser.add_argument("--info", action="store_true", help="查询特定文件的缓存信息")
    parser.add_argument("--export", type=str, help="导出缓存统计信息到JSON文件")
    
    # 清理选项（仅在--clear模式下生效）
    parser.add_argument("--all", action="store_true", help="清理所有缓存（需要--clear）")
    parser.add_argument("--local", action="store_true", help="清理本地文件缓存（需要--clear）")
    parser.add_argument("--parsed", action="store_true", help="清理解析结果缓存（需要--clear）")
    parser.add_argument("--dir", type=str, help="清理指定目录（需要--clear）")
    
    # 查询选项（仅在--info模式下生效）
    parser.add_argument("--file", type=str, help="查询本地文件的缓存信息（需要--info）")
    
    args = parser.parse_args()
    
    print("🛠️  MCP-Local-Reader 缓存管理工具")
    print("=" * 50)
    
    # 显示统计信息
    if args.stats:
        show_cache_stats()
        return
    
    # 分析缓存性能
    if args.analyze:
        show_cache_stats()
        analyze_cache_performance()
        return
    
    # 查询文件缓存信息
    if args.info:
        if not args.file:
            print("❌ 错误: 使用 --info 参数时，需要指定 --file")
            print("\n使用示例:")
            print("  python cache_utils.py --info --file /path/to/file.txt")
            return
        
        get_cache_info(file_path=args.file)
        return
    
    # 导出缓存统计
    if args.export:
        export_cache_stats(args.export)
        return
    
    # 进入清理模式
    if args.clear:
        # 检查是否有具体的清理选项
        if not any([args.all, args.local, args.parsed, args.dir]):
            print("❌ 错误: 使用 --clear 参数时，需要指定具体的清理选项")
            print("\n可用的清理选项:")
            print("  --all      清理所有缓存")
            print("  --local    清理本地文件缓存")
            print("  --parsed   清理解析结果缓存")
            print("  --dir DIR  清理指定目录")
            return
        
        perform_clear_operation(args)
        return
    
    # 默认显示帮助和统计信息
    if not any([args.stats, args.analyze, args.clear, args.info, args.export]):
        show_cache_stats()
        print("\n💡 使用说明:")
        print("  python cache_utils.py --stats                      # 查看缓存统计")
        print("  python cache_utils.py --analyze                    # 分析缓存性能")
        print("  python cache_utils.py --info --file /path/to/file  # 查询文件缓存信息")
        print("  python cache_utils.py --export stats.json         # 导出统计信息")
        print("  python cache_utils.py --clear --all               # 清理所有缓存")
        print("  python cache_utils.py --clear --local             # 清理本地缓存")


if __name__ == "__main__":
    main() 