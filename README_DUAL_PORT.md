# 双端口串口功能使用指南

## 概述

本项目现在支持同时处理两个 UART 端口，允许您同时从两个串口设备接收和处理目标检测数据。这对于需要多传感器数据融合或多设备监控的场景非常有用。

## 主要功能

### 1. 多端口管理
- **MultiPortManager**: 核心多端口管理器类
- 支持最多2个端口同时连接
- 独立的端口配置和状态管理
- 自动数据合并和标识

### 2. 独立端口控制
- 每个端口可以独立设置波特率
- 支持独立的自动波特率检测
- 独立的连接/断开控制
- 独立的数据接收和处理

### 3. 数据融合显示
- 支持两个端口数据的合并显示
- 不同端口数据用不同颜色标识（端口1：红色，端口2：蓝色）
- 可选择性显示某个端口的数据
- 实时数据流显示

### 4. 图形界面支持
- **MultiPortGUI**: 专门的双端口图形界面
- 分栏式端口控制面板
- 标签页式数据显示
- 实时状态监控

## 快速开始

### 1. 启动双端口GUI

```bash
# 启动双端口图形界面
python gui.py --multi

# 或者直接运行测试脚本的GUI模式
python test_dual_port.py --gui
```

### 2. 编程方式使用

```python
from serial_receive import MultiPortManager

# 创建多端口管理器
port_manager = MultiPortManager(max_ports=2)

# 添加两个端口
port_manager.add_port("port1", "/dev/ttyUSB0", 115200, auto_detect=False)
port_manager.add_port("port2", "/dev/ttyUSB1", 115200, auto_detect=True)

# 连接所有端口
results = port_manager.connect_all_ports()

# 开始接收数据
port_manager.start_all_receiving()

# 获取合并的数据
while True:
    all_objects = port_manager.get_all_detected_objects()
    combined_objects = port_manager.get_combined_objects()
    
    # 处理数据...
    time.sleep(0.1)
```

## API 参考

### MultiPortManager 类

#### 基本方法

```python
# 初始化
manager = MultiPortManager(max_ports=2)

# 端口管理
manager.add_port(port_name, port_path, baudrate, auto_detect=False)
manager.remove_port(port_name)
manager.connect_port(port_name)
manager.disconnect_port(port_name)

# 批量操作
manager.connect_all_ports()
manager.disconnect_all_ports()
manager.start_all_receiving()
manager.stop_all_receiving()

# 数据获取
manager.get_all_detected_objects()  # 返回 {port_name: [objects]}
manager.get_combined_objects()      # 返回合并的对象列表
manager.get_port_status()          # 返回所有端口状态

# 工具方法
manager.clear_all_objects()
manager.restart_all_receiving()
manager.has_new_data_any_port()
```

#### 数据结构

**端口状态信息**:
```python
{
    'port1': {
        'port_path': '/dev/ttyUSB0',
        'baudrate': 115200,
        'connected': True,
        'auto_detect': False,
        'last_update': 1640995200.0,
        'object_count': 5,
        'total_objects': 100,
        'has_new_data': True
    },
    'port2': { ... }
}
```

**合并对象格式**:
```python
{
    'class': 0,
    'score': 95,
    'bbox': (20, 30, 100, 150),
    'source_port': 'port1',  # 来源端口标识
    'port_name': 'port1'     # 端口名称
}
```

### MultiPortGUI 类

#### 启动方式

```python
from gui import start_multi_port_gui

# 启动多端口GUI
start_multi_port_gui()
```

#### 界面功能

**控制面板**:
- 端口1设置：串口选择、波特率、自动检测
- 端口2设置：串口选择、波特率、自动检测
- 全局控制：连接所有、断开所有、清理数据
- 状态显示：实时状态信息
- 图像控制：加载图像、显示选项

**显示区域**:
- 图像显示：合并显示两个端口的检测结果
- 串口数据：分栏显示两个端口的原始数据

## 测试和演示

### 1. 功能测试

