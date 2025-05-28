import sys
import time
import tkinter as tk
from threading import Thread

# 导入模拟串口模块
from mock_serial import patch_serial, MockSerialReceiver

# 在导入其他模块前先应用模拟串口补丁
mock_serial = patch_serial()

# 导入GUI模块
from gui import DetectionGUI

class TestDetectionApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("串口目标检测测试")
        
        # 创建GUI实例
        self.gui = DetectionGUI(self.root)
        
        # 替换SerialReceiver为MockSerialReceiver
        self.original_receiver = self.gui.serial_receiver
        self.mock_receiver = MockSerialReceiver()
        self.gui.serial_receiver = self.mock_receiver
        
        # 添加测试控制面板
        self.create_test_panel()
        
        # 设置关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_test_panel(self):
        """创建测试控制面板"""
        test_frame = tk.LabelFrame(self.root, text="测试控制")
        test_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        # 添加测试数据按钮
        add_object_button = tk.Button(
            test_frame, 
            text="添加目标数据", 
            command=lambda: self.add_test_data("object")
        )
        add_object_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        add_text_button = tk.Button(
            test_frame, 
            text="添加文本数据", 
            command=lambda: self.add_test_data("text")
        )
        add_text_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        add_random_button = tk.Button(
            test_frame, 
            text="添加随机数据", 
            command=lambda: self.add_test_data("random")
        )
        add_random_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 添加连续发送数据的控制
        self.continuous_var = tk.BooleanVar(value=False)
        continuous_check = tk.Checkbutton(
            test_frame, 
            text="连续发送", 
            variable=self.continuous_var,
            command=self.toggle_continuous_send
        )
        continuous_check.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 添加发送间隔控制
        tk.Label(test_frame, text="发送间隔(秒):").pack(side=tk.LEFT, padx=5, pady=5)
        
        self.interval_var = tk.StringVar(value="1.0")
        interval_entry = tk.Entry(test_frame, textvariable=self.interval_var, width=5)
        interval_entry.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 添加清空按钮
        clear_button = tk.Button(
            test_frame, 
            text="清空数据", 
            command=self.clear_data
        )
        clear_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 添加状态标签
        self.status_label = tk.Label(test_frame, text="就绪")
        self.status_label.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 连续发送线程
        self.continuous_thread = None
        self.is_sending = False
    
    def add_test_data(self, data_type):
        """添加测试数据"""
        if not self.mock_receiver.serial or not self.mock_receiver.serial.is_open:
            # 自动连接到模拟串口
            self.mock_receiver.connect("MOCK1")
            self.gui.connect_button.config(state=tk.DISABLED)
            self.gui.disconnect_button.config(state=tk.NORMAL)
            self.gui.port_combobox.config(state=tk.DISABLED)
            self.gui.baudrate_combobox.config(state=tk.DISABLED)
            self.mock_receiver.start_receiving()
            self.gui._start_serial_data_display()
            self.update_status(f"已连接到模拟串口 MOCK1")
        
        # 添加测试数据
        self.mock_receiver.add_test_data(data_type)
        self.update_status(f"已添加{data_type}类型的测试数据")
    
    def toggle_continuous_send(self):
        """切换连续发送状态"""
        if self.continuous_var.get():
            # 启动连续发送
            self.is_sending = True
            self.continuous_thread = Thread(target=self.continuous_send, daemon=True)
            self.continuous_thread.start()
            self.update_status("已启动连续发送")
        else:
            # 停止连续发送
            self.is_sending = False
            if self.continuous_thread:
                self.continuous_thread.join(0.5)
            self.update_status("已停止连续发送")
    
    def continuous_send(self):
        """连续发送测试数据的线程"""
        while self.is_sending:
            try:
                interval = float(self.interval_var.get())
                if interval < 0.1:
                    interval = 0.1
            except ValueError:
                interval = 1.0
            
            self.add_test_data("text")
            self.add_test_data("random")
            # self.add_test_data("object")
            time.sleep(interval)
    
    def clear_data(self):
        """清空测试数据"""
        if self.mock_receiver:
            self.mock_receiver.clear_objects()
            self.gui.last_data_length = 0
            self.gui.serial_data = []
            self.gui._update_receive_display()
            self.gui.box_processor.clear_boxes()
            self.gui._update_image()
            self.update_status("已清空所有测试数据")
    
    def update_status(self, message):
        """更新状态标签"""
        self.status_label.config(text=message)
        print(message)
    
    def on_closing(self):
        """关闭窗口时的处理"""
        # 停止连续发送
        self.is_sending = False
        if self.continuous_thread:
            self.continuous_thread.join(0.5)
        
        # 恢复原始接收器
        self.gui.serial_receiver = self.original_receiver
        
        # 关闭GUI
        self.gui.on_closing()
    
    def run(self):
        """运行测试应用"""
        self.root.mainloop()

def main():
    app = TestDetectionApp()
    app.run()

if __name__ == "__main__":
    main() 