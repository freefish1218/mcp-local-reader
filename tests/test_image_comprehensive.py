#!/usr/bin/env python3
"""
图像解析器综合测试
测试各种图像格式、大小和内容情况
"""

import asyncio
import os
import sys
import base64
from pathlib import Path

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from file_reader.parsers.image_parser import ImageParser


async def create_test_images():
    """创建多种测试图像"""
    test_images = {}
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # 1. 包含中英文混合文字的图像
        def create_mixed_text_image():
            image = Image.new('RGB', (400, 200), 'white')
            draw = ImageDraw.Draw(image)
            
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            text = "Hello World!\n这是中文测试\nMixed Text 混合文字\n123456789"
            draw.multiline_text((10, 20), text, fill='black', font=font, spacing=5)
            return image
        
        # 2. 纯英文文字图像
        def create_english_text_image():
            image = Image.new('RGB', (300, 150), 'white')
            draw = ImageDraw.Draw(image)
            
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            text = "English Only\nNumbers: 123\nSpecial: @#$%"
            draw.multiline_text((10, 20), text, fill='black', font=font)
            return image
        
        # 3. 纯中文文字图像
        def create_chinese_text_image():
            image = Image.new('RGB', (300, 150), 'white')
            draw = ImageDraw.Draw(image)
            
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 18)
            except:
                font = ImageFont.load_default()
            
            text = "纯中文测试\n中华人民共和国\n北京时间"
            draw.multiline_text((10, 20), text, fill='black', font=font)
            return image
        
        # 4. 空白图像（无文字）
        def create_blank_image():
            image = Image.new('RGB', (200, 100), 'white')
            # 不添加任何文字
            return image
        
        # 5. 小字体图像
        def create_small_text_image():
            image = Image.new('RGB', (250, 100), 'white')
            draw = ImageDraw.Draw(image)
            
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 10)
            except:
                font = ImageFont.load_default()
            
            text = "Small text 小字体\nTiny words"
            draw.multiline_text((5, 10), text, fill='black', font=font)
            return image
        
        # 创建测试图像
        images = {
            'mixed_text.png': create_mixed_text_image(),
            'english_only.jpg': create_english_text_image(),
            'chinese_only.png': create_chinese_text_image(),
            'blank.png': create_blank_image(),
            'small_text.png': create_small_text_image()
        }
        
        # 保存图像并读取字节数据
        for filename, img in images.items():
            # 确定格式
            format_map = {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG'}
            ext = Path(filename).suffix.lower()
            img_format = format_map.get(ext, 'PNG')
            
            # 保存到临时文件
            img.save(filename, format=img_format)
            
            # 读取字节数据
            with open(filename, 'rb') as f:
                test_images[filename] = {
                    'content': f.read(),
                    'extension': ext,
                    'description': f"测试图像: {filename}"
                }
        
        print(f"成功创建 {len(test_images)} 个测试图像")
        return test_images
        
    except ImportError:
        print("警告: PIL/Pillow 未安装，无法创建测试图像")
        return {}


async def test_image_formats():
    """测试不同图像格式的支持"""
    print("\n=== 测试图像格式支持 ===")
    
    parser = ImageParser()
    
    # 测试支持的格式
    supported_formats = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
    
    for fmt in supported_formats:
        # 创建简单的测试内容
        test_content = b"fake_image_data"  # 模拟图像数据
        
        result = await parser.parse_async(test_content, fmt)
        print(f"格式 {fmt}: {'支持' if not result.error or 'unstructured' not in result.error.lower() else '不支持'}")


async def test_error_cases():
    """测试错误情况处理"""
    print("\n=== 测试错误情况处理 ===")
    
    parser = ImageParser()
    
    # 测试用例
    test_cases = [
        {
            'name': '不支持的格式',
            'content': b"test_data",
            'extension': '.txt',
            'expect_error': True
        },
        {
            'name': '空内容',
            'content': b"",
            'extension': '.png',
            'expect_error': True
        },
        {
            'name': '无扩展名',
            'content': b"test_data",
            'extension': None,
            'expect_error': True
        }
    ]
    
    for case in test_cases:
        print(f"\n测试: {case['name']}")
        result = await parser.parse_async(case['content'], case['extension'])
        
        if case['expect_error']:
            if not result.success:
                print(f"✓ 正确处理错误: {result.error}")
            else:
                print(f"✗ 期望错误但成功了")
        else:
            if result.success:
                print(f"✓ 成功: {result.content[:50]}...")
            else:
                print(f"✗ 期望成功但失败了: {result.error}")


async def test_comprehensive_parsing():
    """综合解析测试"""
    print("\n=== 综合解析测试 ===")
    
    # 创建测试图像
    test_images = await create_test_images()
    
    if not test_images:
        print("无法创建测试图像，跳过综合测试")
        return
    
    parser = ImageParser()
    
    # 测试每个图像
    for filename, image_data in test_images.items():
        print(f"\n--- 测试: {image_data['description']} ---")
        
        try:
            result = await parser.parse_async(
                image_data['content'], 
                image_data['extension'],
                temperature=0.1
            )
            
            print(f"成功: {result.success}")
            print(f"文档类型: {result.doc_type}")
            
            if result.success:
                content_preview = result.content.replace('\n', '\\n')[:100]
                print(f"识别内容预览: {content_preview}")
                print(f"内容长度: {len(result.content)}")
                print(f"元数据: {result.metadata}")
            else:
                print(f"错误信息: {result.error}")
                
        except Exception as e:
            print(f"解析异常: {e}")
            import traceback
            traceback.print_exc()
    
    # 清理测试文件
    for filename in test_images.keys():
        try:
            os.remove(filename)
        except:
            pass
    
    print(f"\n已清理 {len(test_images)} 个测试文件")


async def test_temperature_effects():
    """测试温度参数的影响"""
    print("\n=== 测试温度参数影响 ===")
    
    # 创建一个简单的测试图像
    try:
        from PIL import Image, ImageDraw
        
        image = Image.new('RGB', (200, 100), 'white')
        draw = ImageDraw.Draw(image)
        draw.text((10, 30), "Temperature Test", fill='black')
        
        temp_image_path = "temp_test.png"
        image.save(temp_image_path)
        
        with open(temp_image_path, 'rb') as f:
            test_content = f.read()
        
        parser = ImageParser()
        
        # 测试不同温度值
        temperatures = [0.0, 0.1, 0.5, 1.0]
        
        for temp in temperatures:
            print(f"\n温度 {temp}:")
            result = await parser.parse_async(test_content, '.png', temperature=temp)
            
            if result.success:
                print(f"识别结果: {result.content}")
                print(f"温度设置: {result.metadata.get('temperature', 'N/A')}")
            else:
                print(f"失败: {result.error}")
        
        # 清理
        os.remove(temp_image_path)
        
    except ImportError:
        print("PIL 不可用，跳过温度测试")
    except Exception as e:
        print(f"温度测试异常: {e}")


async def main():
    """主测试函数"""
    print("图像解析器综合测试")
    print("=" * 50)
    
    # 检查环境变量
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("警告: 未设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY 环境变量")
        print("某些测试可能会失败")
    
    # 运行各种测试
    await test_image_formats()
    await test_error_cases()
    await test_comprehensive_parsing()
    await test_temperature_effects()
    
    print("\n" + "=" * 50)
    print("综合测试完成!")


if __name__ == "__main__":
    asyncio.run(main()) 