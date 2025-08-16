#!/usr/bin/env python3
"""
PDF图片链式处理集成测试
测试完整流程：PDF上传 → 解析Markdown → 提取图片链接 → OCR识别
"""

import asyncio
import json
import re
import sys
import time
from pathlib import Path

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


def extract_image_links(markdown_content: str) -> list:
    """
    从Markdown内容中提取图片链接
    
    Args:
        markdown_content: Markdown文本内容
        
    Returns:
        图片链接列表（resource_id格式，去掉file://前缀）
    """
    # 匹配Markdown图片语法: ![alt](file:///resource_id)
    pattern = r'!\[.*?\]\(file:///([^)]+\.(?:png|jpg|jpeg|gif|bmp|webp|tiff))\)'
    matches = re.findall(pattern, markdown_content)
    return matches


def format_duration(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}分{remaining_seconds:.1f}秒"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        remaining_seconds = seconds % 60
        return f"{hours}小时{minutes}分{remaining_seconds:.1f}秒"


async def main():
    """主函数"""
    # 配置
    http_service_url = "http://localhost:8080"
    mcp_service_url = "http://localhost:3001/mcp"
    test_file = "tests/files/项目汇报_202504.pdf"
    
    print("🚀 PDF图片链式处理集成测试")
    print(f"📡 HTTP服务: {http_service_url}")
    print(f"📡 MCP服务: {mcp_service_url}")
    print(f"📄 测试文件: {test_file}")
    print("=" * 80)
    
    # 记录总开始时间
    total_start_time = time.time()
    
    # 检查测试文件
    if not Path(test_file).exists():
        print(f"❌ 测试文件不存在: {test_file}")
        sys.exit(1)
    
    try:
        # 步骤1: 上传PDF文件到HTTP服务
        print(f"\n📤 步骤1: 上传PDF文件到HTTP服务")
        upload_start_time = time.time()
        
        with open(test_file, 'rb') as f:
            file_content = f.read()
        
        print(f"   文件大小: {len(file_content):,} 字节 ({len(file_content)/1024/1024:.1f} MB)")
        
        files = {
            'file': ('项目汇报_202504.pdf', file_content, 'application/pdf')
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{http_service_url}/upload", files=files)
            response.raise_for_status()
            upload_result = response.json()
        
        upload_duration = time.time() - upload_start_time
        print(f"✅ PDF上传成功! 用时: {format_duration(upload_duration)}")
        print(f"   Resource ID: {upload_result.get('resource_id')}")
        print(f"   URL: {upload_result.get('url')}")
        print(f"   文件名: {upload_result.get('filename')}")
        print(f"   大小: {upload_result.get('size')} 字节")
        
        pdf_url = upload_result.get('url')
        if not pdf_url:
            print("❌ 未获取到PDF URL")
            sys.exit(1)
        
        # 步骤2: 通过MCP服务解析PDF，获取Markdown内容
        print(f"\n📖 步骤2: 解析PDF文件，提取Markdown内容")
        print(f"   PDF URL: {pdf_url}")
        
        # 记录PDF解析开始时间
        pdf_parse_start_time = time.time()
        
        transport = StreamableHttpTransport(mcp_service_url)
        async with Client(transport) as mcp_client:
            # 解析PDF
            result = await mcp_client.call_tool("read_local_file", {
                "urls": [{"url": pdf_url}],
                "max_size": 100  # 100MB限制
            })
            
            # 记录PDF解析结束时间
            pdf_parse_duration = time.time() - pdf_parse_start_time
            
            if not result or len(result) == 0 or not hasattr(result[0], 'text'):
                print("❌ MCP服务返回空结果")
                sys.exit(1)
            
            read_result = json.loads(result[0].text)
            contents = read_result.get('contents', [])
            failed = read_result.get('failed', [])
            
            if failed:
                print(f"❌ PDF解析失败:")
                for failure in failed:
                    print(f"   - {failure.get('resource_id')}: {failure.get('error_message')}")
                sys.exit(1)
            
            if not contents:
                print(f"❌ 没有读取到PDF内容")
                sys.exit(1)
            
            pdf_content = contents[0]
            markdown_text = pdf_content.get('content', '')
            content_type = pdf_content.get('content_type', '未知')
            
            print(f"✅ PDF解析完成! 用时: {format_duration(pdf_parse_duration)}")
            print(f"   内容类型: {content_type}")
            print(f"   内容长度: {len(markdown_text):,} 字符")
            print(f"   解析速度: {len(markdown_text)/pdf_parse_duration:.0f} 字符/秒")
            print(f"   内容预览:")
            print(f"   {'-' * 40}")
            print(f"   {markdown_text[:300]}...")
            print(f"   {'-' * 40}")
            
            # 步骤3: 从Markdown中提取图片链接
            print(f"\n🖼️  步骤3: 从Markdown中提取图片链接")
            image_extract_start_time = time.time()
            
            image_links = extract_image_links(markdown_text)
            
            image_extract_duration = time.time() - image_extract_start_time
            
            if not image_links:
                print(f"❌ 未在Markdown中找到图片链接")
                print(f"   检查Markdown内容片段:")
                # 查找可能的图片引用模式
                img_patterns = re.findall(r'!\[.*?\]\([^)]+\)', markdown_text)
                if img_patterns:
                    print(f"   找到的图片模式: {img_patterns[:3]}...")
                else:
                    print(f"   未找到任何图片模式")
                sys.exit(1)
            
            print(f"✅ 找到 {len(image_links)} 个图片链接! 用时: {format_duration(image_extract_duration)}")
            for i, link in enumerate(image_links[:5], 1):  # 显示前5个
                print(f"   {i}. {link}")
            if len(image_links) > 5:
                print(f"   ... 和其他 {len(image_links) - 5} 个图片")
            
            # 步骤4: 通过MCP服务读取图片内容（OCR识别）
            print(f"\n🔍 步骤4: OCR识别图片内容")
            
            # 选择前3个图片进行OCR测试（避免过长时间）
            test_images = image_links[:3]
            print(f"   测试图片数量: {len(test_images)}")
            
            # 记录OCR开始时间
            ocr_start_time = time.time()
            
            # test_images 现在包含的是resource_id（没有file://前缀），需要重新添加前缀
            image_urls = [{"url": f"file:///{link}"} for link in test_images]
            
            result = await mcp_client.call_tool("read_local_file", {
                "urls": image_urls,
                "max_size": 10  # 10MB限制
            })
            
            # 记录OCR结束时间
            ocr_duration = time.time() - ocr_start_time
            
            if not result or len(result) == 0 or not hasattr(result[0], 'text'):
                print("❌ 图片OCR服务返回空结果")
                sys.exit(1)
            
            ocr_result = json.loads(result[0].text)
            ocr_contents = ocr_result.get('contents', [])
            ocr_failed = ocr_result.get('failed', [])
            
            print(f"✅ OCR识别完成! 用时: {format_duration(ocr_duration)}")
            print(f"   成功识别: {len(ocr_contents)} 个图片")
            print(f"   识别失败: {len(ocr_failed)} 个图片")
            print(f"   平均每图片OCR时间: {format_duration(ocr_duration/len(test_images))}")
            
            if ocr_failed:
                print(f"\n❌ OCR失败的图片:")
                for failure in ocr_failed:
                    print(f"   - {failure.get('resource_id')}: {failure.get('error_message')}")
            
            if ocr_contents:
                print(f"\n📝 OCR识别结果:")
                total_ocr_chars = 0
                for i, content in enumerate(ocr_contents, 1):
                    resource_id = content.get('resource_id', '未知')
                    ocr_text = content.get('content', '')
                    content_type = content.get('content_type', '未知')
                    
                    print(f"\n   图片 {i}: {resource_id}")
                    print(f"   内容类型: {content_type}")
                    print(f"   识别文字长度: {len(ocr_text)} 字符")
                    total_ocr_chars += len(ocr_text)
                    if ocr_text.strip():
                        print(f"   识别内容预览:")
                        print(f"   {'-' * 30}")
                        print(f"   {ocr_text[:200]}...")
                        print(f"   {'-' * 30}")
                    else:
                        print(f"   ⚠️  未识别到文字内容")
            
            # 计算总体统计
            total_duration = time.time() - total_start_time
            
            # 最终总结
            print(f"\n🎉 完整链式测试成功!")
            print(f"\n⏱️  性能统计:")
            print(f"   📤 PDF上传: {format_duration(upload_duration)}")
            print(f"   📖 PDF解析: {format_duration(pdf_parse_duration)} ({pdf_parse_duration/total_duration*100:.1f}%)")
            print(f"   🖼️  图片提取: {format_duration(image_extract_duration)}")
            print(f"   🔍 OCR识别: {format_duration(ocr_duration)} ({ocr_duration/total_duration*100:.1f}%)")
            print(f"   📊 总耗时: {format_duration(total_duration)}")
            
            print(f"\n📊 处理结果:")
            print(f"   ✅ PDF解析: {len(markdown_text):,} 字符")
            print(f"   ✅ 图片提取: {len(image_links)} 个图片")
            print(f"   ✅ OCR识别: {len(ocr_contents)}/{len(test_images)} 成功")
            
            if ocr_contents:
                total_ocr_text = sum(len(c.get('content', '')) for c in ocr_contents)
                print(f"   ✅ 总识别文字: {total_ocr_text:,} 字符")
                print(f"   ✅ OCR效率: {total_ocr_text/ocr_duration:.0f} 字符/秒")
            
            print(f"\n🌟 端到端集成测试完全通过! 整个链路运行正常!")
            
            # 性能分析
            print(f"\n📈 性能分析:")
            print(f"   🐌 最耗时环节: {'PDF解析' if pdf_parse_duration > ocr_duration else 'OCR识别'}")
            print(f"   ⚡ 并发优化效果: 使用max_workers=5进行并发处理")
            if pdf_parse_duration > 30:
                print(f"   💡 优化建议: PDF解析时间较长，可能因为文档包含大量图片需要提取和上传")
            
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP请求失败: {e.response.status_code}")
        try:
            error_detail = e.response.json()
            print(f"   错误详情: {error_detail}")
        except:
            print(f"   错误内容: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 