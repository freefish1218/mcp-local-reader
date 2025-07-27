#!/usr/bin/env python3
"""
实际文件解析测试脚本
测试 tests/files 目录下所有文件的解析情况，检查缺少的依赖库，并将解析结果保存到 tests/outputs 目录
"""

import os
import sys
import importlib
import unicodedata
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict


@dataclass
class ParseTestResult:
    """测试结果数据类"""
    file_path: str
    success: bool
    error_message: str = ""
    content_length: int = 0
    metadata: dict = None
    parser_used: str = ""
    output_file: str = ""  # 新增：保存的输出文件路径


class DependencyChecker:
    """依赖库检查器"""
    
    REQUIRED_LIBS = {
        # 核心解析库
        'fitz': ('PyMuPDF', 'PDF解析 - 必需'),
        'pptx': ('python-pptx', 'PowerPoint解析 - 必需'),
        'odf': ('odfpy', 'ODT文档解析 - 推荐'),
        # LLM和图像处理
        'PIL': ('Pillow', '图像处理（OCR用） - 可选'),
    }
    
    def check_dependencies(self) -> Dict[str, bool]:
        """检查依赖库安装情况"""
        results = {}
        missing_libs = []
        
        print("🔍 检查依赖库安装情况...")
        print("-" * 50)
        
        for import_name, (lib_name, description) in self.REQUIRED_LIBS.items():
            try:
                importlib.import_module(import_name)
                print(f"✅ {lib_name}: 已安装 ({description})")
                results[lib_name] = True
            except ImportError:
                print(f"❌ {lib_name}: 未安装 ({description})")
                results[lib_name] = False
                missing_libs.append((lib_name, import_name))
        
        if missing_libs:
            print(f"\n💡 缺少的库安装命令:")
            for lib_name, _ in missing_libs:
                print(f"   pip install {lib_name}")
        
        return results


