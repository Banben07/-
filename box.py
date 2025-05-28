class BoxProcessor:
    def __init__(self):
        self.boxes = []
        self.classes = []
        self.scores = []
    
    def add_box(self, box_class, score, bbox):
        """添加一个检测框
        
        Args:
            box_class: 类别
            score: 置信度分数
            bbox: 边界框坐标 (xmin, ymin, xmax, ymax)
        """
        self.boxes.append(bbox)
        self.classes.append(box_class)
        self.scores.append(score)
    
    def clear_boxes(self):
        """清空所有检测框"""
        self.boxes = []
        self.classes = []
        self.scores = []
    
    def get_boxes(self):
        """获取所有检测框信息"""
        results = []
        for i in range(len(self.boxes)):
            results.append({
                'class': self.classes[i],
                'score': self.scores[i],
                'bbox': self.boxes[i]
            })
        return results
    
    def filter_by_score(self, min_score=50):
        """根据置信度过滤检测框
        
        Args:
            min_score: 最小置信度阈值
        """
        filtered_results = []
        for i in range(len(self.boxes)):
            if self.scores[i] >= min_score:
                filtered_results.append({
                    'class': self.classes[i],
                    'score': self.scores[i],
                    'bbox': self.boxes[i]
                })
        return filtered_results
    
    def filter_by_class(self, target_classes):
        """根据类别过滤检测框
        
        Args:
            target_classes: 目标类别列表
        """
        if not isinstance(target_classes, list):
            target_classes = [target_classes]
            
        filtered_results = []
        for i in range(len(self.boxes)):
            if self.classes[i] in target_classes:
                filtered_results.append({
                    'class': self.classes[i],
                    'score': self.scores[i],
                    'bbox': self.boxes[i]
                })
        return filtered_results
    
    def update_from_objects(self, objects):
        """从对象列表更新检测框
        
        Args:
            objects: 对象列表，每个对象包含class, score, bbox信息
        """
        self.clear_boxes()
        for obj in objects:
            self.add_box(
                obj['class'],
                obj['score'],
                obj['bbox']
            )
    
    def get_statistics(self):
        """获取检测框的统计信息"""
        stats = {
            'total': len(self.boxes),
            'classes': {}
        }
        
        for cls in self.classes:
            if cls not in stats['classes']:
                stats['classes'][cls] = 0
            stats['classes'][cls] += 1
            
        return stats

# 测试代码
if __name__ == "__main__":
    processor = BoxProcessor()
    
    # 添加测试数据
    processor.add_box(0, 95, (20, 30, 100, 150))
    processor.add_box(1, 85, (150, 50, 220, 200))
    processor.add_box(0, 75, (50, 100, 120, 180))
    processor.add_box(2, 65, (10, 10, 50, 50))
    
    # 测试获取所有框
    all_boxes = processor.get_boxes()
    print(f"总共的检测框: {len(all_boxes)}")
    
    # 测试按置信度过滤
    high_score_boxes = processor.filter_by_score(80)
    print(f"高置信度的检测框: {len(high_score_boxes)}")
    
    # 测试按类别过滤
    class0_boxes = processor.filter_by_class(0)
    print(f"类别0的检测框: {len(class0_boxes)}")
    
    # 测试统计信息
    stats = processor.get_statistics()
    print(f"统计信息: {stats}")
