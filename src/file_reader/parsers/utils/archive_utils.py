"""
压缩文件处理工具
提供各种压缩格式的解包功能，支持安全检查和递归目录遍历
"""

import os
import shutil
import zipfile
import tarfile
import gzip
from pathlib import Path
from typing import List, Optional, Dict, Any
import tempfile

from ...utils import get_logger


class ArchiveExtractor:
    """压缩文件提取器"""
    
    def __init__(self):
        """初始化压缩文件提取器"""
        self.logger = get_logger("archive_extractor")
        
        # 安全配置
        self.max_file_size = int(os.getenv("ARCHIVE_MAX_FILE_SIZE_MB", "100")) * 1024 * 1024  # 100MB
        self.max_extracted_size = int(os.getenv("ARCHIVE_MAX_TOTAL_SIZE_MB", "500")) * 1024 * 1024  # 500MB
        self.max_file_count = int(os.getenv("ARCHIVE_MAX_FILES_LIMIT", "1000"))  # 最大文件数
        self.extract_timeout = int(os.getenv("ARCHIVE_EXTRACT_TIMEOUT", "300"))  # 5分钟超时
        
        # 支持的压缩格式映射
        self.extraction_methods = {
            '.zip': self._extract_zip,
            '.rar': self._extract_rar,
            '.7z': self._extract_7z,
            '.tar': self._extract_tar,
            '.gz': self._extract_gz,
            '.tar.gz': self._extract_tar_gz,
            '.tgz': self._extract_tar_gz,
            '.tar.bz2': self._extract_tar_bz2,
            '.tbz2': self._extract_tar_bz2
        }
        
        # 文件类型图标映射
        self.file_type_icons = {
            # 文档
            '.pdf': '📄', '.doc': '📄', '.docx': '📄', '.txt': '📄', '.rtf': '📄',
            '.odt': '📄', '.md': '📄', '.markdown': '📄', '.json': '📄',
            
            # 电子表格
            '.xls': '📊', '.xlsx': '📊', '.csv': '📊', '.ods': '📊',
            
            # 演示文稿
            '.ppt': '📽️', '.pptx': '📽️', '.odp': '📽️',
            
            # 图片
            '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️',
            '.bmp': '🖼️', '.webp': '🖼️', '.tiff': '🖼️',
            
            # 代码文件
            '.py': '🐍', '.js': '📜', '.html': '🌐', '.css': '🎨', '.java': '☕',
            '.cpp': '⚙️', '.c': '⚙️', '.php': '🐘', '.rb': '💎', '.go': '🔷',
            
            # 压缩文件
            '.zip': '📦', '.rar': '📦', '.7z': '📦', '.tar': '📦', '.gz': '📦',
            
            # 音频视频
            '.mp3': '🎵', '.wav': '🎵', '.mp4': '🎬', '.avi': '🎬', '.mov': '🎬',
            
            # 默认
            'default': '📄'
        }

    def extract_archive(self, archive_path: str, extract_path: str, file_extension: str) -> List[Path]:
        """
        根据文件扩展名提取压缩文件
        
        Args:
            archive_path: 压缩文件路径
            extract_path: 解压目标路径
            file_extension: 文件扩展名
            
        Returns:
            提取的文件路径列表
        """
        try:
            self.logger.info(f"开始解压缩文件: {archive_path} -> {extract_path}")
            
            # 安全检查
            if not self._check_archive_safety(archive_path):
                raise Exception("压缩文件安全检查失败")
            
            # 创建解压目录
            os.makedirs(extract_path, exist_ok=True)
            
            # 根据文件扩展名选择解压方法
            extraction_method = self.extraction_methods.get(file_extension.lower())
            if not extraction_method:
                raise Exception(f"不支持的压缩格式: {file_extension}")
            
            # 执行解压
            extracted_files = extraction_method(archive_path, extract_path)
            
            # 后续安全检查
            if not self._check_extracted_files_safety(extracted_files):
                raise Exception("解压文件安全检查失败")
            
            self.logger.info(f"解压成功，提取了 {len(extracted_files)} 个文件")
            return extracted_files
            
        except Exception as e:
            self.logger.error(f"解压缩文件失败: {e}")
            # 清理可能的部分解压文件
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path, ignore_errors=True)
            raise

    def _extract_zip(self, archive_path: str, extract_path: str) -> List[Path]:
        """提取ZIP文件"""
        extracted_files = []
        
        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                # 检查ZIP文件信息
                file_count = len(zip_ref.namelist())
                if file_count > self.max_file_count:
                    raise Exception(f"ZIP文件包含过多文件: {file_count} > {self.max_file_count}")
                
                total_size = sum(info.file_size for info in zip_ref.filelist)
                if total_size > self.max_extracted_size:
                    raise Exception(f"ZIP解压后大小过大: {total_size} > {self.max_extracted_size}")
                
                # 逐个提取文件
                for member in zip_ref.namelist():
                    if self._is_safe_path(member, extract_path):
                        zip_ref.extract(member, extract_path)
                        extracted_file = Path(extract_path) / member
                        if extracted_file.is_file():
                            extracted_files.append(extracted_file)
                
        except zipfile.BadZipFile:
            raise Exception("损坏的ZIP文件")
        except Exception as e:
            raise Exception(f"ZIP解压失败: {e}")
        
        return extracted_files

    def _extract_rar(self, archive_path: str, extract_path: str) -> List[Path]:
        """提取RAR文件"""
        extracted_files = []
        
        try:
            import rarfile
        except ImportError:
            raise Exception("缺少rarfile库，请安装: pip install rarfile")
        
        try:
            with rarfile.RarFile(archive_path, 'r') as rar_ref:
                # 检查RAR文件信息
                file_count = len(rar_ref.namelist())
                if file_count > self.max_file_count:
                    raise Exception(f"RAR文件包含过多文件: {file_count} > {self.max_file_count}")
                
                # 逐个提取文件
                for member in rar_ref.namelist():
                    if self._is_safe_path(member, extract_path):
                        rar_ref.extract(member, extract_path)
                        extracted_file = Path(extract_path) / member
                        if extracted_file.is_file():
                            extracted_files.append(extracted_file)
                
        except rarfile.BadRarFile:
            raise Exception("损坏的RAR文件")
        except Exception as e:
            raise Exception(f"RAR解压失败: {e}")
        
        return extracted_files

    def _extract_7z(self, archive_path: str, extract_path: str) -> List[Path]:
        """提取7Z文件"""
        extracted_files = []
        
        try:
            import py7zr
        except ImportError:
            raise Exception("缺少py7zr库，请安装: pip install py7zr")
        
        try:
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                # 检查7Z文件信息
                file_count = len(archive.getnames())
                if file_count > self.max_file_count:
                    raise Exception(f"7Z文件包含过多文件: {file_count} > {self.max_file_count}")
                
                # 提取所有文件
                archive.extractall(path=extract_path)
                
                # 收集提取的文件
                for member in archive.getnames():
                    extracted_file = Path(extract_path) / member
                    if extracted_file.is_file() and self._is_safe_path(member, extract_path):
                        extracted_files.append(extracted_file)
                
        except py7zr.Bad7zFile:
            raise Exception("损坏的7Z文件")
        except Exception as e:
            raise Exception(f"7Z解压失败: {e}")
        
        return extracted_files

    def _extract_tar(self, archive_path: str, extract_path: str) -> List[Path]:
        """提取TAR文件"""
        return self._extract_tar_generic(archive_path, extract_path, 'r')

    def _extract_tar_gz(self, archive_path: str, extract_path: str) -> List[Path]:
        """提取TAR.GZ文件"""
        return self._extract_tar_generic(archive_path, extract_path, 'r:gz')

    def _extract_tar_bz2(self, archive_path: str, extract_path: str) -> List[Path]:
        """提取TAR.BZ2文件"""
        return self._extract_tar_generic(archive_path, extract_path, 'r:bz2')

    def _extract_tar_generic(self, archive_path: str, extract_path: str, mode: str) -> List[Path]:
        """通用TAR文件提取方法"""
        extracted_files = []
        
        try:
            with tarfile.open(archive_path, mode) as tar_ref:
                # 检查TAR文件信息
                file_count = len(tar_ref.getnames())
                if file_count > self.max_file_count:
                    raise Exception(f"TAR文件包含过多文件: {file_count} > {self.max_file_count}")
                
                # 逐个提取文件
                for member in tar_ref.getmembers():
                    if member.isfile() and self._is_safe_path(member.name, extract_path):
                        tar_ref.extract(member, extract_path)
                        extracted_file = Path(extract_path) / member.name
                        extracted_files.append(extracted_file)
                
        except tarfile.TarError:
            raise Exception("损坏的TAR文件")
        except Exception as e:
            raise Exception(f"TAR解压失败: {e}")
        
        return extracted_files

    def _extract_gz(self, archive_path: str, extract_path: str) -> List[Path]:
        """提取GZ文件（单文件压缩）"""
        extracted_files = []
        
        try:
            # GZ文件通常是单文件压缩
            filename = Path(archive_path).stem  # 去掉.gz扩展名
            output_path = Path(extract_path) / filename
            
            with gzip.open(archive_path, 'rb') as gz_file:
                with open(output_path, 'wb') as out_file:
                    shutil.copyfileobj(gz_file, out_file)
            
            extracted_files.append(output_path)
            
        except Exception as e:
            raise Exception(f"GZ解压失败: {e}")
        
        return extracted_files

    def _is_safe_path(self, path: str, base_path: str) -> bool:
        """
        检查路径是否安全（防止路径遍历攻击）
        
        Args:
            path: 要检查的路径
            base_path: 基础路径
            
        Returns:
            是否安全
        """
        try:
            # 规范化路径
            full_path = Path(base_path) / path
            resolved_path = full_path.resolve()
            base_resolved = Path(base_path).resolve()
            
            # 检查是否在基础路径内
            return str(resolved_path).startswith(str(base_resolved))
            
        except Exception:
            return False

    def _check_archive_safety(self, archive_path: str) -> bool:
        """检查压缩文件安全性"""
        try:
            # 检查文件大小
            file_size = os.path.getsize(archive_path)
            if file_size > self.max_file_size:
                self.logger.warning(f"压缩文件过大: {file_size} > {self.max_file_size}")
                return False
            
            # 检查文件是否存在且可读
            if not os.path.exists(archive_path) or not os.access(archive_path, os.R_OK):
                self.logger.warning(f"压缩文件不存在或不可读: {archive_path}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"压缩文件安全检查失败: {e}")
            return False

    def _check_extracted_files_safety(self, extracted_files: List[Path]) -> bool:
        """检查解压文件安全性"""
        try:
            # 检查文件数量
            if len(extracted_files) > self.max_file_count:
                self.logger.warning(f"解压文件数量过多: {len(extracted_files)} > {self.max_file_count}")
                return False
            
            # 检查总大小
            total_size = sum(f.stat().st_size for f in extracted_files if f.exists())
            if total_size > self.max_extracted_size:
                self.logger.warning(f"解压文件总大小过大: {total_size} > {self.max_extracted_size}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"解压文件安全检查失败: {e}")
            return False

    def get_file_icon(self, file_path: Path) -> str:
        """
        根据文件扩展名获取对应的图标
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件图标字符串
        """
        file_extension = file_path.suffix.lower()
        return self.file_type_icons.get(file_extension, self.file_type_icons['default'])

    def generate_file_tree_text(self, files: List[Path], base_path: str) -> str:
        """
        生成文件树的文本表示
        
        Args:
            files: 文件路径列表
            base_path: 基础路径
            
        Returns:
            文件树文本
        """
        try:
            # 按路径排序文件
            sorted_files = sorted(files, key=lambda x: str(x.relative_to(base_path)))
            
            # 构建目录结构
            tree_lines = []
            dirs_processed = set()
            
            for file_path in sorted_files:
                relative_path = file_path.relative_to(base_path)
                parts = relative_path.parts
                
                # 处理目录层级
                for i, part in enumerate(parts[:-1]):  # 除了文件名本身
                    dir_path = Path(*parts[:i+1])
                    if dir_path not in dirs_processed:
                        indent = "│   " * i + "├── "
                        tree_lines.append(f"{indent}📁 {part}/")
                        dirs_processed.add(dir_path)
                
                # 处理文件
                indent = "│   " * (len(parts) - 1) + "├── "
                icon = self.get_file_icon(file_path)
                file_name = parts[-1]
                tree_lines.append(f"{indent}{icon} {file_name}")
            
            return "\n".join(tree_lines)
            
        except Exception as e:
            self.logger.warning(f"生成文件树失败: {e}")
            return "无法生成文件树"

    def get_archive_stats(self, files: List[Path], archive_size: int) -> Dict[str, Any]:
        """
        获取压缩包统计信息
        
        Args:
            files: 文件列表
            archive_size: 压缩包大小
            
        Returns:
            统计信息字典
        """
        try:
            total_size = sum(f.stat().st_size for f in files if f.exists())
            file_count = len(files)
            
            # 按类型统计
            type_stats = {}
            for file_path in files:
                ext = file_path.suffix.lower()
                if ext not in type_stats:
                    type_stats[ext] = 0
                type_stats[ext] += 1
            
            return {
                'file_count': file_count,
                'total_extracted_size': total_size,
                'archive_size': archive_size,
                'compression_ratio': round((archive_size / max(total_size, 1)) * 100, 1),
                'file_type_distribution': type_stats
            }
            
        except Exception as e:
            self.logger.warning(f"获取压缩包统计失败: {e}")
            return {
                'file_count': len(files),
                'total_extracted_size': 0,
                'archive_size': archive_size,
                'compression_ratio': 0,
                'file_type_distribution': {}
            }
