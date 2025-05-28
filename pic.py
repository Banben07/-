import os
import numpy as np
from PIL import Image, ImageDraw

class ImageProcessor:
    def __init__(self):
        self.image = None
        self.original_image = None
        self.width = 256
        self.height = 256
    
    def load_image(self, image_path=None):
        """加载图像，如果没有指定路径则创建一个空白图像"""
        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                # 调整图像大小为256x256
                img = img.resize((self.width, self.height))
                self.original_image = img.copy()
                self.image = img
                return True
            except Exception as e:
                print(f"加载图像失败: {e}")
                return False
        else:
            # 创建空白图像
            self.image = Image.new('RGB', (self.width, self.height), color=(255, 255, 255))
            self.original_image = self.image.copy()
            return True
    
    def create_blank_image(self):
        """创建空白图像"""
        self.image = Image.new('RGB', (self.width, self.height), color=(255, 255, 255))
        self.original_image = self.image.copy()
        return self.image
    
    def reset_image(self):
        """重置图像到原始状态"""
        if self.original_image:
            self.image = self.original_image.copy()
            return True
        return False
    
    def draw_boxes(self, objects, class_colors=None):
        """在图像上绘制检测框
        
        Args:
            objects: 对象列表，每个对象包含class, score, bbox信息
            class_colors: 类别对应的颜色字典
        """
        if self.image is None:
            self.create_blank_image()
        
        # 复制原图，在副本上绘制
        image_with_boxes = self.image.copy()
        draw = ImageDraw.Draw(image_with_boxes)
        
        # 默认颜色映射
        if class_colors is None:
            class_colors = {
                0: (255, 0, 0),  # 红色
                1: (0, 255, 0),  # 绿色
                2: (0, 0, 255),  # 蓝色
                3: (255, 255, 0),  # 黄色
                4: (255, 0, 255),  # 紫色
                5: (0, 255, 255),  # 青色
            }
        
        # 遍历绘制每个检测框
        for obj in objects:
            try:
                obj_class = obj['class']
                score = obj['score']
                xmin, ymin, xmax, ymax = obj['bbox']
                
                # 确保坐标在图像范围内，并转换为整数
                xmin = max(0, min(int(xmin), self.width - 1))
                ymin = max(0, min(int(ymin), self.height - 1))
                xmax = max(0, min(int(xmax), self.width - 1))
                ymax = max(0, min(int(ymax), self.height - 1))
                
                # 额外检查，确保坐标都是有效数字
                for i, coord in enumerate([xmin, ymin, xmax, ymax]):
                    if not isinstance(coord, int) or coord < 0:
                        if i == 0: xmin = 0
                        if i == 1: ymin = 0
                        if i == 2: xmax = self.width - 1
                        if i == 3: ymax = self.height - 1
                        print(f"修复无效坐标: 索引 {i}, 值 {coord} -> {[xmin, ymin, xmax, ymax][i]}")
                
                # 确保xmax > xmin和ymax > ymin
                if xmax <= xmin:
                    xmax = xmin + 1
                if ymax <= ymin:
                    ymax = ymin + 1
                
                # 确保所有坐标都是整数
                xmin, ymin, xmax, ymax = int(xmin), int(ymin), int(xmax), int(ymax)
                    
                # 打印调试信息
                print(f"绘制边界框: ({xmin},{ymin},{xmax},{ymax})")
                
                # 获取该类别的颜色
                color = class_colors.get(obj_class, (255, 0, 0))
                
                # 绘制矩形框
                draw.rectangle([xmin, ymin, xmax, ymax], outline=color, width=2)
                
                # 绘制类别标签，不显示置信度
                label = f"Class:{obj_class}"
                label_size = draw.textlength(label)
                
                # 标签背景框
                draw.rectangle(
                    [xmin, ymin, xmin + label_size + 10, ymin + 15],
                    fill=color
                )
                
                # 标签文本
                draw.text((xmin + 5, ymin), label, fill=(255, 255, 255))
            except Exception as e:
                print(f"绘制检测框错误 - {e}，边界框: {obj.get('bbox', '未知')}")
        
        return image_with_boxes
    
    def save_image(self, output_path):
        """保存图像到指定路径"""
        if self.image:
            try:
                self.image.save(output_path)
                return True
            except Exception as e:
                print(f"保存图像失败: {e}")
        return False
    
    def get_image(self):
        """获取当前图像"""
        return self.image
    
    def set_image(self, image):
        """设置当前图像"""
        self.image = image

# 测试代码
if __name__ == "__main__":
    processor = ImageProcessor()
    processor.create_blank_image()
    
    # 测试数据
    test_objects = [
        {'class': 0, 'score': 95, 'bbox': (20, 30, 100, 150)},
        {'class': 1, 'score': 85, 'bbox': (150, 50, 220, 200)}
    ]
    
    result = processor.draw_boxes(test_objects)
    result.show()  # 显示测试结果
