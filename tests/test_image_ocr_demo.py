#!/usr/bin/env python3
"""
图片OCR识别演示脚本
专门测试并展示图片文件的OCR识别效果
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from file_reader.parsers.image_parser import ImageParser


async def test_image_ocr():
    """测试图片OCR识别效果"""
    print("🖼️  图片OCR识别演示")
    print("=" * 60)
    
    # 图片文件目录
    files_dir = Path("tests/files")
    
    if not files_dir.exists():
        print("❌ 测试文件目录不存在: tests/files")
        return
    
    # 查找图片文件
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(files_dir.glob(f"*{ext}"))
    
    if not image_files:
        print("❌ 未找到图片文件")
        return
    
    image_files.sort(key=lambda x: x.name)
    print(f"📂 找到 {len(image_files)} 个图片文件:")
    for img_file in image_files:
        file_size = img_file.stat().st_size / 1024  # KB
        print(f"   - {img_file.name} ({file_size:.1f}KB)")
    
    print("\n" + "=" * 60)
    print("🔍 开始OCR识别...")
    print("-" * 60)
    
    # 创建解析器
    parser = ImageParser()
    
    # 逐个测试图片
    for i, image_file in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] 识别图片: {image_file.name}")
        print("-" * 40)
        
        try:
            # 读取图片文件
            with open(image_file, 'rb') as f:
                image_content = f.read()
            
            # 执行OCR识别
            result = await parser.parse_async(image_content, image_file.suffix.lower())
            
            if result.success:
                print("✅ OCR识别成功!")
                print(f"📄 文档类型: {result.doc_type}")
                print(f"📊 元数据: {result.metadata}")
                print(f"📝 文字内容长度: {len(result.content)} 字符")
                
                # 显示识别的文字内容
                if result.content:
                    print("\n🔤 识别的文字内容:")
                    print("-" * 30)
                    # 限制显示长度，避免输出过长
                    display_content = result.content[:500]
                    if len(result.content) > 500:
                        display_content += "\n... (内容过长，已截断)"
                    print(display_content)
                    print("-" * 30)
                else:
                    print("⚠️  未识别到文字内容")
            else:
                print("❌ OCR识别失败")
                print(f"💭 错误信息: {result.error}")
                
        except Exception as e:
            print(f"❌ 处理异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 OCR识别演示完成!")


async def main():
    """主函数"""
    # 检查环境配置
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  警告: 未检测到API密钥环境变量")
        print("请确保设置了 OPENAI_API_KEY 或 ANTHROPIC_API_KEY")
        print("OCR功能需要多模态LLM的支持\n")
    
    # 运行测试
    await test_image_ocr()
    
    print("\n💡 使用提示:")
    print("- 支持格式: PNG, JPG, JPEG, GIF, BMP, WEBP")
    print("- 确保图片文字清晰，避免模糊或过小的文字")
    print("- 建议图片尺寸不要过小（最小边长 > 10px）")
    print("- 中文和英文文字都能很好地识别")


if __name__ == "__main__":
    asyncio.run(main()) 