class FileParserTester:
    """文件解析测试器"""
    
    def __init__(self, files_dir: str = "tests/files", outputs_dir: str = "tests/outputs"):
        self.files_dir = Path(files_dir)
        self.outputs_dir = Path(outputs_dir)
        self.dependency_checker = DependencyChecker()
        self.test_results: List[ParseTestResult] = []
        
        # 创建输出目录
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查项目根目录
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root / "src"))
    
    def _sanitize_filename(self, filename: str) -> str:
        """处理文件名，确保中文文件名安全保存"""
        # 替换不安全的字符
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        
        # 处理Unicode规范化，确保中文字符正确
        filename = unicodedata.normalize('NFC', filename)
        
        # 确保文件名不为空且不以点开始
        if not filename or filename.startswith('.'):
            filename = 'untitled' + filename
        
        return filename
    
    def _save_parse_result(self, file_path: Path, content: str, metadata: dict, parser_used: str) -> str:
        """保存解析结果到输出目录"""
        try:
            # 处理输出文件名
            original_name = file_path.stem  # 不包含扩展名的文件名
            safe_name = self._sanitize_filename(original_name)
            output_filename = f"{safe_name}.md"
            output_path = self.outputs_dir / output_filename
            
            # 如果文件已存在，添加序号
            counter = 1
            while output_path.exists():
                output_filename = f"{safe_name}_{counter}.md"
                output_path = self.outputs_dir / output_filename
                counter += 1
            
            # 保存解析内容
            with open(output_path, 'w', encoding='utf-8') as f:
                # 写入文件头信息
                f.write(f"# 文件解析结果\n")
                f.write(f"原始文件: {file_path.name}\n")
                f.write(f"解析器: {parser_used}\n")
                f.write(f"内容长度: {len(content)} 字符\n")
                
                if metadata:
                    f.write(f"元数据: {json.dumps(metadata, ensure_ascii=False, indent=2)}\n")
                
                f.write(f"\n{'='*50}\n")
                f.write(f"解析内容:\n")
                f.write(f"{'='*50}\n\n")
                
                # 写入实际内容
                f.write(content)
            
            print(f"   💾 内容已保存到: {output_filename}")
            return str(output_path)
            
        except Exception as e:
            print(f"   ⚠️ 保存文件失败: {str(e)}")
            return ""
    
    def test_pdf_file(self, file_path: Path) -> ParseTestResult:
        """测试PDF文件解析"""
        try:
            from file_reader.parsers.pdf_parser import PDFParser
            
            # 读取文件内容
            with open(file_path, 'rb') as f:
                content = f.read()
            
            parser = PDFParser()
            result = parser.parse(content, file_path.suffix)
            
            output_file = ""
            if result.success:
                output_file = self._save_parse_result(
                    file_path, result.content, result.metadata, "PDFParser"
                )
            
            return ParseTestResult(
                file_path=str(file_path),
                success=result.success,
                error_message=result.error if not result.success else "",
                content_length=len(result.content) if result.success else 0,
                metadata=result.metadata if result.success else {},
                parser_used="PDFParser",
                output_file=output_file
            )
        except Exception as e:
            return ParseTestResult(
                file_path=str(file_path),
                success=False,
                error_message=f"PDF解析失败: {str(e)}",
                parser_used="PDFParser"
            )
    
    def test_office_file(self, file_path: Path) -> ParseTestResult:
        """测试Office文件解析（DOC, DOCX, XLSX, XLS, PPT, PPTX, ODT等）"""
        try:
            from file_reader.parsers.office_parser import OfficeParser
            
            # 读取文件内容
            with open(file_path, 'rb') as f:
                content = f.read()
            
            parser = OfficeParser()
            result = parser.parse(content, file_path.suffix)
            
            output_file = ""
            if result.success:
                output_file = self._save_parse_result(
                    file_path, result.content, result.metadata, "OfficeParser"
                )
            
            return ParseTestResult(
                file_path=str(file_path),
                success=result.success,
                error_message=result.error if not result.success else "",
                content_length=len(result.content) if result.success else 0,
                metadata=result.metadata if result.success else {},
                parser_used="OfficeParser",
                output_file=output_file
            )
        except Exception as e:
            return ParseTestResult(
                file_path=str(file_path),
                success=False,
                error_message=f"Office文件解析失败: {str(e)}",
                parser_used="OfficeParser"
            )
    
    def test_text_file(self, file_path: Path) -> ParseTestResult:
        """测试文本文件解析（TXT, MD等）"""
        try:
            from file_reader.parsers.text_parser import TextParser
            
            # 读取文件内容
            with open(file_path, 'rb') as f:
                content = f.read()
            
            parser = TextParser()
            result = parser.parse(content, file_path.suffix)
            
            output_file = ""
            if result.success:
                output_file = self._save_parse_result(
                    file_path, result.content, result.metadata, "TextParser"
                )
            
            return ParseTestResult(
                file_path=str(file_path),
                success=result.success,
                error_message=result.error if not result.success else "",
                content_length=len(result.content) if result.success else 0,
                metadata=result.metadata if result.success else {},
                parser_used="TextParser",
                output_file=output_file
            )
        except Exception as e:
            return ParseTestResult(
                file_path=str(file_path),
                success=False,
                error_message=f"文本文件解析失败: {str(e)}",
                parser_used="TextParser"
            )
    
    async def test_image_file(self, file_path: Path) -> ParseTestResult:
        """测试图片文件解析（PNG, JPG, JPEG, GIF, BMP, WEBP）"""
        try:
            from file_reader.parsers.image_parser import ImageParser
            
            # 读取文件内容
            with open(file_path, 'rb') as f:
                content = f.read()
            
            parser = ImageParser()
            result = await parser.parse_async(content, file_path.suffix)
            
            output_file = ""
            if result.success:
                output_file = self._save_parse_result(
                    file_path, result.content, result.metadata, "ImageParser"
                )
            
            return ParseTestResult(
                file_path=str(file_path),
                success=result.success,
                error_message=result.error if not result.success else "",
                content_length=len(result.content) if result.success else 0,
                metadata=result.metadata if result.success else {},
                parser_used="ImageParser",
                output_file=output_file
            )
        except Exception as e:
            return ParseTestResult(
                file_path=str(file_path),
                success=False,
                error_message=f"图片解析失败: {str(e)}",
                parser_used="ImageParser"
            )
    
    def get_parser_for_file(self, file_path: Path) -> callable:
        """根据文件扩展名选择合适的解析器"""
        suffix = file_path.suffix.lower()
        
        if suffix == '.pdf':
            return self.test_pdf_file
        elif suffix in ['.doc', '.docx', '.xlsx', '.xls', '.ppt', '.pptx', '.odt', '.ods', '.odp', '.csv', '.epub', '.rtf']:
            return self.test_office_file
        elif suffix in ['.txt', '.md', '.markdown']:
            return self.test_text_file
        elif suffix in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff']:
            return self.test_image_file
        else:
            return None
    
    async def test_all_files(self) -> List[ParseTestResult]:
        """测试所有文件"""
        if not self.files_dir.exists():
            print(f"❌ 目录不存在: {self.files_dir}")
            return []
        
        print(f"📂 开始测试目录: {self.files_dir}")
        print(f"💾 输出目录: {self.outputs_dir}")
        print("=" * 60)
        
        # 获取所有测试文件
        test_files = []
        for file_path in self.files_dir.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                test_files.append(file_path)
        
        test_files.sort(key=lambda x: x.name)
        
        if not test_files:
            print("❌ 未找到测试文件")
            return []
        
        print(f"📋 找到 {len(test_files)} 个测试文件:")
        for file_path in test_files:
            file_size = file_path.stat().st_size / 1024  # KB
            print(f"   - {file_path.name} ({file_size:.1f}KB)")
        
        print("\n" + "=" * 60)
        print("🧪 开始解析测试...")
        print("-" * 60)
        
        # 逐个测试文件
        for i, file_path in enumerate(test_files, 1):
            print(f"\n[{i}/{len(test_files)}] 测试文件: {file_path.name}")
            
            parser_func = self.get_parser_for_file(file_path)
            if not parser_func:
                result = ParseTestResult(
                    file_path=str(file_path),
                    success=False,
                    error_message=f"不支持的文件类型: {file_path.suffix}",
                    parser_used="Unknown"
                )
            else:
                # 检查是否是异步函数
                import inspect
                if inspect.iscoroutinefunction(parser_func):
                    result = await parser_func(file_path)
                else:
                    result = parser_func(file_path)
            
            self.test_results.append(result)
            
            # 打印测试结果
            if result.success:
                print(f"   ✅ 解析成功 - 内容长度: {result.content_length} 字符")
                if result.metadata:
                    # 只显示关键元数据
                    key_metadata = {k: v for k, v in result.metadata.items() 
                                  if k in ['页数', 'pages', 'document_type', 'file_type', 'ocr_method', 'image_format', 'image_size', 'temperature']}
                    if key_metadata:
                        print(f"   📄 元数据: {key_metadata}")
                        
                # 对于图片文件，显示识别内容预览
                if result.parser_used == "ImageParser" and result.success:
                    # 从元数据中获取内容长度，或者使用已有的长度信息
                    if result.content_length > 0:
                        print(f"   🔍 OCR识别文字长度: {result.content_length} 字符")
            else:
                print(f"   ❌ 解析失败 - {result.error_message}")
        
        return self.test_results
    
    def save_test_report(self):
        """保存测试报告到JSON文件"""
        try:
            report_data = {
                'summary': {
                    'total_files': len(self.test_results),
                    'successful_files': sum(1 for r in self.test_results if r.success),
                    'failed_files': sum(1 for r in self.test_results if not r.success),
                    'success_rate': (sum(1 for r in self.test_results if r.success) / len(self.test_results) * 100) if self.test_results else 0
                },
                'results': [asdict(result) for result in self.test_results]
            }
            
            report_path = self.outputs_dir / "test_report.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n📊 测试报告已保存到: {report_path}")
            
        except Exception as e:
            print(f"\n⚠️ 保存测试报告失败: {str(e)}")
    
    def print_summary(self):
        """打印测试总结"""
        if not self.test_results:
            print("❌ 没有测试结果")
            return
        
        print("\n" + "=" * 60)
        print("📊 测试总结报告")
        print("=" * 60)
        
        total_files = len(self.test_results)
        successful_files = sum(1 for r in self.test_results if r.success)
        failed_files = total_files - successful_files
        
        print(f"📈 总体统计:")
        print(f"   总文件数: {total_files}")
        print(f"   成功解析: {successful_files}")
        print(f"   解析失败: {failed_files}")
        print(f"   成功率: {(successful_files/total_files)*100:.1f}%")
        
        # 按文件类型分组统计
        print(f"\n📋 文件类型统计:")
        file_types = {}
        for result in self.test_results:
            ext = Path(result.file_path).suffix.lower()
            if ext not in file_types:
                file_types[ext] = {'total': 0, 'success': 0}
            file_types[ext]['total'] += 1
            if result.success:
                file_types[ext]['success'] += 1
        
        for ext, stats in sorted(file_types.items()):
            success_rate = (stats['success'] / stats['total']) * 100
            print(f"   {ext}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        
        # 失败文件详情
        if failed_files > 0:
            print(f"\n❌ 解析失败的文件:")
            for result in self.test_results:
                if not result.success:
                    print(f"   - {Path(result.file_path).name}: {result.error_message}")
        
        # 成功文件详情
        if successful_files > 0:
            print(f"\n✅ 解析成功的文件:")
            for result in self.test_results:
                if result.success:
                    output_info = f" -> {Path(result.output_file).name}" if result.output_file else ""
                    print(f"   - {Path(result.file_path).name}: {result.content_length} 字符{output_info}")


async def main():
    """主函数"""
    print("🧪 实际文件解析测试工具")
    print("=" * 60)
    
    # 初始化测试器
    tester = FileParserTester()
    
    # 检查依赖库
    dependency_results = tester.dependency_checker.check_dependencies()
    
    print("\n" + "=" * 60)
    
    # 测试所有文件
    results = await tester.test_all_files()
    
    # 保存测试报告
    tester.save_test_report()
    
    # 打印总结
    tester.print_summary()
    
    # 根据结果提供建议
    print("\n" + "=" * 60)
    print("💡 解决建议:")
    
    failed_results = [r for r in results if not r.success]
    if failed_results:
        missing_libs = []
        for result in failed_results:
            if "No module named 'docx2txt'" in result.error_message:
                missing_libs.append("docx2txt")
            elif "No module named 'unstructured'" in result.error_message:
                missing_libs.append("unstructured")
            elif "No module named 'pptx'" in result.error_message:
                missing_libs.append("python-pptx")
        
        if missing_libs:
            print("📦 需要安装的库:")
            for lib in set(missing_libs):
                print(f"   pip install {lib}")
        else:
            print("🔧 检查具体错误信息，可能需要系统依赖或文件损坏")
    else:
        print("🎉 所有文件都解析成功！")
    
    # 输出目录信息
    successful_outputs = [r for r in results if r.success and r.output_file]
    if successful_outputs:
        print(f"\n📁 解析结果已保存到 tests/outputs 目录:")
        print(f"   共 {len(successful_outputs)} 个文件")
        print(f"   测试报告: test_report.json")
    
    print("\n" + "=" * 60)
    return len([r for r in results if r.success])


if __name__ == "__main__":
    import asyncio
    
    try:
        success_count = asyncio.run(main())
        sys.exit(0 if success_count > 0 else 1)
    except KeyboardInterrupt:
        print("\n\n❌ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        sys.exit(1) 