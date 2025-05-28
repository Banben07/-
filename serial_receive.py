import serial
import time
import queue
from threading import Thread, Lock, Event
import re

class SerialReceiver:
    def __init__(self, port=None, baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.is_running = False
        self.data_buffer = ""
        self.object_data = []
        self.all_objects = []  # 存储所有收到的目标，而不仅是最新的
        self.data_lock = Lock()
        self.new_data_available = False  # 标记是否有新数据
        self.data_queue = queue.Queue(maxsize=100000)  # 数据队列，用于分离接收和处理
        self.process_event = Event()  # 用于触发处理线程
        
        # 自适应波特率相关配置
        self.common_baudrates = [1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 56000, 57600, 115200, 128000, 230400, 256000, 460800, 921600, 1000000, 1500000, 2000000, 3000000]
        self.auto_detect_baudrate = False
        self.detected_baudrate = None
        
        # 混合检测方案配置
        self.detection_methods = ['hardware_timing', 'software_quality']  # 检测方法优先级
        self.hardware_detection_enabled = True
        self.timing_samples = []  # 存储时序测量样本
        self.detection_results = {}  # 存储各种方法的检测结果
        
    def detect_baudrate(self, port=None, test_duration=2.0):
        """
        混合波特率检测方法
        优先使用硬件时序检测，失败时回退到软件质量评估
        
        Args:
            port: 串口端口，如果为None则使用self.port
            test_duration: 每个波特率的测试时间（秒）
            
        Returns:
            int: 检测到的波特率，如果检测失败返回None
        """
        if port:
            self.port = port
        
        if not self.port:
            raise ValueError("未指定串口端口")
        
        print("开始混合波特率检测...")
        self.detection_results = {}
        
        # 方法1: 硬件时序检测
        if self.hardware_detection_enabled and 'hardware_timing' in self.detection_methods:
            print("\n=== 尝试硬件时序检测 ===")
            try:
                hw_baudrate, hw_confidence, hw_results = self._hardware_timing_detection(
                    self.port, test_duration * 0.5  # 硬件检测用一半时间
                )
                
                self.detection_results['hardware_timing'] = {
                    'baudrate': hw_baudrate,
                    'confidence': hw_confidence,
                    'details': hw_results,
                    'method': 'hardware_timing'
                }
                
                # 如果硬件检测置信度足够高，直接使用结果
                if hw_confidence >= 0.7:  # 70%以上置信度
                    print(f"✓ 硬件时序检测成功: {hw_baudrate} (置信度: {hw_confidence:.2f})")
                    self.detected_baudrate = hw_baudrate
                    return hw_baudrate
                else:
                    print(f"⚠ 硬件时序检测置信度较低: {hw_confidence:.2f}")
                    
            except Exception as e:
                print(f"✗ 硬件时序检测失败: {e}")
                self.detection_results['hardware_timing'] = {
                    'error': str(e),
                    'method': 'hardware_timing'
                }
        
        # 方法2: 软件质量评估（原有方法）
        if 'software_quality' in self.detection_methods:
            print("\n=== 使用软件质量评估 ===")
            try:
                sw_baudrate = self._software_quality_detection(self.port, test_duration)
                
                if sw_baudrate:
                    print(f"✓ 软件质量评估检测: {sw_baudrate}")
                    
                    # 如果有硬件检测结果，进行比较
                    if 'hardware_timing' in self.detection_results:
                        hw_result = self.detection_results['hardware_timing']
                        if 'baudrate' in hw_result and hw_result['baudrate']:
                            # 混合决策：考虑两种方法的结果
                            final_baudrate = self._hybrid_decision(hw_result, sw_baudrate)
                            print(f"✓ 混合决策结果: {final_baudrate}")
                            self.detected_baudrate = final_baudrate
                            return final_baudrate
                    
                    # 只有软件检测结果
                    self.detected_baudrate = sw_baudrate
                    return sw_baudrate
                    
            except Exception as e:
                print(f"✗ 软件质量评估失败: {e}")
        
        print("✗ 所有检测方法都失败")
        return None
    
    def _software_quality_detection(self, port, test_duration):
        """
        软件质量评估检测方法（原有方法）
        
        Args:
            port: 串口端口
            test_duration: 测试时间
            
        Returns:
            int: 检测到的波特率
        """
        print("开始软件质量评估检测...")
        
        best_baudrate = None
        best_score = 0
        
        for baudrate in self.common_baudrates:
            print(f"测试波特率: {baudrate}")
            
            try:
                # 尝试使用当前波特率连接
                test_serial = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=0.1  # 短超时时间用于快速检测
                )
                
                # 清空输入缓冲区
                test_serial.reset_input_buffer()
                
                # 收集数据样本
                data_samples = []
                start_time = time.time()
                
                while time.time() - start_time < test_duration:
                    if test_serial.in_waiting > 0:
                        try:
                            data = test_serial.read(test_serial.in_waiting).decode('ascii', errors='replace')
                            data_samples.append(data)
                        except Exception:
                            pass
                    time.sleep(0.05)  # 50ms间隔
                
                test_serial.close()
                
                # 评估数据质量
                score = self._evaluate_data_quality(data_samples)
                print(f"波特率 {baudrate} 的质量分数: {score}")
                
                if score > best_score:
                    best_score = score
                    best_baudrate = baudrate
                    
            except Exception as e:
                print(f"测试波特率 {baudrate} 时出错: {e}")
                continue
        
        return best_baudrate if best_score > 0 else None
    
    def _hybrid_decision(self, hw_result, sw_baudrate):
        """
        混合决策：结合硬件时序检测和软件质量评估的结果
        
        Args:
            hw_result: 硬件检测结果
            sw_baudrate: 软件检测波特率
            
        Returns:
            int: 最终决定的波特率
        """
        hw_baudrate = hw_result.get('baudrate')
        hw_confidence = hw_result.get('confidence', 0.0)
        
        print(f"混合决策分析:")
        print(f"  硬件检测: {hw_baudrate} (置信度: {hw_confidence:.2f})")
        print(f"  软件检测: {sw_baudrate}")
        
        # 决策规则
        if hw_confidence >= 0.5:  # 硬件检测有一定置信度
            if hw_baudrate == sw_baudrate:
                # 两种方法结果一致，置信度最高
                print("  决策：两种方法结果一致，采用该结果")
                return hw_baudrate
            else:
                # 结果不一致，倾向于硬件检测（更精确）
                if hw_confidence >= 0.6:
                    print("  决策：硬件检测置信度较高，采用硬件结果")
                    return hw_baudrate
                else:
                    print("  决策：硬件检测置信度不够，采用软件结果")
                    return sw_baudrate
        else:
            # 硬件检测置信度很低，使用软件检测结果
            print("  决策：硬件检测置信度过低，采用软件结果")
            return sw_baudrate
    
    def _evaluate_data_quality(self, data_samples):
        """
        评估接收到的数据质量 - 通用版本
        
        Args:
            data_samples: 数据样本列表
            
        Returns:
            float: 质量分数 (0-100)
        """
        if not data_samples:
            return 0
        
        combined_data = ''.join(data_samples)
        
        if not combined_data:
            return 0
        
        score = 0
        
        # 1. 数据量评分 (最高40分) - 提高权重
        # 数据越多表示通信越稳定
        data_length_score = min(len(combined_data) / 50, 40)  # 50字符以上给满分
        score += data_length_score
        
        # 2. 可打印字符比例评分 (最高40分) - 提高权重  
        # 可打印字符比例越高表示数据传输质量越好
        printable_chars = sum(1 for c in combined_data if 32 <= ord(c) <= 126 or c in '\r\n\t')
        printable_ratio = printable_chars / len(combined_data) if combined_data else 0
        printable_score = printable_ratio * 40
        score += printable_score
        
        # 3. 数据连续性和规律性评分 (最高20分)
        consistency_score = 0
        
        # 检查是否包含数字（很多串口应用都会传输数字）
        if re.search(r'\d+', combined_data):
            consistency_score += 8
        
        # 检查是否包含字母（表示有结构化数据）
        if re.search(r'[a-zA-Z]+', combined_data):
            consistency_score += 6
        
        # 检查是否有重复模式（如循环发送的数据）
        # 检测重复的字符或数字模式
        if len(combined_data) >= 4:
            # 简单检测：是否有重复的2字符模式
            for i in range(len(combined_data) - 3):
                pattern = combined_data[i:i+2]
                if pattern in combined_data[i+2:]:
                    consistency_score += 3
                    break
            
        # 检查换行符的存在（表示结构化数据）
        if '\n' in combined_data or '\r' in combined_data:
            consistency_score += 3
        
        score += min(consistency_score, 20)
        
        return min(score, 100)  # 确保不超过100分
        
    def connect_with_auto_detect(self, port=None, test_duration=2.0):
        """
        使用自动波特率检测连接串口
        
        Args:
            port: 串口端口
            test_duration: 每个波特率的测试时间
            
        Returns:
            bool: 连接是否成功
        """
        if port:
            self.port = port
            
        # 首先尝试检测波特率
        detected_baudrate = self.detect_baudrate(self.port, test_duration)
        
        if detected_baudrate:
            # 使用检测到的波特率连接
            old_baudrate = self.baudrate
            self.baudrate = detected_baudrate
            
            if self.connect():
                print(f"使用检测到的波特率 {detected_baudrate} 连接成功")
                self.auto_detect_baudrate = True
                return True
            else:
                # 如果连接失败，恢复原波特率
                self.baudrate = old_baudrate
                print(f"使用检测到的波特率 {detected_baudrate} 连接失败")
        
        # 如果自动检测失败，尝试使用默认波特率连接
        print(f"使用默认波特率 {self.baudrate} 连接")
        return self.connect()
        
    def connect(self, port=None):
        """连接到指定的串口"""
        if port:
            self.port = port
        
        if not self.port:
            raise ValueError("未指定串口端口")
            
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            return True
        except Exception as e:
            print(f"串口连接失败: {e}")
            return False
    
    def get_connection_info(self):
        """获取连接信息，包括混合检测的详细结果"""
        if self.serial and self.serial.is_open:
            info = {
                'port': self.port,
                'baudrate': self.baudrate,
                'timeout': self.timeout,
                'auto_detected': self.auto_detect_baudrate,
                'detected_baudrate': self.detected_baudrate,
                'detection_methods': self.detection_methods,
                'detection_results': self.detection_results
            }
            return info
        return None
    
    def get_detection_summary(self):
        """获取检测方法的摘要信息"""
        if not self.detection_results:
            return "未进行检测"
        
        summary = []
        
        for method, result in self.detection_results.items():
            if method == 'hardware_timing':
                if 'error' in result:
                    summary.append(f"硬件时序检测: 失败 ({result['error']})")
                else:
                    summary.append(f"硬件时序检测: {result['baudrate']} (置信度: {result['confidence']:.2f})")
            elif method == 'software_quality':
                summary.append(f"软件质量评估: {result.get('baudrate', '失败')}")
        
        return "; ".join(summary)
    
    def disconnect(self):
        """断开串口连接"""
        self.is_running = False
        time.sleep(0.2)  # 给线程一些时间来清理
        
        if self.serial and self.serial.is_open:
            self.serial.close()
            
    def list_ports(self):
        """列出所有可用的串口"""
        from serial.tools import list_ports
        return [port.device for port in list_ports.comports()]
    
    def start_receiving(self):
        """开始接收数据的线程"""
        if not self.serial or not self.serial.is_open:
            return False
            
        self.is_running = True
        
        # 启动数据接收线程 - 只负责接收数据并放入队列
        Thread(target=self._receive_thread, daemon=True).start()
        
        # 启动数据处理线程 - 负责处理队列中的数据
        Thread(target=self._process_thread, daemon=True).start()
        
        return True
        
    def _receive_thread(self):
        """接收数据的线程 - 仅负责从串口读取数据并放入队列"""
        reconnect_delay = 1.0  # 初始重连延迟时间（秒）
        max_reconnect_delay = 5.0  # 最大重连延迟
        
        while self.is_running:
            try:
                # 检查串口是否连接并打开
                if not self.serial or not self.serial.is_open:
                    time.sleep(reconnect_delay)
                    try:
                        # 尝试重新连接
                        if self.serial and not self.serial.is_open:
                            self.serial.open()
                            print("串口重新连接成功")
                            reconnect_delay = 1.0  # 重置重连延迟
                    except Exception as e:
                        # 连接失败，增加重连延迟时间（指数退避）
                        reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
                        print(f"串口重连失败: {e}, 将在 {reconnect_delay:.1f} 秒后重试")
                    continue
                
                # 读取数据
                if self.serial.in_waiting:
                    try:
                        # 一次读取所有可用数据，减少读取次数
                        received_data = self.serial.read(self.serial.in_waiting).decode('ascii', errors='replace')
                        
                        # 放入队列，不阻塞，如果队列满则丢弃最早的数据
                        try:
                            if not self.data_queue.full():
                                self.data_queue.put_nowait(received_data)
                                self.process_event.set()  # 通知处理线程有新数据
                            else:
                                # 队列满了，打印警告并丢弃数据
                                print("警告: 数据接收缓冲区已满，部分数据将被丢弃")
                                # 清空队列的一半数据，以便接收新数据
                                for _ in range(self.data_queue.qsize() // 2):
                                    try:
                                        self.data_queue.get_nowait()
                                    except queue.Empty:
                                        break
                                # 现在尝试添加新数据
                                self.data_queue.put_nowait(received_data)
                                self.process_event.set()
                                
                        except queue.Full:
                            pass  # 队列满，忽略此批数据
                            
                    except (serial.SerialException, OSError) as e:
                        if "句柄无效" in str(e) or "Handle is invalid" in str(e):
                            # 跳过句柄无效错误，尝试下次循环重新连接
                            print("串口句柄无效，将尝试重新连接...")
                            if self.serial:
                                try:
                                    self.serial.close()
                                except Exception:
                                    pass
                            time.sleep(reconnect_delay)
                            continue
                        else:
                            # 其他错误，打印信息
                            print(f"读取串口数据时出错: {e}")
                
                # 短暂休眠，避免过度读取
                time.sleep(0.001)  # 1ms的休眠，确保高速响应
                
            except Exception as e:
                error_msg = str(e)
                # 过滤掉句柄无效错误的重复打印
                if "句柄无效" not in error_msg and "Handle is invalid" not in error_msg:
                    print(f"接收线程出错: {e}")
                time.sleep(0.1)  # 出错后短暂休眠
                
    def _process_thread(self):
        """处理数据的线程 - 负责处理队列中的数据"""
        reprocess_timer = 0  # 用于定期重新处理缓冲区的计时器
        
        while self.is_running:
            try:
                # 等待新数据或超时
                self.process_event.wait(timeout=0.2)
                self.process_event.clear()
                
                # 处理队列中的所有数据
                data_chunks = []
                
                # 提取队列中的所有数据
                while not self.data_queue.empty():
                    try:
                        chunk = self.data_queue.get_nowait()
                        data_chunks.append(chunk)
                        self.data_queue.task_done()
                    except queue.Empty:
                        break
                
                # 如果有数据，则处理
                if data_chunks:
                    combined_data = ''.join(data_chunks)
                    self._process_data(combined_data)
                
                # 定期重新检查缓冲区中的数据，以防有未完成的对象
                reprocess_timer += 1
                if reprocess_timer >= 50:  # 每50个周期重新处理一次
                    reprocess_timer = 0
                    with self.data_lock:
                        if self.data_buffer:
                            # 重新处理缓冲区中的数据
                            self._reprocess_buffer()
                
            except Exception as e:
                print(f"处理线程出错: {e}")
                time.sleep(0.1)
                
    def _reprocess_buffer(self):
        """重新处理缓冲区中的数据，尝试找到完整的对象"""
        pattern = r'class:(\d+)\s*\n*score:(\d+)\s*\n*bbox:(\d+)\s*\n*bbox:(\d+)\s*\n*bbox:(\d+)\s*\n*bbox:(\d+)'
        matches = re.finditer(pattern, self.data_buffer)
        
        found_match = False
        for match in matches:
            found_match = True
        
        if not found_match:
            # 检查数据缓冲区是否包含部分模式匹配
            partial_patterns = [
                r'class:\d+', 
                r'score:\d+', 
                r'bbox:\d+'
            ]
            
            has_partial_match = False
            for partial in partial_patterns:
                if re.search(partial, self.data_buffer):
                    has_partial_match = True
                    break
            
            # 如果没有部分模式匹配或缓冲区过大，则清理缓冲区
            if (not has_partial_match and len(self.data_buffer) > 1024000000) or len(self.data_buffer) > 4096000000:
                # 查找最后一个可能是有效开始的位置
                last_class_pos = self.data_buffer.rfind('class:')
                
                if last_class_pos > 0:
                    # 保留最后一个可能的起始位置
                    self.data_buffer = self.data_buffer[last_class_pos:]
                    print(f"数据缓冲区已清理至最后一个有效位置，当前大小: {len(self.data_buffer)}")
                else:
                    # 完全清空缓冲区
                    self.data_buffer = ""
                    print("警告: 数据缓冲区已完全清空，未发现有效数据格式")
    
    def _process_data(self, data):
        """处理接收到的数据"""
        with self.data_lock:
            # 将新数据追加到缓冲区
            self.data_buffer += data
            
            # 查找完整的对象数据 - 使用更精确的正则表达式模式
            pattern = r'class:(\d+)\s*\n*score:(\d+)\s*\n*bbox:(\d+)\s*\n*bbox:(\d+)\s*\n*bbox:(\d+)\s*\n*bbox:(\d+)'
            
            try:
                # 使用finditer而不是findall，以便获取匹配的结束位置
                matches = list(re.finditer(pattern, self.data_buffer))
                
                if not matches:
                    # 如果数据缓冲区超过某个阈值但没有匹配，尝试主动清理
                    if len(self.data_buffer) > 2048000000:
                        # 查找最后一个可能的"class:"
                        last_class_pos = self.data_buffer.rfind('class:')
                        
                        if last_class_pos > 0:
                            # 清理到最后一个"class:"之前的所有内容
                            self.data_buffer = self.data_buffer[last_class_pos:]
                            print(f"数据缓冲区已清理，当前大小: {len(self.data_buffer)}")
                        else:
                            # 进一步检查有无数据格式标记
                            has_format_markers = any(marker in self.data_buffer for marker in ['class:', 'score:', 'bbox:'])
                            
                            # 如果没有任何格式标记，清空整个缓冲区
                            if not has_format_markers:
                                old_size = len(self.data_buffer)
                                self.data_buffer = ""
                                print(f"数据缓冲区已完全清空，大小从 {old_size} 字节减至 0 字节")
                    
                    return  # 没有找到匹配项
                
                # 临时存储所有检测到的新对象，稍后会进行处理
                new_detected_objects = []
                
                for match in matches:
                    try:
                        obj_class = int(match.group(1))
                        score = int(match.group(2))
                        x1 = int(match.group(3))
                        y1 = int(match.group(4))
                        x2 = int(match.group(5))
                        y2 = int(match.group(6))
                        
                        # 调试信息
                        print(f"匹配坐标: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
                        
                        # 确保坐标顺序正确（左上角和右下角）
                        xmin = min(x1, x2)
                        ymin = min(y1, y2)
                        xmax = max(x1, x2)
                        ymax = max(y1, y2)
                        
                        # 确保坐标有效值（防止相等）
                        if xmax == xmin:
                            xmax = xmin + 1
                        if ymax == ymin:
                            ymax = ymin + 1
                        
                        # 验证坐标合法性
                        if 0 <= xmin and xmax <= 255 and 0 <= ymin and ymax <= 255:
                            new_detected_objects.append({
                                'class': obj_class,
                                'score': score,
                                'bbox': (xmin, ymin, xmax, ymax)
                            })
                        else:
                            print(f"坐标超出有效范围，已忽略: ({x1}, {y1}, {x2}, {y2})")
                            
                    except ValueError as e:
                        print(f"数据转换错误: {e}")
                
                # 如果有新检测到的对象，需要与现有对象进行全局分析
                if new_detected_objects:
                    # 第一步：比较新对象间的关系，找出垂直连接的对象
                    # 创建一个连接图，记录哪些新对象应该合并
                    n = len(new_detected_objects)
                    connected = [[] for _ in range(n)]  # 记录每个对象连接的其他对象索引
                    
                    # 检查所有新对象两两之间的关系
                    for i in range(n):
                        for j in range(i+1, n):
                            obj1 = new_detected_objects[i]
                            obj2 = new_detected_objects[j]
                            
                            # 如果两个对象是同一类别，并且垂直方向上相邻
                            # if obj1['class'] == obj2['class'] and self._is_vertically_adjacent(obj1['bbox'], obj2['bbox']):
                            #     connected[i].append(j)
                            #     connected[j].append(i)
                            #     print(f"检测到垂直相邻框: {obj1['bbox']} 和 {obj2['bbox']}")
                    
                    # 第二步：根据连接关系合并对象
                    merged_objects = []  # 最终的合并结果
                    visited = [False] * n  # 记录已处理的对象
                    
                    for i in range(n):
                        if visited[i]:
                            continue
                            
                        # 如果这个对象没有连接到其他对象，直接添加
                        if not connected[i]:
                            merged_objects.append(new_detected_objects[i])
                            visited[i] = True
                            continue
                        
                        # 找出所有连接到这个对象的对象（包括间接连接）
                        group = []  # 存储所有连接的对象索引
                        queue = [i]  # BFS队列
                        
                        while queue:
                            current = queue.pop(0)
                            if visited[current]:
                                continue
                                
                            group.append(current)
                            visited[current] = True
                            
                            for neighbor in connected[current]:
                                if not visited[neighbor]:
                                    queue.append(neighbor)
                        
                        # 合并这个组中的所有对象
                        if len(group) > 1:
                            # 取所有边界框的并集
                            merged_box = self._merge_boxes([new_detected_objects[j]['bbox'] for j in group])
                            # 取最高置信度
                            merged_score = max(new_detected_objects[j]['score'] for j in group)
                            # 使用第一个对象的类别
                            merged_class = new_detected_objects[group[0]]['class']
                            
                            merged_obj = {
                                'class': merged_class,
                                'score': merged_score,
                                'bbox': merged_box
                            }
                            
                            merged_objects.append(merged_obj)
                            print(f"合并垂直相邻框组: {[new_detected_objects[j]['bbox'] for j in group]} 为 {merged_box}")
                        else:
                            # 只有一个对象，直接添加
                            merged_objects.append(new_detected_objects[group[0]])
                    
                    # 第三步：检查每个新合并的对象与现有对象的重叠情况
                    final_objects = []  # 最终保留的对象
                    objects_to_remove = []  # 需要从all_objects移除的索引
                    
                    for new_obj in merged_objects:
                        overlap_found = False
                        
                        for i, existing_obj in enumerate(self.all_objects):
                            # 检查重叠
                            if self._calculate_iou(new_obj['bbox'], existing_obj['bbox']) > 0.3:  # 降低阈值以检测更多重叠
                                objects_to_remove.append(i)
                                overlap_found = True
                                print(f"检测到重叠框，将用新框替换: 新框{new_obj['bbox']} vs 已有框{existing_obj['bbox']}")
                        
                        # 不管是否重叠，都添加新对象
                        final_objects.append(new_obj)
                    
                    # 移除被新框替换的旧对象
                    if objects_to_remove:
                        # 从大到小排序索引，以便从后向前删除不影响前面的索引
                        objects_to_remove = list(set(objects_to_remove))  # 去重
                        objects_to_remove.sort(reverse=True)
                        for idx in objects_to_remove:
                            if idx < len(self.all_objects):
                                old_obj = self.all_objects.pop(idx)
                                print(f"已移除旧框: {old_obj['bbox']}")
                    
                    # 将所有处理后的新对象添加到all_objects中
                    self.all_objects.extend(final_objects)
                    # 限制列表大小，防止内存泄漏
                    if len(self.all_objects) > 30:  # 保留最近的30个目标
                        self.all_objects = self.all_objects[-30:]
                    
                    # 更新当前帧检测到的对象
                    self.object_data = final_objects
                    self.new_data_available = True
                
                # 数据缓冲区过长时进行清理，避免占用过多内存
                if len(self.data_buffer) > 8192000000:  # 如果超过8KB
                    # 仅保留最后的一部分数据
                    self.data_buffer = self.data_buffer[-4096:]  # 保留最后4KB
                    print(f"数据缓冲区已清理，当前大小: {len(self.data_buffer)}")
            
            except Exception as e:
                print(f"解析数据错误: {e}")
                # 出现解析错误时，清理部分缓冲区防止错误累积
                if len(self.data_buffer) > 1024:
                    self.data_buffer = self.data_buffer[-512:]
    
    def _calculate_iou(self, box1, box2):
        """计算两个边界框的IoU（交并比）"""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        # 计算交集区域
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        # 检查是否有交集
        if inter_x_max <= inter_x_min or inter_y_max <= inter_y_min:
            return 0.0
            
        # 计算交集面积
        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        
        # 计算两个框的面积
        box1_area = (x1_max - x1_min) * (y1_max - y1_min)
        box2_area = (x2_max - x2_min) * (y2_max - y2_min)
        
        # 计算并集面积
        union_area = box1_area + box2_area - inter_area
        
        # 计算IoU
        iou = inter_area / union_area
        
        return iou
    
    def _calculate_vertical_overlap(self, box1, box2):
        """计算两个边界框在垂直方向上的重叠程度，即使它们在水平方向上分开"""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        # 计算高度（垂直方向尺寸）
        height1 = y1_max - y1_min
        height2 = y2_max - y2_min
        
        # 计算垂直方向上的重叠
        overlap_y_min = max(y1_min, y2_min)
        overlap_y_max = min(y1_max, y2_max)
        
        # 如果没有垂直重叠，返回0
        if overlap_y_max <= overlap_y_min:
            return 0.0
        
        # 计算重叠高度
        overlap_height = overlap_y_max - overlap_y_min
        
        # 计算与两个框高度中最小值的比例
        min_height = min(height1, height2)
        
        # 如果任一高度为0，返回0防止除零错误
        if min_height == 0:
            return 0.0
            
        return overlap_height / min_height
    
    def _is_box_adjacent(self, box1, box2, max_gap=5):
        """判断两个边界框是否相邻（上下相邻或左右相邻）"""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        # 检查x坐标是否重叠或相近
        x_overlap = (
            (x1_min <= x2_max and x1_max >= x2_min) or 
            (x2_min <= x1_max and x2_max >= x1_min) or
            (abs(x1_min - x2_min) <= max_gap and abs(x1_max - x2_max) <= max_gap)
        )
        
        # 检查y坐标是否相接或正好相连
        y_adjacent_or_connected = (
            # 正好相连的情况，如y1_max和y2_min是同一个值
            (y1_max == y2_min) or (y2_max == y1_min) or
            # 或者非常接近（在max_gap范围内）
            (abs(y1_max - y2_min) <= max_gap) or (abs(y2_max - y1_min) <= max_gap)
        )
        
        # 检查y坐标是否重叠
        y_overlap = (
            (y1_min <= y2_max and y1_max >= y2_min) or 
            (y2_min <= y1_max and y2_max >= y1_min)
        )
        
        # 检查x坐标是否相接
        x_adjacent = (
            (abs(x1_max - x2_min) <= max_gap) or 
            (abs(x2_max - x1_min) <= max_gap)
        )
        
        # 如果x坐标重叠或相近，且y坐标相接或连接，则认为是相邻框
        if x_overlap and y_adjacent_or_connected:
            return True
            
        # 或者，如果y坐标重叠，且x坐标相接，也认为是相邻框
        if y_overlap and x_adjacent:
            return True
            
        return False
    
    def _merge_adjacent_boxes(self, objects):
        """合并相邻的边界框"""
        if not objects:
            return []
            
        # 复制对象列表以防止修改原始数据
        objects_copy = objects.copy()
        merged_objects = []
        processed = [False] * len(objects_copy)
        
        for i in range(len(objects_copy)):
            if processed[i]:
                continue
                
            current_obj = objects_copy[i].copy()  # 复制对象
            processed[i] = True
            merged = False
            
            # 查找与当前对象相邻的其他对象
            for j in range(i+1, len(objects_copy)):
                if processed[j]:
                    continue
                    
                if (objects_copy[i]['class'] == objects_copy[j]['class'] and
                        self._is_box_adjacent(objects_copy[i]['bbox'], objects_copy[j]['bbox'])):
                    # 合并两个边界框
                    x1_min, y1_min, x1_max, y1_max = objects_copy[i]['bbox']
                    x2_min, y2_min, x2_max, y2_max = objects_copy[j]['bbox']
                    
                    # 取边界的并集
                    merged_bbox = (
                        min(x1_min, x2_min),
                        min(y1_min, y2_min),
                        max(x1_max, x2_max),
                        max(y1_max, y2_max)
                    )
                    
                    # 取较高的置信度
                    merged_score = max(objects_copy[i]['score'], objects_copy[j]['score'])
                    
                    # 更新当前对象
                    current_obj['bbox'] = merged_bbox
                    current_obj['score'] = merged_score
                    
                    processed[j] = True
                    merged = True
                    print(f"合并相邻框: {objects_copy[i]['bbox']} + {objects_copy[j]['bbox']} = {merged_bbox}")
            
            merged_objects.append(current_obj)
                    
        return merged_objects
    
    def get_detected_objects(self):
        """获取当前帧检测到的对象"""
        with self.data_lock:
            # 在返回之前进行最后一次相邻框检查，优先保留较低位置的框
            filtered_objects = self._filter_vertically_connected_boxes(self.object_data.copy())
            return filtered_objects
    
    def get_all_objects(self):
        """获取所有已检测到的对象"""
        with self.data_lock:
            # 在返回之前进行最后一次相邻框检查，优先保留较低位置的框
            filtered_objects = self._filter_vertically_connected_boxes(self.all_objects.copy())
            return filtered_objects
            
    def _filter_vertically_connected_boxes(self, objects):
        """过滤垂直方向上相连的框，只保留位置较低的那个"""
        if not objects or len(objects) <= 1:
            return objects
            
        # 首先按照x坐标排序，便于比较相似x坐标的框
        objects.sort(key=lambda obj: (obj['bbox'][0], obj['bbox'][1]))
        
        # 需要保留的索引和需要移除的索引
        to_keep = set(range(len(objects)))
        to_remove = set()
        
        # 两两比较所有框
        for i in range(len(objects)):
            if i in to_remove:
                continue
                
            for j in range(i+1, len(objects)):
                if j in to_remove:
                    continue
                    
                box1 = objects[i]['bbox']
                box2 = objects[j]['bbox']
                
                # 提取坐标
                x1_min, y1_min, x1_max, y1_max = box1
                x2_min, y2_min, x2_max, y2_max = box2
                
                # 检查x坐标是否足够相似 (允许一定的误差)
                x_similar = (abs(x1_min - x2_min) == 0 and abs(x1_max - x2_max) == 0)
                
                # 检查y坐标是否恰好相连或非常接近 (允许1像素的误差)
                y_connected = (abs(y1_max - y2_min) <= 1) or (abs(y2_max - y1_min) <= 1)
                
                # 如果x坐标相似且y坐标相连
                if x_similar and y_connected:
                    # 决定移除哪一个框 - 总是保留y坐标较大的那个（即下方的框）
                    if y1_max < y2_max:  # 如果框1在上，框2在下
                        print(f"垂直相连框筛选: 移除上方框 {box1}，保留下方框 {box2}")
                        to_remove.add(i)
                        break  # 找到要移除的框后，不再继续比较
                    else:  # 如果框2在上，框1在下
                        print(f"垂直相连框筛选: 移除上方框 {box2}，保留下方框 {box1}")
                        to_remove.add(j)
        
        # 构建过滤后的对象列表
        filtered_objects = [objects[i] for i in range(len(objects)) if i not in to_remove]
        
        return filtered_objects
    
    def clear_objects(self):
        """清空所有目标数据"""
        with self.data_lock:
            self.object_data = []
            self.all_objects = []
            self.data_buffer = ""  # 同时清空数据缓冲区
            
            # 清空队列
            while not self.data_queue.empty():
                try:
                    self.data_queue.get_nowait()
                    self.data_queue.task_done()
                except queue.Empty:
                    break
                    
            # 重置新数据标志，确保下一次有数据时会被识别为新数据
            self.new_data_available = False
            
            # 发送事件通知处理线程继续处理
            self.process_event.set()
            
            # 打印清除完成的消息，确认清除操作完成
            print("所有对象数据已清除，准备接收新数据")
            
    def restart_receiving(self):
        """重新启动接收过程，用于切换图片后恢复接收"""
        # 先清除所有已有数据
        self.clear_objects()
        
        # 检查串口连接状态
        if not self.serial or not self.serial.is_open:
            print("串口未连接或已关闭，尝试重新连接...")
            try:
                if self.serial and not self.serial.is_open:
                    self.serial.open()
                    print("串口已重新打开")
                elif not self.serial and self.port:
                    self.connect(self.port)
                    print(f"已重新连接到串口 {self.port}")
            except Exception as e:
                print(f"重新连接串口失败: {e}")
                return False
        
        # 检查线程运行状态
        if not self.is_running:
            print("重新启动接收线程...")
            self.start_receiving()
        else:
            # 如果线程已经在运行，只需激活处理
            self.process_event.set()
            print("接收线程已在运行，已重新激活数据处理")
        
        return True
    
    def has_new_data(self):
        """检查是否有新数据"""
        with self.data_lock:
            has_new = self.new_data_available
            self.new_data_available = False
            return has_new

    def _is_vertically_adjacent(self, box1, box2, max_gap=1):
        """判断两个边界框是否在垂直方向上相邻"""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        # 检查x坐标是否有足够重叠
        x_overlap = min(x1_max, x2_max) - max(x1_min, x2_min)
        box1_width = x1_max - x1_min
        box2_width = x2_max - x2_min
        min_width = min(box1_width, box2_width)
        
        # 如果x轴重叠部分超过最小宽度的50%，认为x轴足够重叠
        x_overlap_sufficient = x_overlap > min_width * 0.5
        
        # 检查y坐标是否相邻（一个框的底部是否接近另一个框的顶部）
        y_adjacent = abs(y1_max - y2_min) <= max_gap or abs(y2_max - y1_min) <= max_gap
        
        # 同时满足x重叠和y相邻的条件
        return x_overlap_sufficient and y_adjacent
                    
    def _merge_boxes(self, boxes):
        """合并多个边界框为一个"""
        if not boxes:
            return None
            
        # 取所有边界框的外接矩形
        xmin = min(box[0] for box in boxes)
        ymin = min(box[1] for box in boxes)
        xmax = max(box[2] for box in boxes)
        ymax = max(box[3] for box in boxes)
        
        return (xmin, ymin, xmax, ymax)

    def _hardware_timing_detection(self, port, test_duration=1.0):
        """
        硬件时序检测方法 - 通过分析ASCII字符'2'(0x32)的时序来检测波特率
        
        Args:
            port: 串口端口
            test_duration: 检测持续时间
            
        Returns:
            tuple: (检测到的波特率, 置信度, 详细结果)
        """
        print("开始硬件时序检测...")
        print("检测目标: ASCII字符'2' (0x32 = 00110010)")
        
        # 常见波特率对应的位时间 (微秒)
        baudrate_bit_times = {}
        for baudrate in self.common_baudrates:
            bit_time_us = 1000000 / baudrate  # 微秒
            baudrate_bit_times[baudrate] = bit_time_us
        
        timing_results = {}
        
        for baudrate in self.common_baudrates:
            print(f"测试波特率: {baudrate} (位时间: {baudrate_bit_times[baudrate]:.1f}μs)")
            
            try:
                # 创建测试串口连接
                test_serial = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=0.1
                )
                
                # 清空缓冲区
                test_serial.reset_input_buffer()
                
                # 收集ASCII字符'2'的时序样本
                timing_samples = self._collect_ascii2_timing_samples(test_serial, test_duration)
                
                test_serial.close()
                
                if timing_samples:
                    # 分析时序样本，计算置信度
                    confidence = self._analyze_ascii2_timing_samples(
                        timing_samples, 
                        baudrate_bit_times[baudrate]
                    )
                    timing_results[baudrate] = {
                        'confidence': confidence,
                        'samples': len(timing_samples),
                        'expected_bit_time': baudrate_bit_times[baudrate]
                    }
                    print(f"  样本数: {len(timing_samples)}, 置信度: {confidence:.2f}")
                else:
                    timing_results[baudrate] = {
                        'confidence': 0.0,
                        'samples': 0,
                        'expected_bit_time': baudrate_bit_times[baudrate]
                    }
                    print(f"  未检测到有效时序")
                
            except Exception as e:
                print(f"  测试波特率 {baudrate} 时出错: {e}")
                timing_results[baudrate] = {
                    'confidence': 0.0,
                    'samples': 0,
                    'error': str(e)
                }
        
        # 找出置信度最高的波特率
        best_baudrate = None
        best_confidence = 0.0
        
        for baudrate, result in timing_results.items():
            if result['confidence'] > best_confidence:
                best_confidence = result['confidence']
                best_baudrate = baudrate
        
        return best_baudrate, best_confidence, timing_results
    
    def _collect_ascii2_timing_samples(self, test_serial, duration):
        """
        收集ASCII字符'2'的时序样本
        
        Args:
            test_serial: 测试串口对象
            duration: 采样持续时间
            
        Returns:
            list: 时序样本列表 [(时间戳, 字符数据), ...]
        """
        import time
        
        samples = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            if test_serial.in_waiting > 0:
                # 记录接收时间戳和数据
                timestamp = time.time()
                try:
                    data = test_serial.read(test_serial.in_waiting)
                    if data:
                        # 检查是否包含ASCII字符'2'
                        for byte_val in data:
                            if byte_val == 0x32:  # ASCII '2'
                                samples.append((timestamp, chr(byte_val)))
                except Exception:
                    pass
            
            time.sleep(0.001)  # 1ms精度
        
        return samples
    
    def _analyze_ascii2_timing_samples(self, samples, expected_bit_time_us):
        """
        分析ASCII字符'2'的时序样本，计算与期望波特率的匹配度
        
        ASCII '2' = 0x32 = 00110010 (binary)
        串口帧格式: [起始位0][数据位00110010][停止位1]
        
        Args:
            samples: 时序样本
            expected_bit_time_us: 期望的位时间（微秒）
            
        Returns:
            float: 置信度 (0.0-1.0)
        """
        if len(samples) < 2:
            return 0.0
        
        # 计算样本间的时间间隔
        intervals = []
        for i in range(1, len(samples)):
            interval_s = samples[i][0] - samples[i-1][0]
            interval_us = interval_s * 1000000  # 转换为微秒
            intervals.append(interval_us)
        
        if not intervals:
            return 0.0
        
        # ASCII '2' (0x32) 的位模式分析
        # 二进制: 00110010
        # 完整帧: 起始(0) + 数据(00110010) + 停止(1)
        # 预期字符间隔应该是10位的倍数（考虑连续发送）
        
        confidence_scores = []
        
        for interval_us in intervals:
            # ASCII字符'2'的传输包含10位（起始位+8数据位+停止位）
            # 连续发送'2'时，间隔应该是10位时间的倍数
            expected_char_time = expected_bit_time_us * 10  # 单个字符时间
            
            # 检查间隔是否接近字符时间的整数倍
            best_match = 0.0
            for multiplier in [1, 2, 3, 4, 5]:  # 检查1-5个字符的间隔
                expected_interval = expected_char_time * multiplier
                error = abs(interval_us - expected_interval) / expected_interval
                match_score = max(0, 1.0 - error)
                best_match = max(best_match, match_score)
            
            confidence_scores.append(best_match)
        
        # 计算平均置信度
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            
            # 样本数量加权 - 更多样本提高置信度
            sample_weight = min(len(samples) / 5.0, 1.0)  # 降低样本要求
            
            # ASCII '2' 特定的置信度提升
            # 如果检测到规律的'2'字符，额外增加置信度
            if len(samples) >= 3:
                # 检查是否有规律的间隔模式
                if len(set(int(i/1000) for i in intervals[:3])) <= 2:  # 间隔相似（毫秒级精度）
                    avg_confidence *= 1.2  # 20%置信度奖励
            
            return min(avg_confidence * sample_weight, 1.0)
        
        return 0.0

# 测试代码
if __name__ == "__main__":
    receiver = SerialReceiver()
    available_ports = receiver.list_ports()
    print(f"可用串口: {available_ports}")
    
    if available_ports:
        receiver.connect(available_ports[0])
        receiver.start_receiving()
        
        try:
            while True:
                objects = receiver.get_detected_objects()
                if objects:
                    print(f"检测到 {len(objects)} 个对象:")
                    for obj in objects:
                        print(f"类别: {obj['class']}, 置信度: {obj['score']}, 边界框: {obj['bbox']}")
                time.sleep(0.5)
        except KeyboardInterrupt:
            receiver.disconnect()
            print("程序已退出")
