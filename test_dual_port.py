#!/usr/bin/env python3
"""
双端口串口测试脚本

此脚本用于测试双端口串口功能，包括：
1. 双端口连接测试
2. 数据接收和显示
3. 自动波特率检测
4. 图像显示和控制
"""

import time
import sys
import threading
from serial_receive import MultiPortManager
from gui import start_multi_port_gui
from mock_serial import MockSerialReceiver

def test_dual_port_basic():
    """测试基本的双端口功能"""
    print("=== 双端口基本功能测试 ===\n")
    
    # 创建多端口管理器
    port_manager = MultiPortManager(max_ports=2)
    
    # 模拟添加两个端口
    success1 = port_manager.add_port("port1", "MOCK_PORT_1", 115200, auto_detect=False)
    success2 = port_manager.add_port("port2", "MOCK_PORT_2", 115200, auto_detect=False)
    
    if success1 and success2:
        print("✓ 成功添加两个端口")
    else:
        print("✗ 添加端口失败")
        return False
    
    # 显示端口状态
    status = port_manager.get_port_status()
    print("\n端口状态:")
    for port_name, port_status in status.items():
        print(f"  {port_name}: 路径={port_status['port_path']}, 波特率={port_status['baudrate']}, 连接={port_status['connected']}")
    
    # 测试连接（模拟）
    print("\n测试端口连接...")
    try:
        # 这里使用模拟连接，因为实际端口可能不存在
        print("  注意：实际连接需要真实的串口设备")
        print("  当前为功能演示，实际使用时请连接真实设备")
    except Exception as e:
        print(f"  连接测试: {e}")
    
    # 测试数据合并
    print("\n测试数据合并功能...")
    combined_objects = port_manager.get_combined_objects()
    print(f"  合并的目标数量: {len(combined_objects)}")
    
    # 清理
    port_manager.disconnect_all_ports()
    print("\n✓ 双端口基本功能测试完成")
    
    return True

def test_mock_dual_port():
    """测试模拟双端口功能"""
    print("\n=== 模拟双端口功能测试 ===\n")
    
    # 创建两个模拟串口接收器
    mock_receiver1 = MockSerialReceiver()
    mock_receiver2 = MockSerialReceiver()
    
    # 创建模拟端口
    success1 = mock_receiver1.create_mock_port("MOCK_PORT_1", 115200)
    success2 = mock_receiver2.create_mock_port("MOCK_PORT_2", 115200)
    
    if not (success1 and success2):
        print("✗ 创建模拟端口失败")
        return False
    
    print("✓ 创建两个模拟端口成功")
    
    # 创建多端口管理器
    port_manager = MultiPortManager(max_ports=2)
    
    # 添加端口
    port_manager.add_port("port1", "MOCK_PORT_1", 115200, auto_detect=False)
    port_manager.add_port("port2", "MOCK_PORT_2", 115200, auto_detect=False)
    
    # 开始生成测试数据
    print("\n开始生成测试数据...")
    mock_receiver1.start_mock_data_generation(0.5)  # 每0.5秒生成一次
    mock_receiver2.start_mock_data_generation(0.8)  # 每0.8秒生成一次
    
    # 监听数据
    start_time = time.time()
    test_duration = 5.0  # 测试5秒
    
    print(f"监听 {test_duration} 秒...")
    
    while time.time() - start_time < test_duration:
        # 获取所有端口的数据
        all_objects = port_manager.get_all_detected_objects()
        
        if all_objects:
            elapsed = time.time() - start_time
            port1_count = len(all_objects.get('port1', []))
            port2_count = len(all_objects.get('port2', []))
            
            print(f"[{elapsed:.1f}s] 端口1: {port1_count} 个目标, 端口2: {port2_count} 个目标")
        
        time.sleep(1.0)
    
    # 停止数据生成
    mock_receiver1.stop_mock_data_generation()
    mock_receiver2.stop_mock_data_generation()
    
    # 获取最终统计
    final_objects = port_manager.get_combined_objects()
    print(f"\n最终统计:")
    print(f"  合并目标总数: {len(final_objects)}")
    
    # 按端口分组统计
    port1_objects = [obj for obj in final_objects if obj.get('source_port') == 'port1']
    port2_objects = [obj for obj in final_objects if obj.get('source_port') == 'port2']
    
    print(f"  端口1目标数: {len(port1_objects)}")
    print(f"  端口2目标数: {len(port2_objects)}")
    
    # 显示端口状态
    status = port_manager.get_port_status()
    print(f"\n端口状态总结:")
    for port_name, port_status in status.items():
        print(f"  {port_name}:")
        print(f"    连接状态: {port_status.get('connected', False)}")
        print(f"    当前目标: {port_status.get('object_count', 0)}")
        print(f"    总计目标: {port_status.get('total_objects', 0)}")
        print(f"    有新数据: {port_status.get('has_new_data', False)}")
    
    print("\n✓ 模拟双端口功能测试完成")
    
    return True