```bash
# 运行完整的双端口测试套件
python test_dual_port.py

# 运行带GUI演示的测试
python test_dual_port.py --gui
```

### 2. 模拟测试

如果没有真实的串口设备，可以使用模拟功能：

```python
from mock_serial import MockSerialReceiver

# 创建模拟串口
mock1 = MockSerialReceiver()
mock2 = MockSerialReceiver()

mock1.create_mock_port("MOCK_PORT_1", 115200)
mock2.create_mock_port("MOCK_PORT_2", 115200)

# 开始生成测试数据
mock1.start_mock_data_generation(0.5)
mock2.start_mock_data_generation(0.8)
```

### 3. 波特率检测测试

```python
# 测试双端口自动波特率检测
best_baudrate1, results1 = mock1.test_baudrate_detection()
best_baudrate2, results2 = mock2.test_baudrate_detection()
```

## 配置选项

### 端口配置

```python
# 端口1配置（红色显示）
port_configs = {
    'port1': {
        'name': '端口1',
        'color': 'red',
        'enabled': True
    },
    'port2': {
        'name': '端口2', 
        'color': 'blue',
        'enabled': True
    }
}
```

### 显示配置

- **显示端口1**: 控制是否显示端口1的检测结果
- **显示端口2**: 控制是否显示端口2的检测结果
- **合并显示**: 在同一图像上显示两个端口的结果
- **自动更新**: 自动刷新图像显示

## 使用场景

### 1. 多传感器融合
```python
# 使用两个摄像头或传感器
port_manager.add_port("camera1", "/dev/ttyUSB0", 115200)
port_manager.add_port("camera2", "/dev/ttyUSB1", 115200)

# 获取融合数据
combined_objects = port_manager.get_combined_objects()
```

### 2. 设备对比测试
```python
# 对比两个设备的检测结果
all_objects = port_manager.get_all_detected_objects()
port1_objects = all_objects.get('port1', [])
port2_objects = all_objects.get('port2', [])

# 分析差异...
```

### 3. 备份和冗余
```python
# 一个端口作为主要数据源，另一个作为备份
if not port_manager.get_receiver('port1').has_new_data():
    # 使用端口2的数据
    backup_objects = port_manager.get_all_detected_objects().get('port2', [])
```

## 注意事项

1. **端口冲突**: 确保两个端口使用不同的串口设备
2. **性能考虑**: 双端口同时接收会增加CPU使用率
3. **数据同步**: 不同端口的数据可能有时间差
4. **内存管理**: 及时清理不需要的历史数据
5. **错误处理**: 一个端口断开不会影响另一个端口

## 故障排除

### 常见问题

1. **端口无法连接**
   - 检查串口设备是否存在
   - 确认端口没有被其他程序占用
   - 验证波特率设置是否正确

2. **数据接收异常**
   - 检查设备是否正常发送数据
   - 尝试使用自动波特率检测
   - 查看状态信息中的错误消息

3. **GUI界面问题**
   - 确保所有依赖包已安装
   - 检查tkinter支持
   - 查看控制台错误信息

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看端口状态
status = port_manager.get_port_status()
print(f"端口状态: {status}")

# 检查数据流
if port_manager.has_new_data_any_port():
    print("有新数据可用")
```

## 扩展和定制

### 添加更多端口

虽然当前限制为2个端口，但可以轻松扩展：

```python
# 修改最大端口数
port_manager = MultiPortManager(max_ports=4)
```

### 自定义数据处理

```python
# 添加数据处理回调
def custom_data_handler(port_name, objects):
    print(f"端口 {port_name} 收到 {len(objects)} 个目标")

port_manager.add_update_callback(custom_data_handler)
```

### 自定义显示颜色

```python
# 修改端口显示颜色
port_configs['port1']['color'] = 'green'
port_configs['port2']['color'] = 'orange'
```

## 版本历史

- **v1.0**: 初始双端口支持
- **v1.1**: 添加自动波特率检测
- **v1.2**: 增强GUI界面
- **v1.3**: 添加模拟测试功能

## 许可证

本项目遵循 MIT 许可证。 