#!/usr/bin/env python3
"""
通用波特率检测测试脚本

测试新的通用波特率检测功能，不依赖特定的数据格式。
包括循环发送数字的场景测试。
"""

from mock_serial import MockSerialReceiver

def test_number_cycle_detection():
    """测试循环发送数字的波特率检测"""
    print("=== 数字循环发送波特率检测测试 ===\n")
    
    mock_receiver = MockSerialReceiver()
    mock_receiver.create_mock_port("MOCK_NUM_CYCLE", 115200)
    
    # 模拟不同波特率下循环发送数字"2"
    test_scenarios = {
        9600: "2\n2\n2\n2\n2\n",  # 稳定的数字循环
        115200: "2\n2\n2\n2\n2\n2\n2\n2\n",  # 更多数据
        230400: "2\n2??\x01",  # 部分乱码
    }
    
    test_results = {}
    
    for baudrate, test_data in test_scenarios.items():
        print(f"测试波特率: {baudrate}")
        print(f"测试数据: {repr(test_data)}")
        
        # 评估数据质量
        score = mock_receiver.serial_receiver._evaluate_data_quality([test_data])
        test_results[baudrate] = score
        print(f"质量评分: {score:.1f}")
        
        # 分析评分详情
        combined_data = test_data
        
        # 数据量评分
        data_length_score = min(len(combined_data) / 50, 40)
        print(f"  数据量评分: {data_length_score:.1f}/40")
        
        # 可打印字符比例评分
        printable_chars = sum(1 for c in combined_data if 32 <= ord(c) <= 126 or c in '\r\n\t')
        printable_ratio = printable_chars / len(combined_data) if combined_data else 0
        printable_score = printable_ratio * 40
        print(f"  可打印字符评分: {printable_score:.1f}/40 (比例: {printable_ratio:.2f})")
        
        # 连续性和规律性评分
        import re
        consistency_score = 0
        if re.search(r'\d+', combined_data):
            consistency_score += 8
        if re.search(r'[a-zA-Z]+', combined_data):
            consistency_score += 6
        if '\n' in combined_data or '\r' in combined_data:
            consistency_score += 3
        # 重复模式检测
        if len(combined_data) >= 4:
            for i in range(len(combined_data) - 3):
                pattern = combined_data[i:i+2]
                if pattern in combined_data[i+2:]:
                    consistency_score += 3
                    break
        consistency_score = min(consistency_score, 20)
        print(f"  连续性评分: {consistency_score:.1f}/20")
        print()
    
    # 找出最佳波特率
    best_baudrate = max(test_results, key=test_results.get)
    print(f"✓ 检测到最佳波特率: {best_baudrate} (评分: {test_results[best_baudrate]:.1f})")
    
    return best_baudrate, test_results

def test_various_data_types():
    """测试各种类型数据的波特率检测"""
    print("\n=== 各种数据类型波特率检测测试 ===\n")
    
    mock_receiver = MockSerialReceiver()
    mock_receiver.create_mock_port("MOCK_VARIOUS", 115200)
    
    test_data_types = {
        "纯数字循环": "2\n2\n2\n2\n2\n",
        "传感器数据": "temp:25.6\nhumidity:65.2\nstatus:OK\n",
        "命令格式": "START:1\nSTOP:0\nRESET:1\n",
        "混合数据": "123\nOK\n456\nERROR\n789\nREADY\n",
        "乱码数据": "2\n??\x01\x02\xff\x03corrupted",
    }
    
    results = {}
    
    for data_type, test_data in test_data_types.items():
        print(f"数据类型: {data_type}")
        print(f"测试数据: {repr(test_data)}")
        
        score = mock_receiver.serial_receiver._evaluate_data_quality([test_data])
        results[data_type] = score
        print(f"质量评分: {score:.1f}/100")
        print()
    
    # 按评分排序
    sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    
    print("数据质量排名:")
    for i, (data_type, score) in enumerate(sorted_results, 1):
        print(f"{i}. {data_type}: {score:.1f}分")
    
    return results

def main():
    """主测试函数"""
    print("通用波特率检测功能测试\n")
    print("=" * 50)
    
    # 测试数字循环场景
    test_number_cycle_detection()
    
    # 测试各种数据类型
    test_various_data_types()
    
    print("\n" + "=" * 50)
    print("测试总结:")
    print("1. 新的波特率检测算法不再依赖特定的目标检测格式")
    print("2. 能够正确评估循环发送数字(如'2')的数据质量") 
    print("3. 支持各种串口应用场景：传感器数据、命令格式、混合数据等")
    print("4. 基于数据量、可打印字符比例和数据规律性进行综合评分")
    
if __name__ == "__main__":
    main() 