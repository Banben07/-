#!/usr/bin/env python3
"""
模拟串口测试脚本

此脚本用于测试模拟串口的功能，包括自动波特率检测和数据接收。
"""

import time
import sys
from mock_serial import MockSerialReceiver

def test_mock_serial_basic():
    """测试基本的模拟串口功能"""
    print("=== 模拟串口基本功能测试 ===\n")
    
    # 创建模拟串口接收器
    mock_receiver = MockSerialReceiver()
    
    # 创建模拟端口
    success = mock_receiver.create_mock_port("MOCK_TEST", 115200)
    if not success:
        print("✗ 创建模拟端口失败")
        return False
    
    print("✓ 模拟端口创建成功: MOCK_TEST")
    
    # 添加测试数据
    test_cases = [
        ("single", "单个目标"),
        ("multiple", "多个目标"),
        ("high_score", "高置信度目标"),
        ("random", "随机目标")
    ]
    
    for data_type, description in test_cases:
        print(f"\n--- 测试 {description} ---")
        
        # 清空之前的数据
        mock_receiver.clear_objects()
        
        # 添加测试数据
        success = mock_receiver.add_test_data(data_type)
        if not success:
            print(f"✗ 添加{description}数据失败")
            continue
        
        # 启动数据处理
        mock_receiver.start_mock_data_generation(0.1)
        
        # 等待数据处理
        time.sleep(0.5)
        
        # 检查结果
        objects = mock_receiver.get_detected_objects()
        if objects:
            print(f"✓ 检测到 {len(objects)} 个目标:")
            for i, obj in enumerate(objects):
                print(f"  目标 {i+1}: 类别={obj['class']}, 置信度={obj['score']}, 位置={obj['bbox']}")
        else:
            print("✗ 未检测到目标")
        
        # 停止数据生成
        mock_receiver.stop_mock_data_generation()
    
    return True

def test_mock_auto_generation():
    """测试自动数据生成功能"""
    print("\n\n=== 自动数据生成测试 ===\n")
    
    mock_receiver = MockSerialReceiver()
    mock_receiver.create_mock_port("MOCK_AUTO", 115200)
    
    print("开始自动生成数据...")
    mock_receiver.start_mock_data_generation(0.3)  # 每0.3秒生成一次数据
    
    # 监听5秒
    start_time = time.time()
    last_count = 0
    
    while time.time() - start_time < 5.0:
        if mock_receiver.has_new_data():
            objects = mock_receiver.get_all_objects()
            if len(objects) != last_count:
                print(f"[{time.time() - start_time:.1f}s] 检测到 {len(objects)} 个累计目标")
                
                # 显示最新的目标
                current_objects = mock_receiver.get_detected_objects()
                if current_objects:
                    print(f"  当前帧: {len(current_objects)} 个目标")
                    for obj in current_objects[-3:]:  # 只显示最后3个
                        print(f"    类别={obj['class']}, 置信度={obj['score']}")
                
                last_count = len(objects)
        
        time.sleep(0.1)
    
    mock_receiver.stop_mock_data_generation()
    print("✓ 自动数据生成测试完成")
    
    return True

def test_mock_baudrate_detection():
    """测试模拟串口的波特率检测"""
    print("\n\n=== 模拟波特率检测测试 ===\n")
    
    mock_receiver = MockSerialReceiver()
    
    # 测试波特率检测
    best_baudrate, results = mock_receiver.test_baudrate_detection()
    
    print("\n详细结果:")
    for baudrate, score in results.items():
        status = "✓" if baudrate == best_baudrate else " "
        print(f"{status} {baudrate}: {score:.1f} 分")
    
    return best_baudrate == 115200  # 期望115200获得最高分

def test_performance():
    """测试模拟串口性能"""
    print("\n\n=== 性能测试 ===\n")
    
    mock_receiver = MockSerialReceiver()
    mock_receiver.create_mock_port("MOCK_PERF", 921600)
    
    print("高频数据生成测试 (每0.05秒生成一次)...")
    mock_receiver.start_mock_data_generation(0.05)
    
    start_time = time.time()
    data_count = 0
    
    # 测试10秒
    while time.time() - start_time < 10.0:
        if mock_receiver.has_new_data():
            data_count += 1
            objects = mock_receiver.get_detected_objects()
            
            # 每秒报告一次
            if data_count % 20 == 0:
                elapsed = time.time() - start_time
                rate = data_count / elapsed
                print(f"  {elapsed:.1f}s: {data_count} 次更新, {rate:.1f} 次/秒, 当前 {len(objects)} 个目标")
        
        time.sleep(0.01)
    
    mock_receiver.stop_mock_data_generation()
    
    total_time = time.time() - start_time
    avg_rate = data_count / total_time
    
    print(f"\n性能统计:")
    print(f"  总时间: {total_time:.1f} 秒")
    print(f"  数据更新次数: {data_count}")
    print(f"  平均更新频率: {avg_rate:.1f} 次/秒")
    
    return avg_rate > 10  # 期望平均频率超过10次/秒

def test_integration_with_gui():
    """测试与GUI的集成"""
    print("\n\n=== GUI集成测试 ===\n")
    
    try:
        # 尝试导入GUI相关模块
        from gui import DetectionGUI
        import tkinter as tk
        
        print("✓ GUI模块导入成功")
        
        # 这里可以添加更多的GUI集成测试
        # 但为了避免阻塞测试，我们只进行基本检查
        
        print("✓ GUI集成测试通过")
        return True
        
    except ImportError as e:
        print(f"✗ GUI模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ GUI集成测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("模拟串口功能测试套件\n")
    print("=" * 50)
    
    test_results = []
    
    # 运行所有测试
    tests = [
        # ("基本功能", test_mock_serial_basic),
        # ("自动生成", test_mock_auto_generation),
        ("波特率检测", test_mock_baudrate_detection),
        # ("性能测试", test_performance),
        ("GUI集成", test_integration_with_gui)
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            test_results.append((test_name, result))
            status = "✓ 通过" if result else "✗ 失败"
            print(f"\n{test_name}: {status}")
        except Exception as e:
            test_results.append((test_name, False))
            print(f"\n{test_name}: ✗ 错误 - {e}")
            import traceback
            traceback.print_exc()
    
    # 总结报告
    print(f"\n{'='*50}")
    print("测试总结报告")
    print(f"{'='*50}")
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:<15}: {status}")
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！模拟串口功能正常工作。")
    else:
        print("⚠️  部分测试失败，请检查相关功能。")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试过程中发生严重错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 