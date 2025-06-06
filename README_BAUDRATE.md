# 串口自动波特率检测功能说明

## 概述

`SerialReceiver` 类现在支持自动波特率检测功能，可以自动识别串口设备使用的波特率，无需手动配置。

## 功能特点

### 1. 自动波特率检测
- 支持常见波特率：9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600
- 基于数据质量评分算法选择最佳波特率
- 智能识别目标检测数据格式

### 2. 数据质量评估
系统通过以下指标评估数据质量：
- **数据量评分** (最高20分)：根据接收到的数据量评分
- **可打印字符比例** (最高30分)：ASCII可打印字符的比例
- **模式匹配评分** (最高50分)：
  - 检测关键词：`class:`, `score:`, `bbox:`
  - 完整模式匹配：`class:数字 score:数字 bbox:数字`
  - 数字模式识别

### 3. 多种连接方式
- **手动连接**：使用指定的波特率连接
- **自动连接**：启用自动检测并连接
- **混合模式**：先尝试自动检测，失败后使用默认波特率

## 使用方法

### 1. 代码中使用

#### 自动检测波特率
```python
from serial_receive import SerialReceiver

# 创建接收器实例
receiver = SerialReceiver()

# 方法1：仅检测波特率
detected_baudrate = receiver.detect_baudrate("/dev/ttyUSB0", test_duration=3.0)
if detected_baudrate:
    print(f"检测到波特率: {detected_baudrate}")

# 方法2：自动检测并连接
success = receiver.connect_with_auto_detect("/dev/ttyUSB0")
if success:
    print("自动连接成功")
    
    # 获取连接信息
    info = receiver.get_connection_info()
    print(f"使用波特率: {info['baudrate']}")
    print(f"是否自动检测: {info['auto_detected']}")
```

#### 手动指定波特率
```python
# 传统方式 - 手动指定波特率
receiver = SerialReceiver(baudrate=115200)
if receiver.connect("/dev/ttyUSB0"):
    print("手动连接成功")
```

### 2. GUI界面使用

#### 启用自动检测
1. 在"串口设置"区域勾选"自动检测"选项
2. 点击"连接"按钮开始自动检测
3. 或直接点击"自动连接"按钮（会自动启用检测）

#### 手动设置波特率
1. 取消勾选"自动检测"选项
2. 从下拉列表选择波特率
3. 点击"连接"按钮

## 参数配置

### detect_baudrate() 参数
- `port`: 串口端口路径
- `test_duration`: 每个波特率的测试时间（秒），默认2.0秒

### connect_with_auto_detect() 参数
- `port`: 串口端口路径  
- `test_duration`: 检测时间，默认2.0秒

## 最佳实践

### 1. 设备准备
- 确保串口设备已连接并正在发送数据
- 数据应包含目标检测相关信息（推荐包含 `class:`, `score:`, `bbox:` 关键词）
- 避免在检测过程中断开设备

### 2. 检测优化
- 对于高速数据传输，可以缩短 `test_duration`
- 对于低速或间歇性数据，可以延长 `test_duration`
- 如果已知大概的波特率范围，可以修改 `common_baudrates` 列表

### 3. 故障排除
- 如果检测失败，检查设备是否正在发送数据
- 尝试手动设置常见的波特率（9600, 115200）
- 检查串口权限和设备路径

## 技术细节

### 检测算法流程
1. 遍历预定义的波特率列表
2. 使用当前波特率连接串口
3. 收集指定时间内的数据样本
4. 计算数据质量评分
5. 选择评分最高的波特率

### 评分算法详细说明

#### 数据量评分
```python
data_length_score = min(len(combined_data) / 100, 20)
```
- 数据越多分数越高，最高20分
- 100字符可获得满分

#### 可打印字符比例评分
```python
printable_ratio = printable_chars / total_chars
printable_score = printable_ratio * 30
```
- 可打印字符比例越高分数越高
- 包括ASCII 32-126以及换行符、制表符

#### 模式匹配评分
- 关键词匹配：每个关键词10分
- 完整模式匹配：每个完整模式5分
- 数字存在：额外5分
- 最高总计50分

## 示例和测试

### 运行测试脚本
```bash
python test_baudrate_detection.py
```

测试脚本将执行：
- 自动波特率检测测试
- 自动连接测试
- 数据接收测试
- 手动波特率连接对比测试

### 预期输出示例
```
=== 串口自动波特率检测测试 ===

发现可用串口: ['/dev/ttyUSB0']

选择串口进行测试: /dev/ttyUSB0

--- 测试 1: 手动波特率检测 ---
开始自动检测波特率...
测试波特率: 9600
波特率 9600 的质量分数: 25.5
测试波特率: 19200
波特率 19200 的质量分数: 0
测试波特率: 115200
波特率 115200 的质量分数: 67.8
✓ 自动检测成功！检测到波特率: 115200

--- 测试 2: 自动连接测试 ---
正在尝试自动连接...
✓ 自动连接成功！
  端口: /dev/ttyUSB0
  波特率: 115200
  自动检测: 是
  检测到的波特率: 115200
```

## 兼容性说明

- 保持与现有代码的完全兼容性
- 所有原有的手动波特率设置方法继续有效
- 新功能为可选功能，不影响现有工作流程

## 注意事项

1. **性能影响**：自动检测需要额外时间（默认每个波特率2秒）
2. **数据依赖**：检测准确性取决于设备发送的数据质量
3. **设备兼容性**：某些特殊设备可能需要特定的波特率设置
4. **并发限制**：检测过程中会独占串口，其他应用无法同时访问 