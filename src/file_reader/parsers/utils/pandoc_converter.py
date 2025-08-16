"""
Pandoc转换工具
提供使用pandoc将各种文档格式转换为Markdown的功能
"""

import tempfile
import subprocess
import os
import shlex
from pathlib import Path
from typing import Optional

from ...utils import get_logger


class PandocConverter:
    """Pandoc转换器，用于将文档转换为Markdown格式"""

    def __init__(self):
        """初始化Pandoc转换器"""
        self.logger = get_logger("pandoc_converter")

    def convert_to_markdown(self, file_path: str, file_extension: str, temp_image_dir: str = None) -> str:
        """
        使用pandoc将文档转换为Markdown格式
        支持: .docx, .odt, .rtf, .csv, .epub
        
        Args:
            file_path: 输入文件路径
            file_extension: 文件扩展名
            temp_image_dir: 临时图片目录，如果为None则创建临时目录
            
        Returns:
            转换后的Markdown内容
        """
        try:
            self.logger.info(f"使用pandoc转换文件: {file_path} ({file_extension})")
            
            # 使用提供的图片目录或创建临时目录
            if temp_image_dir:
                media_dir = temp_image_dir
                use_existing_dir = True
            else:
                media_dir = tempfile.mkdtemp(prefix="pandoc_media_")
                use_existing_dir = False
                
            try:
                # 构建pandoc命令，使用shlex.quote()防止命令注入
                # 对文件路径和媒体目录进行安全转义
                safe_file_path = shlex.quote(os.path.abspath(file_path))
                safe_media_dir = shlex.quote(os.path.abspath(media_dir))
                
                cmd = [
                    'pandoc',
                    safe_file_path,
                    '--to', 'markdown',
                    '--extract-media', safe_media_dir,
                    '--wrap', 'none',  # 不自动换行
                ]
                
                # 根据文件类型添加特定参数
                format_mapping = {
                    '.docx': 'docx',
                    '.odt': 'odt',
                    '.rtf': 'rtf',
                    '.csv': 'csv',
                    '.epub': 'epub'
                }
                
                from_format = format_mapping.get(file_extension)
                if from_format:
                    cmd.extend(['--from', from_format])
                
                self.logger.debug(f"执行pandoc命令: {' '.join(cmd)}")
                
                # 执行pandoc命令
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2分钟超时
                    encoding='utf-8'
                )
                
                if result.returncode == 0:
                    markdown_content = result.stdout.strip()
                    if markdown_content:
                        self.logger.info(f"pandoc转换成功，生成Markdown内容长度: {len(markdown_content)}")
                        
                        # 检查提取的媒体文件
                        media_files = list(Path(media_dir).rglob('*'))
                        image_files = [f for f in media_files if f.is_file() and 
                                     f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']]
                        
                        if image_files:
                            self.logger.info(f"pandoc提取了 {len(image_files)} 个图片文件")
                        
                        return markdown_content
                    else:
                        self.logger.warning("pandoc转换成功但内容为空")
                        return ""
                else:
                    error_msg = result.stderr or "未知错误"
                    self.logger.error(f"pandoc转换失败: {error_msg}")
                    raise Exception(f"pandoc转换失败: {error_msg}")
                    
            finally:
                # 如果是我们创建的临时目录，需要清理
                if not use_existing_dir and os.path.exists(media_dir):
                    import shutil
                    shutil.rmtree(media_dir, ignore_errors=True)
                    
        except subprocess.TimeoutExpired:
            self.logger.error("pandoc转换超时")
            raise Exception("pandoc转换超时")
        except FileNotFoundError:
            self.logger.error("未找到pandoc命令，请确保已安装pandoc")
            raise Exception("未找到pandoc命令，请安装pandoc: brew install pandoc")
        except Exception as e:
            self.logger.error(f"pandoc转换异常: {e}")
            raise Exception(f"pandoc转换失败: {e}")

    def is_supported_format(self, file_extension: str) -> bool:
        """
        检查是否为pandoc支持的格式
        
        Args:
            file_extension: 文件扩展名
            
        Returns:
            是否支持
        """
        supported_formats = ['.docx', '.odt', '.rtf', '.csv', '.epub']
        return file_extension.lower() in supported_formats 