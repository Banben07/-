import time
import threading
import random
from queue import Queue

class MockSerial:
    """模拟串口类，用于测试"""
    def __init__(self, port=None, baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.is_open = False
        self.in_waiting = 0
        self.data_buffer = bytearray()
        self.lock = threading.Lock()
        self.auto_generate = False
        self.generate_thread = None
        self.stop_generate = False
    
    def open(self):
        """打开模拟串口"""
        self.is_open = True
        return True
    
    def close(self):
        """关闭模拟串口"""
        self.is_open = False
        self.stop_auto_generate()
    
    def read(self, size=1):
        """读取指定大小的数据"""
        with self.lock:
            if not self.data_buffer:
                return b''
            
            if size >= len(self.data_buffer):
                data = bytes(self.data_buffer)
                self.data_buffer.clear()
                self.in_waiting = 0
                return data
            else:
                data = bytes(self.data_buffer[:size])
                self.data_buffer = self.data_buffer[size:]
                self.in_waiting = len(self.data_buffer)
                return data
    
    def write(self, data):
        """写入数据（模拟）"""
        return len(data)
    
    def reset_input_buffer(self):
        """清空输入缓冲区"""
        with self.lock:
            self.data_buffer.clear()
            self.in_waiting = 0
    
    def add_data(self, data):
        """添加模拟数据到缓冲区"""
        if isinstance(data, str):
            data = data.encode('ascii', errors='replace')
        
        with self.lock:
            self.data_buffer.extend(data)
            self.in_waiting = len(self.data_buffer)
    
    def start_auto_generate(self, interval=0.5):
        """开始自动生成测试数据"""
        if self.auto_generate:
            return
            
        self.auto_generate = True
        self.stop_generate = False
        self.generate_thread = threading.Thread(target=self._generate_data_loop, args=(interval,), daemon=True)
        self.generate_thread.start()
    
    def stop_auto_generate(self):
        """停止自动生成数据"""
        self.auto_generate = False
        self.stop_generate = True
        if self.generate_thread:
            self.generate_thread.join(timeout=1.0)
    
    def _generate_data_loop(self, interval):
        """数据生成循环"""
        while self.auto_generate and not self.stop_generate:
            # 生成随机的目标检测数据
            test_data = self._generate_detection_data()
            self.add_data(test_data)
            time.sleep(interval)
    
    def _generate_detection_data(self):
        """生成模拟的目标检测数据"""
        # 随机生成1-3个目标
        num_objects = random.randint(1, 3)
        data_parts = []
        
        for _ in range(num_objects):
            obj_class = random.randint(0, 5)
            score = random.randint(60, 99)
            
            # 生成合理的边界框坐标
            x1 = random.randint(0, 200)
            y1 = random.randint(0, 200)
            x2 = x1 + random.randint(20, 55)
            y2 = y1 + random.randint(20, 55)
            
            # 确保坐标在255范围内
            x2 = min(x2, 255)
            y2 = min(y2, 255)
            
            obj_data = f"class:{obj_class}\nscore:{score}\nbbox:{x1}\nbbox:{y1}\nbbox:{x2}\nbbox:{y2}\n"
            data_parts.append(obj_data)
        
        return "".join(data_parts)

class MockSerialReceiver:
    """集成了模拟串口的接收器，用于测试"""
    def __init__(self):
        from serial_receive import SerialReceiver
        self.serial_receiver = SerialReceiver()
        self.mock_serial = None
        
    def create_mock_port(self, port_name="MOCK_PORT", baudrate=115200):
        """创建模拟串口"""
        self.mock_serial = MockSerial(port=port_name, baudrate=baudrate)
        # 替换串口接收器的串口对象
        self.serial_receiver.serial = self.mock_serial
        self.serial_receiver.port = port_name
        self.serial_receiver.baudrate = baudrate
        return True
    
    def start_mock_data_generation(self, interval=0.5):
        """开始生成模拟数据"""
        if self.mock_serial:
            self.mock_serial.open()
            self.mock_serial.start_auto_generate(interval)
            self.serial_receiver.start_receiving()
            return True
        return False
    
    def stop_mock_data_generation(self):
        """停止生成模拟数据"""
        if self.mock_serial:
            self.mock_serial.stop_auto_generate()
            self.serial_receiver.disconnect()
    
    def add_test_data(self, data_type="random"):
        """添加特定类型的测试数据"""
        if not self.mock_serial:
            return False
            
        if data_type == "single":
            # 单个目标
            test_data = "class:1\nscore:85\nbbox:50\nbbox:60\nbbox:100\nbbox:120\n"
        elif data_type == "multiple":
            # 多个目标
            test_data = """class:0\nscore:95\nbbox:20\nbbox:30\nbbox:80\nbbox:90\n
class:2\nscore:75\nbbox:150\nbbox:50\nbbox:200\nbbox:100\n
class:1\nscore:88\nbbox:100\nbbox:150\nbbox:140\nbbox:200\n"""
        elif data_type == "high_score":
            # 高置信度目标
            test_data = "class:0\nscore:98\nbbox:10\nbbox:10\nbbox:50\nbbox:50\n"
        else:  # random
            test_data = self.mock_serial._generate_detection_data()
        
        self.mock_serial.add_data(test_data)
        return True
    
    def get_detected_objects(self):
        """获取检测到的目标"""
        return self.serial_receiver.get_detected_objects()
    
    def get_all_objects(self):
        """获取所有目标"""
        return self.serial_receiver.get_all_objects()
    
    def has_new_data(self):
        """检查是否有新数据"""
        return self.serial_receiver.has_new_data()
    
    def clear_objects(self):
        """清空目标数据"""
        self.serial_receiver.clear_objects()
    
    def test_baudrate_detection(self):
        """测试波特率检测功能"""
        print("=== 模拟串口波特率检测测试 ===\n")
        
        # 创建模拟串口
        self.create_mock_port("MOCK_TEST_PORT", 115200)
        
        # 模拟不同波特率的数据质量
        test_results = {}
        
        for baudrate in [9600, 115200, 230400]:
            print(f"模拟测试波特率: {baudrate}")
            
            # 模拟该波特率下的数据
            self.mock_serial.baudrate = baudrate
            self.mock_serial.open()
            
            # 添加测试数据
            if baudrate == 115200:
                # 115200时数据质量最好
                test_data = """class:1\nscore:95\nbbox:10\nbbox:20\nbbox:50\nbbox:60\n
class:2\nscore:88\nbbox:100\nbbox:110\nbbox:140\nbbox:150\n"""
            elif baudrate == 9600:
                # 9600时数据质量中等
                test_data = "class:0\nscore:75\nbbox:30\nbbox:40\nbbox:70\nbbox:80\n"
            else:
                # 其他波特率数据质量较差
                test_data = "class:1\nscore:65\n"  # 不完整的数据
            
            self.mock_serial.add_data(test_data)
            
            # 评估数据质量
            score = self.serial_receiver._evaluate_data_quality([test_data])
            test_results[baudrate] = score
            print(f"  质量评分: {score}")
            
            self.mock_serial.close()
        
        # 找出最佳波特率
        best_baudrate = max(test_results, key=test_results.get)
        print(f"\n✓ 检测到最佳波特率: {best_baudrate} (评分: {test_results[best_baudrate]})")
        
        return best_baudrate, test_results

class MockSerialTools:
    """模拟serial.tools.list_ports模块"""
    class ComPort:
        def __init__(self, device):
            self.device = device
    
    @staticmethod
    def comports():
        """返回模拟的串口列表"""
        return [
            MockSerialTools.ComPort("COM1"),
            MockSerialTools.ComPort("COM2"),
            MockSerialTools.ComPort("/dev/ttyUSB0"),
            MockSerialTools.ComPort("/dev/ttyS0"),
            MockSerialTools.ComPort("MOCK1"),  # 特殊的模拟串口
            MockSerialTools.ComPort("MOCK2")   # 特殊的模拟串口
        ]

def patch_serial():
    """模拟serial模块，用于测试"""
    import sys
    
    # 创建模拟的serial模块
    class MockSerialModule:
        Serial = MockSerial
        SerialException = Exception
        
        class tools:
            list_ports = MockSerialTools
    
    # 替换系统中的serial模块
    sys.modules['serial'] = MockSerialModule()
    sys.modules['serial.tools'] = MockSerialModule.tools
    sys.modules['serial.tools.list_ports'] = MockSerialTools

if __name__ == "__main__":
    # 测试代码
    mock_serial = patch_serial()
    
    # 创建模拟串口
    ser = MockSerial("MOCK1")
    ser.open()
    
    # 添加一些测试数据
    ser.add_data("class:0\nscore:95\nbbox:20\nbbox:30\nbbox:100\nbbox:150\n")
    
    # 读取数据
    data = ser.read(ser.in_waiting)
    print(f"读取到的数据: {data.decode('ascii')}")
    
    # 列出可用串口
    ports = MockSerialTools.comports()
    print(f"可用串口: {[port.device for port in ports]}") 