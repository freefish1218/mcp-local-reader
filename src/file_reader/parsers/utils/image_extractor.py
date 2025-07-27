"""
Office文档图片提取器
提供从Excel、PowerPoint等Office文档中提取图片的功能
"""

import os
from typing import List, Optional

from ...utils import get_logger


class OfficeImageExtractor:
    """Office文档图片提取器"""

    def __init__(self):
        """初始化图片提取器"""
        self.logger = get_logger("image_extractor")

    def extract_excel_images(self, file_path: str, temp_image_dir: str) -> None:
        """
        提取Excel文件中的图片
        
        Args:
            file_path: Excel文件路径
            temp_image_dir: 临时图片保存目录
        """
        try:
            self.logger.info(f"开始提取Excel图片: {file_path}")
            
            try:
                from openpyxl import load_workbook
                from openpyxl.drawing.image import Image as OpenpyxlImage
            except ImportError:
                self.logger.warning("openpyxl库未安装，无法提取Excel图片")
                return
            
            try:
                workbook = load_workbook(file_path, data_only=False)
                image_count = 0
                
                for sheet_idx, sheet in enumerate(workbook.worksheets):
                    sheet_name = sheet.title or f"Sheet{sheet_idx + 1}"
                    self.logger.debug(f"检查工作表图片: {sheet_name}")
                    
                    # 获取工作表中的图片
                    if hasattr(sheet, '_images') and sheet._images:
                        for img_idx, image in enumerate(sheet._images):
                            try:
                                # 生成图片文件名
                                img_filename = f"excel_s{sheet_idx}_i{img_idx}.png"
                                img_path = os.path.join(temp_image_dir, img_filename)
                                
                                # 保存图片数据
                                with open(img_path, 'wb') as img_file:
                                    # 获取图片数据
                                    if hasattr(image, '_data'):
                                        img_file.write(image._data())
                                    elif hasattr(image, 'image') and hasattr(image.image, 'fp'):
                                        image.image.fp.seek(0)
                                        img_file.write(image.image.fp.read())
                                    else:
                                        self.logger.warning(f"无法获取图片数据: {img_filename}")
                                        continue
                                
                                image_count += 1
                                self.logger.debug(f"保存Excel图片: {img_filename}")
                                
                            except Exception as e:
                                self.logger.warning(f"保存Excel图片失败: sheet={sheet_name}, img={img_idx}, 错误: {e}")
                                continue
                
                if image_count > 0:
                    self.logger.info(f"成功提取Excel图片: {image_count} 个")
                else:
                    self.logger.debug("Excel文件中未找到图片")
                    
            except Exception as e:
                self.logger.warning(f"Excel图片提取失败: {e}")
                
        except Exception as e:
            self.logger.error(f"Excel图片提取异常: {e}")

    def extract_pptx_image(self, shape, slide_idx: int, img_idx: int, temp_image_dir: str) -> Optional[str]:
        """
        从PowerPoint形状中提取图片
        
        Args:
            shape: PowerPoint图片形状
            slide_idx: 幻灯片索引（从0开始）
            img_idx: 图片索引（从0开始）
            temp_image_dir: 临时图片保存目录
            
        Returns:
            图片的Markdown引用字符串，失败返回None
        """
        try:
            # 生成图片文件名
            img_filename = f"pptx_sl{slide_idx}_i{img_idx}.png"
            img_path = os.path.join(temp_image_dir, img_filename)
            
            # 获取图片数据
            image = shape.image
            image_bytes = image.blob
            
            # 保存图片文件
            with open(img_path, 'wb') as img_file:
                img_file.write(image_bytes)
            
            self.logger.debug(f"保存PowerPoint图片: {img_filename}")
            
            # 返回图片的临时引用（会被后续处理替换为resource_id）
            return f"![图片]({img_filename})"
            
        except Exception as e:
            self.logger.warning(f"提取PowerPoint图片失败: slide={slide_idx}, img={img_idx}, 错误: {e}")
            return None

    def extract_pptx_images_from_slide(self, slide, slide_idx: int, temp_image_dir: str) -> List[str]:
        """
        从PowerPoint幻灯片中提取所有图片
        
        Args:
            slide: PowerPoint幻灯片对象
            slide_idx: 幻灯片索引
            temp_image_dir: 临时图片保存目录
            
        Returns:
            图片引用列表
        """
        slide_images = []
        
        if not temp_image_dir:
            return slide_images
        
        try:
            from pptx.enum.shapes import MSO_SHAPE_TYPE
            
            for shape in slide.shapes:
                if hasattr(shape, 'shape_type') and shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    img_ref = self.extract_pptx_image(shape, slide_idx, len(slide_images), temp_image_dir)
                    if img_ref:
                        slide_images.append(img_ref)
                        
        except ImportError:
            self.logger.warning("python-pptx库未安装，无法提取PowerPoint图片")
        except Exception as e:
            self.logger.warning(f"从幻灯片提取图片失败: slide={slide_idx}, 错误: {e}")
        
        return slide_images


class PowerPointTextAnalyzer:
    """PowerPoint文本分析器，用于判断文本格式"""

    @staticmethod
    def is_title_text(shape, text: str) -> bool:
        """判断是否为标题文本"""
        try:
            # 检查形状类型和位置来判断是否为标题
            if hasattr(shape, 'placeholder_format'):
                if shape.placeholder_format.type in [1, 2]:  # 标题或副标题
                    return True
            
            # 简单的文本特征判断
            if len(text) < 100 and '\n' not in text:
                return True
                
        except:
            pass
        return False

    @staticmethod
    def is_bullet_text(text: str) -> bool:
        """判断是否为项目符号文本"""
        lines = text.split('\n')
        if len(lines) > 1:
            # 多行文本，可能是列表
            bullet_chars = ['•', '·', '-', '*', '○']
            for line in lines[:3]:  # 检查前3行
                stripped = line.strip()
                if stripped and any(stripped.startswith(char) for char in bullet_chars):
                    return True
        return False 