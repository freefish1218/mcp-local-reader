"""
压缩文件解析器
支持ZIP、RAR、7Z、TAR等压缩格式的解析，提取文件并生成文件树Markdown
"""

import tempfile
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List

from .base import BaseParser
from .mixins.file_mixin import FileProcessingMixin
from ..models import ParseResult
from .utils.archive_utils import ArchiveExtractor


class ArchiveParser(BaseParser, FileProcessingMixin):
    """压缩文件解析器，解包并输出文件树Markdown格式"""

    def __init__(self):
        """初始化压缩文件解析器"""
        BaseParser.__init__(self)
        FileProcessingMixin.__init__(self)
        self.parser_version = "1.0"
        
        # 初始化压缩文件提取器
        self.archive_extractor = ArchiveExtractor()
        
        # 支持的压缩文件格式
        self.supported_formats = {
            '.zip', '.rar', '.7z', '.tar', '.gz', 
            '.tar.gz', '.tgz', '.tar.bz2', '.tbz2'
        }

    def _parse_content(self, content: bytes, file_extension: str = None) -> ParseResult:
        """
        解析压缩文件，返回文件树Markdown格式内容
        
        Args:
            content: 文件内容字节数据
            file_extension: 文件扩展名
            
        Returns:
            解析结果对象，内容为文件树Markdown格式
        """
        if not file_extension:
            return self._create_error_result("缺少文件扩展名")
        
        file_extension = file_extension.lower()
        
        # 检查是否支持该压缩格式
        if file_extension not in self.supported_formats:
            return self._create_error_result(f"不支持的压缩文件类型: {file_extension}")
        
        temp_archive_file = None
        temp_extract_dir = None
        
        try:
            self.logger.info(f"开始解析压缩文件: {file_extension}")
            
            # 保存压缩文件到临时位置
            temp_archive_file = tempfile.NamedTemporaryFile(suffix=file_extension, delete=False)
            # 确保临时文件权限为600（仅所有者可读写）
            os.chmod(temp_archive_file.name, 0o600)
            temp_archive_file.write(content)
            temp_archive_file.close()
            
            # 创建临时解压目录
            temp_extract_dir = tempfile.mkdtemp(prefix=f"archive_{file_extension[1:]}_extract_")
            # 确保临时目录权限为700（仅所有者可读写执行）
            os.chmod(temp_extract_dir, 0o700)
            
            # 解压文件
            extracted_files = self.archive_extractor.extract_archive(
                temp_archive_file.name, 
                temp_extract_dir, 
                file_extension
            )
            
            if not extracted_files:
                return self._create_error_result("压缩文件为空或解压失败")
            
            # 生成文件树Markdown内容
            markdown_content = self._generate_file_tree_markdown(
                extracted_files, 
                temp_extract_dir, 
                file_extension,
                len(content)
            )
            
            # 处理提取的文件（上传到存储服务）
            processed_markdown, file_resources = self.process_archive_files(
                files=extracted_files,
                markdown_content=markdown_content,
                temp_dir=temp_extract_dir,
                doc_type=file_extension[1:],  # 去掉点号
                source_file_path=temp_archive_file.name
            )
            
            # 创建元数据
            archive_stats = self.archive_extractor.get_archive_stats(extracted_files, len(content))
            metadata = {
                "parser": "archive_extractor",
                "original_format": file_extension,
                "output_format": "markdown",
                "file_count": len(extracted_files),
                "file_resources": file_resources,
                **archive_stats
            }
            
            self.logger.info(f"压缩文件解析成功: {file_extension} -> Markdown, 文件: {len(extracted_files)}")
            return self._create_success_result(processed_markdown, file_extension.replace('.', ''), metadata)
            
        except Exception as e:
            self.logger.error(f"解析压缩文件失败: {e}")
            return self._create_error_result(f"解析压缩文件失败: {e}")
        finally:
            # 清理临时文件
            if temp_archive_file and os.path.exists(temp_archive_file.name):
                os.unlink(temp_archive_file.name)
            if temp_extract_dir and os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir, ignore_errors=True)

    def _generate_file_tree_markdown(self, files: List[Path], base_path: str, 
                                    file_extension: str, archive_size: int) -> str:
        """
        生成文件树的Markdown表示
        
        Args:
            files: 文件路径列表
            base_path: 基础路径
            file_extension: 压缩文件扩展名
            archive_size: 压缩文件大小
            
        Returns:
            文件树Markdown内容
        """
        try:
            # 按路径排序文件
            sorted_files = sorted(files, key=lambda x: str(x.relative_to(base_path)))
            
            # 构建目录结构字典
            dir_structure = {}
            file_structure = {}
            
            for file_path in sorted_files:
                relative_path = file_path.relative_to(base_path)
                parts = relative_path.parts
                
                # 构建目录结构
                current_level = dir_structure
                for part in parts[:-1]:  # 除了文件名本身
                    if part not in current_level:
                        current_level[part] = {}
                    current_level = current_level[part]
                
                # 添加文件
                if len(parts) > 0:
                    filename = parts[-1]
                    parent_path = parts[:-1] if len(parts) > 1 else ()
                    
                    if parent_path not in file_structure:
                        file_structure[parent_path] = []
                    file_structure[parent_path].append((filename, file_path))
            
            # 生成Markdown内容
            markdown_parts = []
            
            # 添加标题
            markdown_parts.append(f"# 压缩包内容: {file_extension} 文件")
            markdown_parts.append("")
            
            # 添加统计信息
            archive_stats = self.archive_extractor.get_archive_stats(sorted_files, archive_size)
            markdown_parts.append("## 📊 压缩包信息")
            markdown_parts.append("")
            markdown_parts.append(f"- **文件数量**: {archive_stats['file_count']} 个")
            markdown_parts.append(f"- **压缩包大小**: {self._format_size(archive_stats['archive_size'])}")
            markdown_parts.append(f"- **解压后大小**: {self._format_size(archive_stats['total_extracted_size'])}")
            markdown_parts.append(f"- **压缩率**: {archive_stats['compression_ratio']}%")
            markdown_parts.append("")
            
            # 添加文件类型分布
            if archive_stats['file_type_distribution']:
                markdown_parts.append("### 📋 文件类型分布")
                markdown_parts.append("")
                for file_type, count in sorted(archive_stats['file_type_distribution'].items()):
                    type_name = file_type if file_type else "无扩展名"
                    markdown_parts.append(f"- **{type_name}**: {count} 个")
                markdown_parts.append("")
            
            # 添加文件树
            markdown_parts.append("## 📁 文件结构")
            markdown_parts.append("")
            markdown_parts.append("```")
            
            # 递归生成文件树
            tree_lines = self._build_tree_lines(dir_structure, file_structure, (), 0)
            markdown_parts.extend(tree_lines)
            
            markdown_parts.append("```")
            markdown_parts.append("")
            
            # 添加文件列表（带下载链接）
            markdown_parts.append("## 📄 文件列表")
            markdown_parts.append("")
            
            for file_path in sorted_files:
                relative_path = file_path.relative_to(base_path)
                icon = self.archive_extractor.get_file_icon(file_path)
                file_size = self._format_size(file_path.stat().st_size)
                
                # 这里的链接会被后续处理替换为真实的resource_id
                markdown_parts.append(f"- {icon} **{relative_path}** ({file_size}) → [{relative_path}]({file_path.name})")
            
            return "\n".join(markdown_parts)
            
        except Exception as e:
            self.logger.error(f"生成文件树Markdown失败: {e}")
            return f"# 压缩包内容: {file_extension} 文件\n\n解析文件树时发生错误: {e}"

    def _build_tree_lines(self, dir_structure: dict, file_structure: dict, 
                         current_path: tuple, depth: int) -> List[str]:
        """
        递归构建文件树行
        
        Args:
            dir_structure: 目录结构字典
            file_structure: 文件结构字典
            current_path: 当前路径
            depth: 当前深度
            
        Returns:
            文件树行列表
        """
        lines = []
        prefix = "│   " * depth
        
        # 处理当前路径下的目录
        if current_path in dir_structure or (len(current_path) == 0 and dir_structure):
            current_dirs = dir_structure if len(current_path) == 0 else dir_structure
            for path_part in current_path:
                if path_part in current_dirs:
                    current_dirs = current_dirs[path_part]
                else:
                    current_dirs = {}
                    break
            
            # 添加子目录
            for dirname in sorted(current_dirs.keys()):
                lines.append(f"{prefix}├── 📁 {dirname}/")
                sub_lines = self._build_tree_lines(
                    dir_structure, file_structure, 
                    current_path + (dirname,), depth + 1
                )
                lines.extend(sub_lines)
        
        # 处理当前路径下的文件
        if current_path in file_structure:
            for filename, file_path in sorted(file_structure[current_path]):
                icon = self.archive_extractor.get_file_icon(file_path)
                lines.append(f"{prefix}├── {icon} {filename}")
        
        return lines

    def _format_size(self, size_bytes: int) -> str:
        """
        格式化文件大小显示
        
        Args:
            size_bytes: 字节大小
            
        Returns:
            格式化的大小字符串
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def get_archive_upload_stats(self) -> Dict[str, Any]:
        """
        获取文件上传统计信息
        
        Returns:
            上传统计信息字典
        """
        return self.get_file_upload_stats()
