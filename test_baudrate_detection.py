#!/usr/bin/env python3
"""
自动波特率检测测试脚本

此脚本用于测试 SerialReceiver 类的自动波特率检测功能。
"""

import time
import sys
from serial_receive import SerialReceiver

def test_baudrate_detection():
    """测试自动波特率检测功能"""
    
    print("=== 串口自动波特率检测测试 ===\n")
    
    # 创建串口接收器实例
    receiver = SerialReceiver()
    
    # 获取可用串口
    ports = receiver.list_ports()
    
    if not ports:
        print("错误: 未找到可用的串口")
        return False
    
    print(f"发现可用串口: {ports}")
    
    # 选择第一个可用串口进行测试
    test_port = ports[0]
    print(f"\n选择串口进行测试: {test_port}")
    
    print("\n--- 测试 1: 手动波特率检测 ---")
    
    # 测试手动检测波特率
    detected_baudrate = receiver.detect_baudrate(test_port, test_duration=3.0)
    
    if detected_baudrate:
        print(f"✓ 自动检测成功！检测到波特率: {detected_baudrate}")
    else:
        print("✗ 未能自动检测到合适的波特率")
    
    print("\n--- 测试 2: 自动连接测试 ---")
    
    # 测试自动连接功能
    print("正在尝试自动连接...")
    success = receiver.connect_with_auto_detect(test_port, test_duration=2.0)
    
    if success:
        # 获取连接信息
        conn_info = receiver.get_connection_info()
        print(f"✓ 自动连接成功！")
        print(f"  端口: {conn_info['port']}")
        print(f"  波特率: {conn_info['baudrate']}")
        print(f"  自动检测: {'是' if conn_info['auto_detected'] else '否'}")
        print(f"  检测到的波特率: {conn_info['detected_baudrate']}")
        
        # 测试数据接收
        print("\n--- 测试 3: 数据接收测试 ---")
        print("开始接收数据 (5秒)...")
        
        receiver.start_receiving()
        
        start_time = time.time()
        last_object_count = 0
        
        while time.time() - start_time < 5.0:
            if receiver.has_new_data():
                objects = receiver.get_detected_objects()
                if objects and len(objects) != last_object_count:
                    print(f"  检测到 {len(objects)} 个目标")
                    for i, obj in enumerate(objects):
                        print(f"    目标 {i+1}: 类别={obj['class']}, 置信度={obj['score']}, 位置={obj['bbox']}")
                    last_object_count = len(objects)
            
            time.sleep(0.1)
        
        print("数据接收测试完成")
        
        # 断开连接
        receiver.disconnect()
        print("已断开连接")
        
    else:
        print("✗ 自动连接失败")
    
    print("\n--- 测试 4: 支持的波特率列表 ---")
    print(f"支持的波特率: {receiver.common_baudrates}")
    
    return success

def test_manual_connection():
    """测试手动波特率连接"""
    
    print("\n\n=== 手动波特率连接测试 ===\n")
    
    receiver = SerialReceiver()
    ports = receiver.list_ports()
    
    if not ports:
        print("错误: 未找到可用的串口")
        return False
    
    test_port = ports[0]
    
    # 测试常见的波特率
    test_baudrates = [9600, 115200, 19200, 38400, 57600]
    
    for baudrate in test_baudrates:
        print(f"测试波特率: {baudrate}")
        
        receiver.baudrate = baudrate
        
        if receiver.connect(test_port):
            print(f"✓ 波特率 {baudrate} 连接成功")
            
            # 简单测试数据接收
            receiver.start_receiving()
            time.sleep(1)
            
            objects = receiver.get_detected_objects()
            if objects:
                print(f"  接收到 {len(objects)} 个目标")
            else:
                print("  未接收到目标数据")
            
            receiver.disconnect()
            print(f"  已断开连接\n")
            
        else:
            print(f"✗ 波特率 {baudrate} 连接失败\n")

def main():
    """主函数"""
    
    print("串口自动波特率检测功能测试\n")
    print("请确保有串口设备连接并正在发送数据\n")
    
    try:
        # 测试自动检测
        auto_success = test_baudrate_detection()
        
        # 测试手动连接
        test_manual_connection()
        
        print("\n=== 测试总结 ===")
        if auto_success:
            print("✓ 自动波特率检测功能正常工作")
        else:
            print("✗ 自动波特率检测功能需要调试")
            
        print("\n建议:")
        print("1. 确保串口设备正在持续发送数据")
        print("2. 数据应包含目标检测相关的关键词 (class:, score:, bbox:)")
        print("3. 如果检测失败，请尝试手动设置波特率")
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 