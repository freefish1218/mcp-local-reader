"""
文档转换工具
提供Office文档格式转换功能，主要用于旧格式到新格式的转换
"""

import tempfile
import subprocess
import shlex
import os
from pathlib import Path
from typing import Optional
import shutil

from ...utils import get_logger


class DocumentConverter:
    """文档格式转换器，主要使用LibreOffice进行转换"""

    def __init__(self):
        """初始化文档转换器"""
        self.logger = get_logger("document_converter")

    def convert_old_format_with_libreoffice(self, file_path: str, file_extension: str) -> Optional[str]:
        """
        使用LibreOffice将旧格式文件转换为新格式
        
        Args:
            file_path: 输入文件路径
            file_extension: 文件扩展名 (.doc, .xls, .ppt)
            
        Returns:
            转换后的文件路径，失败返回None
        """
        try:
            # 确定目标格式
            format_mapping = {
                '.doc': 'docx',
                '.xls': 'xlsx', 
                '.ppt': 'pptx'
            }
            
            target_format = format_mapping.get(file_extension)
            if not target_format:
                raise Exception(f"不支持的旧格式: {file_extension}")
            
            self.logger.info(f"使用LibreOffice转换 {file_extension} -> {target_format}")
            
            # 创建临时输出目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # LibreOffice命令行转换，使用shlex.quote()防止命令注入
                # 对文件路径和输出目录进行安全转义
                safe_file_path = shlex.quote(os.path.abspath(file_path))
                safe_temp_dir = shlex.quote(os.path.abspath(temp_dir))
                
                cmd = [
                    'libreoffice',
                    '--headless',
                    '--convert-to', target_format,
                    '--outdir', safe_temp_dir,
                    safe_file_path
                ]
                
                # 尝试不同的LibreOffice命令名称
                libreoffice_commands = [
                    'libreoffice', 
                    'soffice', 
                    '/Applications/LibreOffice.app/Contents/MacOS/soffice'
                ]
                
                conversion_success = False
                for lo_cmd in libreoffice_commands:
                    try:
                        cmd[0] = lo_cmd
                        self.logger.debug(f"尝试使用命令: {' '.join(cmd)}")
                        
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=120  # 2分钟超时
                        )
                        
                        if result.returncode == 0:
                            conversion_success = True
                            self.logger.info(f"LibreOffice转换成功，使用命令: {lo_cmd}")
                            break
                        else:
                            self.logger.debug(f"命令 {lo_cmd} 失败: {result.stderr}")
                    
                    except FileNotFoundError:
                        self.logger.debug(f"命令 {lo_cmd} 未找到")
                        continue
                    except subprocess.TimeoutExpired:
                        self.logger.warning(f"LibreOffice转换超时: {lo_cmd}")
                        continue
                    except Exception as e:
                        self.logger.debug(f"命令 {lo_cmd} 执行异常: {e}")
                        continue
                
                if not conversion_success:
                    raise Exception("LibreOffice转换失败：未找到可用的LibreOffice命令或转换失败")
                
                # 查找转换后的文件
                original_filename = Path(file_path).stem
                target_file = Path(temp_dir) / f"{original_filename}.{target_format}"
                
                if not target_file.exists():
                    raise Exception(f"转换后的文件不存在: {target_file}")
                
                # 将文件复制到新的临时位置（因为temp_dir会被清理）
                new_temp_file = tempfile.NamedTemporaryFile(
                    suffix=f'.{target_format}', 
                    delete=False
                )
                # 确保临时文件权限为600（仅所有者可读写）
                os.chmod(new_temp_file.name, 0o600)
                new_temp_file.close()
                
                shutil.copy2(str(target_file), new_temp_file.name)
                
                self.logger.info(f"成功转换 {file_extension} -> {target_format}: {new_temp_file.name}")
                return new_temp_file.name
                
        except Exception as e:
            self.logger.error(f"LibreOffice转换失败: {e}")
            return None

    def is_old_format(self, file_extension: str) -> bool:
        """
        判断是否为需要转换的旧格式
        
        Args:
            file_extension: 文件扩展名
            
        Returns:
            是否为旧格式
        """
        return file_extension.lower() in ['.doc', '.xls', '.ppt']

    def get_target_format(self, old_extension: str) -> str:
        """
        获取旧格式对应的新格式
        
        Args:
            old_extension: 旧格式扩展名
            
        Returns:
            新格式扩展名
        """
        mapping = {
            '.doc': '.docx',
            '.xls': '.xlsx',
            '.ppt': '.pptx'
        }
        return mapping.get(old_extension.lower(), old_extension) 