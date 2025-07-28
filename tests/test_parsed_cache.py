#!/usr/bin/env python3
"""
解析结果缓存功能测试脚本
验证解析器缓存机制是否正常工作
"""

import time
import os
import sys
from pathlib import Path

# 添加src路径到系统路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from file_reader.parsers import TextParser, PDFParser, OfficeParser
from file_reader.parsed_cache import get_parsed_cache


def test_text_parser_cache():
    """测试文本解析器的缓存功能"""
    print("🧪 测试文本解析器缓存功能...")
    
    parser = TextParser()
    test_content = "这是一个测试文档的内容。\n它包含多行文本。\n用于验证缓存功能。".encode('utf-8')
    
    # 第一次解析（缓存未命中）
    print("📝 第一次解析（缓存未命中）...")
    start_time = time.time()
    result1 = parser.parse(test_content, ".txt")
    time1 = time.time() - start_time
    
    if result1.success:
        print(f"✅ 第一次解析成功，耗时: {time1:.4f}秒")
        print(f"   内容长度: {len(result1.content)}")
    else:
        print(f"❌ 第一次解析失败: {result1.error}")
        assert False, f"第一次解析失败: {result1.error}"
    
    # 第二次解析（缓存命中）
    print("📝 第二次解析（缓存命中）...")
    start_time = time.time()
    result2 = parser.parse(test_content, ".txt")
    time2 = time.time() - start_time
    
    if result2.success:
        print(f"✅ 第二次解析成功，耗时: {time2:.4f}秒")
        print(f"   内容长度: {len(result2.content)}")
        print(f"   内容匹配: {'✅' if result1.content == result2.content else '❌'}")
        print(f"   速度提升: {time1/time2:.1f}倍")
    else:
        print(f"❌ 第二次解析失败: {result2.error}")
        assert False, f"第二次解析失败: {result2.error}"


def test_cache_key_generation():
    """测试缓存键生成逻辑"""
    print("\n🔑 测试缓存键生成逻辑...")
    
    cache = get_parsed_cache()
    
    content1 = "相同的内容".encode('utf-8')
    content2 = "相同的内容".encode('utf-8')
    content3 = "不同的内容".encode('utf-8')
    
    # 相同内容应该生成相同的缓存键
    key1 = cache.get_cache_key(content1, "text", "1.0")
    key2 = cache.get_cache_key(content2, "text", "1.0")
    key3 = cache.get_cache_key(content3, "text", "1.0")
    
    print(f"缓存键1: {key1}")
    print(f"缓存键2: {key2}")
    print(f"缓存键3: {key3}")
    print(f"键1和键2相同: {'✅' if key1 == key2 else '❌'}")
    print(f"键1和键3不同: {'✅' if key1 != key3 else '❌'}")
    
    # 不同版本应该生成不同的缓存键
    key4 = cache.get_cache_key(content1, "text", "1.1")
    print(f"缓存键4（不同版本）: {key4}")
    print(f"键1和键4不同: {'✅' if key1 != key4 else '❌'}")
    
    # 使用断言而不是return
    assert key1 == key2, "相同内容应该生成相同的缓存键"
    assert key1 != key3, "不同内容应该生成不同的缓存键"
    assert key1 != key4, "不同版本应该生成不同的缓存键"


def test_cache_with_config():
    """测试带配置参数的缓存功能"""
    print("\n⚙️ 测试带配置参数的缓存功能...")
    
    cache = get_parsed_cache()
    
    content = "测试内容".encode('utf-8')
    config1 = {"temperature": 0.5, "param": "value1"}
    config2 = {"temperature": 0.7, "param": "value1"}
    config3 = {"temperature": 0.5, "param": "value1"}  # 与config1相同
    
    key1 = cache.get_cache_key(content, "image", "1.0", config1)
    key2 = cache.get_cache_key(content, "image", "1.0", config2)
    key3 = cache.get_cache_key(content, "image", "1.0", config3)
    
    print(f"配置1缓存键: {key1}")
    print(f"配置2缓存键: {key2}")
    print(f"配置3缓存键: {key3}")
    print(f"键1和键2不同: {'✅' if key1 != key2 else '❌'}")
    print(f"键1和键3相同: {'✅' if key1 == key3 else '❌'}")
    
    # 使用断言而不是return
    assert key1 != key2, "不同配置应该生成不同的缓存键"
    assert key1 == key3, "相同配置应该生成相同的缓存键"


def test_cache_stats():
    """测试缓存统计功能"""
    print("\n📊 测试缓存统计功能...")
    
    cache = get_parsed_cache()
    stats = cache.get_cache_stats()
    
    print("缓存统计信息:")
    print(f"  总缓存项数: {stats.get('total_items', 0)}")
    print(f"  总内容大小: {stats.get('total_content_size', 0)} 字节")
    print(f"  缓存命中次数: {stats.get('cache_hits', 0)}")
    print(f"  缓存未命中次数: {stats.get('cache_misses', 0)}")
    print(f"  缓存写入次数: {stats.get('cache_writes', 0)}")
    print(f"  缓存错误次数: {stats.get('cache_errors', 0)}")
    
    total_requests = stats.get('cache_hits', 0) + stats.get('cache_misses', 0)
    if total_requests > 0:
        hit_rate = stats.get('cache_hits', 0) / total_requests
        print(f"  缓存命中率: {hit_rate:.2%}")
    
    # 验证统计数据
    assert isinstance(stats, dict), "缓存统计应该返回字典"
    assert 'cache_hits' in stats, "统计应该包含缓存命中数"
    assert 'cache_misses' in stats, "统计应该包含缓存未命中数"


def main():
    """主测试函数"""
    print("🚀 开始解析结果缓存功能测试")
    print("=" * 50)
    
    # 确保日志级别设置
    os.environ.setdefault("LOG_LEVEL", "INFO")
    
    tests = [
        ("文本解析器缓存", test_text_parser_cache),
        ("缓存键生成", test_cache_key_generation),
        ("配置参数缓存", test_cache_with_config),
        ("缓存统计", test_cache_stats),
    ]
    
    success_count = 0
    total_count = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔄 运行测试: {test_name}")
            test_func()  # 不检查返回值，依赖断言
            print(f"✅ {test_name} 测试通过")
            success_count += 1
        except Exception as e:
            print(f"❌ {test_name} 测试出现异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print(f"测试完成: {success_count}/{total_count} 通过")
    
    if success_count == total_count:
        print("🎉 所有测试都通过！解析结果缓存功能正常工作")
        return True
    else:
        print("⚠️  部分测试失败，请检查上述错误信息")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 