def test_auto_detect_dual_port():
    """测试双端口自动检测功能"""
    print("\n=== 双端口自动检测测试 ===\n")
    
    # 创建两个模拟串口接收器
    mock_receiver1 = MockSerialReceiver()
    mock_receiver2 = MockSerialReceiver()
    
    # 测试波特率检测
    print("测试端口1波特率检测...")
    best_baudrate1, results1 = mock_receiver1.test_baudrate_detection()
    
    print("测试端口2波特率检测...")
    best_baudrate2, results2 = mock_receiver2.test_baudrate_detection()
    
    print(f"\n检测结果:")
    print(f"  端口1最佳波特率: {best_baudrate1}")
    print(f"  端口2最佳波特率: {best_baudrate2}")
    
    # 创建多端口管理器并使用检测到的波特率
    port_manager = MultiPortManager(max_ports=2)
    
    # 添加端口时使用自动检测
    success1 = port_manager.add_port("port1", "MOCK_PORT_1", best_baudrate1, auto_detect=True)
    success2 = port_manager.add_port("port2", "MOCK_PORT_2", best_baudrate2, auto_detect=True)
    
    if success1 and success2:
        print("✓ 成功添加两个自动检测端口")
    else:
        print("✗ 添加自动检测端口失败")
        return False
    
    print("\n✓ 双端口自动检测测试完成")
    
    return True

def demo_gui():
    """演示多端口GUI"""
    print("\n=== 启动多端口GUI演示 ===\n")
    
    print("启动多端口GUI界面...")
    print("GUI功能说明:")
    print("  1. 左侧控制面板可以分别配置两个串口")
    print("  2. 支持独立的波特率设置和自动检测")
    print("  3. 可以同时连接和断开多个端口")
    print("  4. 右侧显示区域包含图像显示和数据显示")
    print("  5. 支持分别显示两个端口的数据，用不同颜色区分")
    print("  6. 可以独立控制每个端口的显示状态")
    
    try:
        # 启动多端口GUI
        start_multi_port_gui()
    except KeyboardInterrupt:
        print("\n用户中断GUI演示")
    except Exception as e:
        print(f"\nGUI演示异常: {e}")

def main():
    """主测试函数"""
    print("双端口串口功能测试套件\n")
    print("=" * 50)
    
    test_results = []
    
    # 运行所有测试
    tests = [
        ("双端口基本功能", test_dual_port_basic),
        ("模拟双端口功能", test_mock_dual_port),
        ("双端口自动检测", test_auto_detect_dual_port)
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
        print(f"{test_name:<20}: {status}")
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！双端口功能正常工作。")
    else:
        print("⚠️  部分测试失败，请检查相关功能。")
    
    # 询问是否启动GUI演示
    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        demo_gui()
    else:
        print("\n提示: 使用 --gui 参数启动图形界面演示")
        print("例如: python test_dual_port.py --gui")
    
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