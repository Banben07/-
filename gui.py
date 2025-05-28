import sys
import os
import time
from threading import Thread
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import serial

# 导入自定义模块
from serial_receive import SerialReceiver
from pic import ImageProcessor
from box import BoxProcessor

class DetectionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("串口目标检测显示器")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 初始化模块
        self.serial_receiver = SerialReceiver()
        self.image_processor = ImageProcessor()
        self.box_processor = BoxProcessor()
        
        # 创建空白图像
        self.image_processor.create_blank_image()
        
        # 界面刷新间隔(毫秒)
        self.update_interval = 100
        
        # 是否自动更新图像
        self.auto_update = True
        
        self.last_data_length = 0
        
        # 检测阈值
        self.score_threshold = 0
        
        # 测试数据
        self.test_objects = [
            {'class': 0, 'score': 95, 'bbox': (20, 30, 100, 150)},
            {'class': 1, 'score': 85, 'bbox': (150, 50, 220, 200)},
            {'class': 2, 'score': 75, 'bbox': (50, 180, 120, 240)},
            {'class': 0, 'score': 65, 'bbox': (180, 120, 230, 190)}
        ]
        
        # 缩放比例
        self.zoom_factor = 1.0
        
        # 串口收发数据
        self.serial_data = []
        
        # 初始化界面
        self._init_ui()
        
        # 启动更新线程
        self.is_running = True
        self.update_thread = Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
    
    def _init_ui(self):
        """初始化GUI界面"""
        # 创建主窗口框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 右侧显示区域
        display_frame = ttk.LabelFrame(main_frame, text="图像显示")
        display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 分割右侧区域为上下两部分
        self.upper_display = ttk.Frame(display_frame)
        self.upper_display.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        self.lower_display = ttk.LabelFrame(display_frame, text="串口数据")
        self.lower_display.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False, padx=0, pady=0, ipady=80)
        
        # 缩放控制区域
        zoom_frame = ttk.Frame(self.upper_display)
        zoom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(zoom_frame, text="缩放比例:").pack(side=tk.LEFT)
        
        self.zoom_out_button = ttk.Button(zoom_frame, text="-", width=2, command=self._zoom_out)
        self.zoom_out_button.pack(side=tk.LEFT, padx=5)
        
        self.zoom_label = ttk.Label(zoom_frame, text="100%")
        self.zoom_label.pack(side=tk.LEFT, padx=5)
        
        self.zoom_in_button = ttk.Button(zoom_frame, text="+", width=2, command=self._zoom_in)
        self.zoom_in_button.pack(side=tk.LEFT, padx=5)
        
        self.reset_zoom_button = ttk.Button(zoom_frame, text="重置", width=5, command=self._reset_zoom)
        self.reset_zoom_button.pack(side=tk.LEFT, padx=5)
        
        # 图像显示滚动区域
        self.image_canvas = tk.Canvas(self.upper_display, bg="white")
        self.image_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 串口设置部分
        serial_frame = ttk.LabelFrame(control_frame, text="串口设置")
        serial_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 串口选择
        ttk.Label(serial_frame, text="选择串口:").pack(anchor=tk.W, padx=5, pady=2)
        self.port_combobox = ttk.Combobox(serial_frame, width=15)
        self.port_combobox.pack(fill=tk.X, padx=5, pady=2)
        
        # 波特率设置
        baudrate_frame = ttk.Frame(serial_frame)
        baudrate_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(baudrate_frame, text="波特率:").pack(anchor=tk.W)
        
        baud_control_frame = ttk.Frame(baudrate_frame)
        baud_control_frame.pack(fill=tk.X)
        
        self.baudrate_combobox = ttk.Combobox(baud_control_frame, width=12)
        self.baudrate_combobox['values'] = ('1200', '2400', '4800', '9600', '14400', '19200', '28800', '38400', '56000', '57600', '115200', '128000', '230400', '256000', '460800', '921600', '1000000', '1500000', '2000000', '3000000')
        self.baudrate_combobox.current(3)  # 设置为9600
        self.baudrate_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 自动检测波特率选项
        self.auto_detect_var = tk.BooleanVar(value=False)
        self.auto_detect_check = ttk.Checkbutton(
            baud_control_frame, 
            text="自动检测", 
            variable=self.auto_detect_var,
            command=self._toggle_auto_detect
        )
        self.auto_detect_check.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 串口操作按钮
        button_frame = ttk.Frame(serial_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.refresh_button = ttk.Button(button_frame, text="刷新", command=self._refresh_ports)
        self.refresh_button.pack(side=tk.LEFT, padx=2)
        
        self.connect_button = ttk.Button(button_frame, text="连接", command=self._connect_serial)
        self.connect_button.pack(side=tk.LEFT, padx=2)
        
        self.auto_connect_button = ttk.Button(button_frame, text="自动连接", command=self._auto_connect_serial)
        self.auto_connect_button.pack(side=tk.LEFT, padx=2)
        
        self.disconnect_button = ttk.Button(button_frame, text="断开", command=self._disconnect_serial)
        self.disconnect_button.pack(side=tk.LEFT, padx=2)
        self.disconnect_button.config(state=tk.DISABLED)
        
        # 添加清理缓冲区按钮
        self.clear_buffer_button = ttk.Button(button_frame, text="清理缓冲区", command=self._clear_serial_buffer)
        self.clear_buffer_button.pack(side=tk.LEFT, padx=2)
        
        # 图像控制部分
        image_frame = ttk.LabelFrame(control_frame, text="图像控制")
        image_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 显示模式控制
        display_mode_frame = ttk.Frame(image_frame)
        display_mode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.show_image_var = tk.BooleanVar(value=False)  # 默认不显示图像区域
        self.show_image_check = ttk.Checkbutton(
            display_mode_frame, 
            text="显示图像区域", 
            variable=self.show_image_var,
            command=self._toggle_image_display
        )
        self.show_image_check.pack(side=tk.LEFT)
        
        # 加载图像按钮
        self.load_image_button = ttk.Button(image_frame, text="加载图像", command=self._load_image)
        self.load_image_button.pack(fill=tk.X, padx=5, pady=5)
        
        # 自动更新选项
        self.auto_update_var = tk.BooleanVar(value=True)
        self.auto_update_check = ttk.Checkbutton(
            image_frame, 
            text="自动更新", 
            variable=self.auto_update_var,
            command=self._toggle_auto_update
        )
        self.auto_update_check.pack(anchor=tk.W, padx=5, pady=5)
        
        # 手动更新按钮
        self.update_button = ttk.Button(image_frame, text="手动更新", command=self._update_image)
        self.update_button.pack(fill=tk.X, padx=5, pady=5)
        self.update_button.config(state=tk.DISABLED)
        
        # 保存图像按钮
        self.save_button = ttk.Button(image_frame, text="保存图像", command=self._save_image)
        self.save_button.pack(fill=tk.X, padx=5, pady=5)
        
        # 测试画框按钮
        self.test_button = ttk.Button(image_frame, text="测试画框", command=self._test_draw_boxes)
        self.test_button.pack(fill=tk.X, padx=5, pady=5)
        
        # 重启GUI按钮
        self.restart_button = ttk.Button(image_frame, text="重启GUI", command=self.restart_gui)
        self.restart_button.pack(fill=tk.X, padx=5, pady=5)
        
        # 检测信息显示
        info_frame = ttk.LabelFrame(control_frame, text="检测信息")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建文本框显示检测信息
        self.info_text = tk.Text(info_frame, width=30, height=10)
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 清空按钮
        self.clear_button = ttk.Button(info_frame, text="清空检测框", command=self._clear_boxes)
        self.clear_button.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建图像显示标签
        self.image_label = ttk.Label(self.image_canvas)
        self.canvas_image_id = self.image_canvas.create_window((0, 0), window=self.image_label, anchor=tk.CENTER)
        
        # 串口数据显示和发送区域
        serial_data_frame = ttk.Frame(self.lower_display)
        serial_data_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 垂直布局而非左右分割
        # 接收区域
        receive_frame = ttk.Frame(serial_data_frame)
        receive_frame.pack(fill=tk.BOTH, expand=True, padx=2)
        
        receive_label = ttk.Label(receive_frame, text="接收数据:")
        receive_label.pack(anchor=tk.W)
        
        self.receive_text = scrolledtext.ScrolledText(receive_frame, height=5, width=30)
        self.receive_text.pack(fill=tk.BOTH, expand=True)
        
        receive_controls = ttk.Frame(receive_frame)
        receive_controls.pack(fill=tk.X, pady=2)
        
        self.hex_display_var = tk.BooleanVar(value=False)
        hex_check = ttk.Checkbutton(receive_controls, text="十六进制显示", variable=self.hex_display_var)
        hex_check.pack(side=tk.LEFT)
        
        clear_receive_button = ttk.Button(receive_controls, text="清空", command=self._clear_receive)
        clear_receive_button.pack(side=tk.RIGHT)
        
        # 发送区域 - 一行高度
        send_frame = ttk.Frame(serial_data_frame)
        send_frame.pack(fill=tk.X, expand=False, padx=2, pady=5)
        
        send_label = ttk.Label(send_frame, text="发送数据:")
        send_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.send_entry = ttk.Entry(send_frame)
        self.send_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.hex_send_var = tk.BooleanVar(value=False)
        hex_send_check = ttk.Checkbutton(send_frame, text="HEX", variable=self.hex_send_var)
        hex_send_check.pack(side=tk.LEFT, padx=5)
        
        send_button = ttk.Button(send_frame, text="发送", command=self._send_data, width=8)
        send_button.pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 初始化串口下拉列表
        self._refresh_ports()
        
        # 初始显示空白图像
        self._update_image_display(self.image_processor.get_image())
        
        # 应用默认的图像显示设置（默认隐藏图像区域）
        self._toggle_image_display()
        
    def _refresh_ports(self):
        """刷新可用串口列表"""
        ports = self.serial_receiver.list_ports()
        self.port_combobox['values'] = ports
        if ports:
            self.port_combobox.current(0)
        self._update_status(f"发现 {len(ports)} 个可用串口")
    
    def _toggle_auto_detect(self):
        """切换自动检测波特率状态"""
        if self.auto_detect_var.get():
            # 启用自动检测时禁用波特率选择
            self.baudrate_combobox.config(state=tk.DISABLED)
            self._update_status("已启用自动波特率检测")
        else:
            # 禁用自动检测时恢复波特率选择
            self.baudrate_combobox.config(state=tk.NORMAL)
            self._update_status("已禁用自动波特率检测")
    
    def _connect_serial(self):
        """连接串口"""
        port = self.port_combobox.get()
        
        if not port:
            messagebox.showerror("错误", "请选择一个串口")
            return
        
        # 根据是否启用自动检测选择连接方式
        if self.auto_detect_var.get():
            # 使用自动检测波特率连接
            self._update_status("正在自动检测波特率...")
            self.connect_button.config(state=tk.DISABLED)
            self.auto_connect_button.config(state=tk.DISABLED)
            
            # 在后台线程中进行自动检测，避免阻塞UI
            Thread(target=self._auto_detect_and_connect, args=(port,), daemon=True).start()
        else:
            # 使用手动设置的波特率连接
            baudrate = int(self.baudrate_combobox.get())
            self.serial_receiver.baudrate = baudrate
            
            if self.serial_receiver.connect(port):
                self._connection_success(port, baudrate, auto_detected=False)
            else:
                messagebox.showerror("错误", f"无法连接到串口 {port}")
    
    def _auto_connect_serial(self):
        """自动连接串口（启用自动检测）"""
        port = self.port_combobox.get()
        
        if not port:
            messagebox.showerror("错误", "请选择一个串口")
            return
        
        # 启用自动检测
        self.auto_detect_var.set(True)
        self.baudrate_combobox.config(state=tk.DISABLED)
        
        # 连接串口
        self._connect_serial()
        
    def _auto_detect_and_connect(self, port):
        """在后台线程中进行自动检测和连接"""
        try:
            # 使用自动检测连接
            success = self.serial_receiver.connect_with_auto_detect(port)
            
            if success:
                # 获取连接信息
                conn_info = self.serial_receiver.get_connection_info()
                baudrate = conn_info['baudrate']
                auto_detected = conn_info['auto_detected']
                
                # 在主线程中更新UI
                self.root.after(0, lambda: self._connection_success(port, baudrate, auto_detected))
            else:
                # 连接失败
                self.root.after(0, lambda: self._connection_failed(port))
                
        except Exception as e:
            self.root.after(0, lambda: self._connection_error(port, str(e)))
    
    def _connection_success(self, port, baudrate, auto_detected=False):
        """连接成功后的UI更新"""
        detect_text = "自动检测" if auto_detected else "手动设置"
        self._update_status(f"已连接到 {port}, 波特率: {baudrate} ({detect_text})")
        
        # 更新波特率显示
        if auto_detected:
            # 更新下拉框显示检测到的波特率
            if str(baudrate) in self.baudrate_combobox['values']:
                self.baudrate_combobox.set(str(baudrate))
            else:
                # 如果检测到的波特率不在列表中，添加它
                current_values = list(self.baudrate_combobox['values'])
                current_values.append(str(baudrate))
                self.baudrate_combobox['values'] = current_values
                self.baudrate_combobox.set(str(baudrate))
        
        # 更新按钮状态
        self.connect_button.config(state=tk.DISABLED)
        self.auto_connect_button.config(state=tk.DISABLED)
        self.disconnect_button.config(state=tk.NORMAL)
        self.port_combobox.config(state=tk.DISABLED)
        self.auto_detect_check.config(state=tk.DISABLED)
        
        # 如果没有启用自动检测，禁用波特率选择
        if not auto_detected:
            self.baudrate_combobox.config(state=tk.DISABLED)
        
        # 开始接收数据
        self.serial_receiver.start_receiving()
        
        # 启动串口数据显示更新
        self._start_serial_data_display()
    
    def _connection_failed(self, port):
        """连接失败后的UI更新"""
        self._update_status(f"无法连接到串口 {port}")
        messagebox.showerror("连接失败", f"无法连接到串口 {port}")
        
        # 强制重置连接状态
        self._force_reset_connection_state()
    
    def _connection_error(self, port, error_msg):
        """连接错误后的UI更新"""
        self._update_status(f"连接 {port} 时发生错误: {error_msg}")
        messagebox.showerror("连接错误", f"连接 {port} 时发生错误:\n{error_msg}")
        
        # 强制重置连接状态
        self._force_reset_connection_state()
    
    def _disconnect_serial(self):
        """断开串口连接"""
        # 强制停止自动检测状态和恢复控件状态
        self._force_reset_connection_state()
        
        if self.serial_receiver:
            # 先清理缓冲区
            self.serial_receiver.clear_objects()
            # 然后断开连接
            self.serial_receiver.disconnect()
            
        self.last_data_length = 0
        
        self._update_status("串口连接已断开")
        
    def _force_reset_connection_state(self):
        """强制重置所有连接相关的控件状态"""
        # 恢复按钮状态
        self.connect_button.config(state=tk.NORMAL)
        self.auto_connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)
        self.port_combobox.config(state=tk.NORMAL)
        self.auto_detect_check.config(state=tk.NORMAL)
        
        # 根据自动检测状态恢复波特率选择
        if not self.auto_detect_var.get():
            self.baudrate_combobox.config(state=tk.NORMAL)
        else:
            self.baudrate_combobox.config(state=tk.DISABLED)
    
    def _load_image(self):
        """加载背景图像"""
        file_path = filedialog.askopenfilename(
            title="选择图像",
            filetypes=[
                ("图像文件", "*.jpg *.jpeg *.png *.bmp"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            # 清除所有现有的检测框
            self.box_processor.clear_boxes()
            self.serial_receiver.clear_objects()
            self.last_data_length = 0  # 添加这一行
            
            # 加载新图像
            if self.image_processor.load_image(file_path):
                self._update_status(f"已加载图像: {os.path.basename(file_path)}")
                
                # 清空检测信息
                self.info_text.delete(1.0, tk.END)
                
                # 显示新的空白图像
                self._update_image_display(self.image_processor.get_image())
            else:
                messagebox.showerror("错误", "无法加载图像")
    
    def _update_image(self):
        """手动更新图像"""
        # 使用get_all_objects而不是get_detected_objects，确保显示所有曾检测到的目标
        objects = self.serial_receiver.get_all_objects()
        
        # 根据阈值过滤对象
        filtered_objects = [obj for obj in objects if obj['score'] >= self.score_threshold]
        
        # 更新框处理器
        self.box_processor.update_from_objects(filtered_objects)
        
        # 在图像上绘制检测框
        image_with_boxes = self.image_processor.draw_boxes(filtered_objects)
        
        # 更新图像显示
        self._update_image_display(image_with_boxes)
        
        # 更新检测信息
        self._update_detection_info(filtered_objects)
    
    def _update_image_display(self, image):
        """更新图像显示"""
        # 保存原始图像
        self.original_image = image.copy()
        
        # 应用缩放
        display_width = int(256 * self.zoom_factor)
        display_height = int(256 * self.zoom_factor)
        
        # 调整图像大小
        if self.zoom_factor != 1.0:
            resized_img = image.resize((display_width, display_height), Image.LANCZOS)
        else:
            resized_img = image
        
        # 转换为Tkinter格式
        tk_img = ImageTk.PhotoImage(resized_img)
        
        # 保存引用以防止垃圾回收
        self.tk_img = tk_img
        
        # 更新标签
        self.image_label.config(image=tk_img)
        
        # 计算画布中心位置
        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()
        
        # 如果画布尚未显示，使用默认大小
        if canvas_width <= 1:
            canvas_width = 400
            canvas_height = 400
        
        # 计算居中位置
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        # 更新图像位置至中心
        self.image_canvas.coords(self.canvas_image_id, center_x, center_y)
        
        # 更新画布滚动区域
        self.image_canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
    
    def _update_detection_info(self, objects):
        """更新检测信息显示"""
        self.info_text.delete(1.0, tk.END)
        
        if not objects:
            self.info_text.insert(tk.END, "未检测到物体\n")
            return
        
        self.info_text.insert(tk.END, f"检测到 {len(objects)} 个物体:\n\n")
        
        for i, obj in enumerate(objects):
            obj_class = obj['class']
            xmin, ymin, xmax, ymax = obj['bbox']
            
            info = f"物体 {i+1}:\n"
            info += f"  类别: {obj_class}\n"
            info += f"  位置: ({xmin}, {ymin}, {xmax}, {ymax})\n\n"
            
            self.info_text.insert(tk.END, info)
    
    def _toggle_auto_update(self):
        """切换自动更新状态"""
        self.auto_update = self.auto_update_var.get()
        
        if self.auto_update:
            self.update_button.config(state=tk.DISABLED)
            self._update_status("已启用自动更新")
        else:
            self.update_button.config(state=tk.NORMAL)
            self._update_status("已禁用自动更新")
    
    def _toggle_image_display(self):
        """切换图像显示区域的可见性"""
        show_image = self.show_image_var.get()
        
        if show_image:
            # 显示图像区域
            self.upper_display.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=0, pady=0)
            self.lower_display.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False, padx=0, pady=0, ipady=80)
            
            # 启用图像相关按钮
            self.load_image_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.NORMAL)
            self.test_button.config(state=tk.NORMAL)
            self.update_button.config(state=tk.NORMAL if not self.auto_update else tk.DISABLED)
            self.auto_update_check.config(state=tk.NORMAL)
            
            self._update_status("已显示图像区域")
        else:
            # 隐藏图像区域，让串口数据区域占据全部空间
            self.upper_display.pack_forget()
            self.lower_display.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=0, pady=0)
            
            # 禁用图像相关按钮
            self.load_image_button.config(state=tk.DISABLED)
            self.save_button.config(state=tk.DISABLED)
            self.test_button.config(state=tk.DISABLED)
            self.update_button.config(state=tk.DISABLED)
            self.auto_update_check.config(state=tk.DISABLED)
            
            self._update_status("已隐藏图像区域，串口数据区域扩大")
    
    def _save_image(self):
        """保存当前图像"""
        file_path = filedialog.asksaveasfilename(
            title="保存图像",
            defaultextension=".png",
            filetypes=[
                ("PNG文件", "*.png"),
                ("JPEG文件", "*.jpg"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            if hasattr(self, 'original_image'):
                # 直接保存original_image，它是带有检测框的当前显示图像
                try:
                    self.original_image.save(file_path)
                    self._update_status(f"图像已保存: {os.path.basename(file_path)}")
                except Exception as e:
                    messagebox.showerror("错误", f"保存图像失败: {e}")
            else:
                messagebox.showerror("错误", "没有可保存的图像")
    
    def _clear_boxes(self):
        """清空检测框"""
        self.box_processor.clear_boxes()
        self.image_processor.reset_image()
        self._update_image_display(self.image_processor.get_image())
        self.info_text.delete(1.0, tk.END)
        # 同时清空串口接收器中存储的目标数据
        self.serial_receiver.clear_objects()
        self.last_data_length = 0
        self._update_status("检测框已清空")
    
    def _update_status(self, message):
        """更新状态栏信息"""
        self.status_bar.config(text=message)
        print(message)
    
    def _update_loop(self):
        """图像更新循环线程"""
        last_error_time = 0
        last_error_msg = ""
        
        while self.is_running:
            try:
                # 串口已连接并且自动更新开启时才更新
                if self.auto_update and self.serial_receiver.serial and self.serial_receiver.serial.is_open:
                    try:
                        # 检查是否有新数据或手动触发更新
                        if self.serial_receiver.has_new_data() or hasattr(self, 'force_update') and self.force_update:
                            self._update_image()
                            if hasattr(self, 'force_update'):
                                self.force_update = False
                    except (serial.SerialException, OSError) as e:
                        # 过滤掉句柄无效错误的打印
                        error_msg = str(e)
                        if "句柄无效" not in error_msg and "Handle is invalid" not in error_msg:
                            current_time = time.time()
                            if error_msg != last_error_msg or current_time - last_error_time > 5:
                                print(f"更新图像时出错: {e}")
                                last_error_msg = error_msg
                                last_error_time = current_time
                
                time.sleep(0.1)  # 更新频率
                
            except Exception as e:
                # 过滤掉重复错误和句柄无效错误
                error_msg = str(e)
                if "句柄无效" not in error_msg and "Handle is invalid" not in error_msg:
                    current_time = time.time()
                    if error_msg != last_error_msg or current_time - last_error_time > 5:
                        print(f"更新循环错误: {e}")
                        last_error_msg = error_msg
                        last_error_time = current_time
                
                time.sleep(0.5)  # 出错时暂停稍长时间
    
    def _test_draw_boxes(self):
        """使用测试数据绘制检测框"""
        # 获取当前阈值
        threshold = self.score_threshold
        
        # 根据阈值过滤对象
        filtered_test_objects = [obj for obj in self.test_objects if obj['score'] >= threshold]
        
        # 更新框处理器
        self.box_processor.update_from_objects(filtered_test_objects)
        
        # 在图像上绘制检测框
        image_with_boxes = self.image_processor.draw_boxes(filtered_test_objects)
        
        # 更新图像显示
        self._update_image_display(image_with_boxes)
        
        # 更新检测信息
        self._update_detection_info(filtered_test_objects)
        
        self._update_status(f"已显示 {len(filtered_test_objects)} 个测试检测框")
    
    def _zoom_in(self):
        """放大图像"""
        if self.zoom_factor < 3.0:
            self.zoom_factor += 0.2
            self._update_zoom_label()
            self._update_image_display(self.original_image)
    
    def _zoom_out(self):
        """缩小图像"""
        if self.zoom_factor > 0.4:
            self.zoom_factor -= 0.2
            self._update_zoom_label()
            self._update_image_display(self.original_image)
    
    def _reset_zoom(self):
        """重置缩放"""
        self.zoom_factor = 1.0
        self._update_zoom_label()
        self._update_image_display(self.original_image)
    
    def _update_zoom_label(self):
        """更新缩放标签"""
        zoom_percentage = int(self.zoom_factor * 100)
        self.zoom_label.config(text=f"{zoom_percentage}%")
    
    def on_closing(self):
        """关闭窗口时的处理"""
        self.is_running = False
        if self.serial_receiver:
            self.serial_receiver.disconnect()
        self.root.destroy()
        
    def _start_serial_data_display(self):
        """启动串口数据显示更新"""
        if hasattr(self, 'serial_data_thread') and self.serial_data_thread.is_alive():
            return
        
        self.serial_data_thread = Thread(target=self._serial_data_display_loop, daemon=True)
        self.serial_data_thread.start()
    
    def _serial_data_display_loop(self):
        """串口数据显示更新循环"""
        # last_data_length = 0
        error_count = 0
        last_error_time = 0
        last_error_msg = ""
        buffer_warning_time = 0
        current_time = time.time()
        
        while self.is_running:
            try:
                # 检查串口是否连接
                if not self.serial_receiver.serial or not self.serial_receiver.serial.is_open:
                    time.sleep(0.5)
                    continue
                
                # 检查数据缓冲区大小，如果过大则提醒用户
                current_time = time.time()
                buffer_size = len(self.serial_receiver.data_buffer)
                if buffer_size > 4096000000 and current_time - buffer_warning_time > 5:
                    buffer_warning_time = current_time
                    self._update_status(f"警告: 数据缓冲区过大 ({buffer_size} 字节)，可能需要清理")
                
                # 获取原始数据
                try:
                    raw_data = self.serial_receiver.data_buffer
                    
                    if len(raw_data) > self.last_data_length:  # 修改为使用类属性
                    # 新数据部分
                        new_data = raw_data[self.last_data_length:]  # 修改为使用类属性
                        self.last_data_length = len(raw_data)  # 修改为使用类属性
                        
                        # 添加到数据列表
                        self.serial_data.append(new_data)
                        
                        # 限制数据列表长度
                        if len(self.serial_data) > 100:
                            self.serial_data = self.serial_data[-100:]
                        
                        # 更新显示
                        self._update_receive_display()
                        
                        # 强制触发一次图像更新
                        self.force_update = True
                        
                    time.sleep(0.1)  # 更新频率
                    error_count = 0  # 重置错误计数
                    
                except (serial.SerialException, OSError) as e:
                    # 过滤重复错误消息
                    current_time = time.time()
                    error_msg = str(e)
                    
                    # 只有当错误消息变化或者距离上次错误超过5秒时才显示
                    if (error_msg != last_error_msg or current_time - last_error_time > 5) and \
                       "句柄无效" not in error_msg and "Handle is invalid" not in error_msg:
                        print(f"读取串口缓冲区错误: {e}")
                        last_error_msg = error_msg
                        last_error_time = current_time
                    
                    time.sleep(0.5)
                    
            except Exception as e:
                # 过滤重复错误消息
                current_time = time.time()
                error_msg = str(e)
                
                if (error_msg != last_error_msg or current_time - last_error_time > 5) and \
                   "句柄无效" not in error_msg and "Handle is invalid" not in error_msg:
                    print(f"串口数据显示更新错误: {e}")
                    last_error_msg = error_msg
                    last_error_time = current_time
                
                error_count += 1
                time.sleep(0.5)
    
    def _update_receive_display(self):
        """更新接收数据显示"""
        # 清空显示
        self.receive_text.delete(1.0, tk.END)
        
        # 组合所有数据
        all_data = ''.join(self.serial_data)
        
        # 检查是否使用十六进制显示
        if self.hex_display_var.get():
            # 转换为十六进制显示
            hex_data = ''
            for i, char in enumerate(all_data):
                hex_data += f"{ord(char):02X} "
                if (i + 1) % 16 == 0:
                    hex_data += '\n'
            display_data = hex_data
        else:
            # 显示ASCII文本
            display_data = ''
            for char in all_data:
                # 如果是可打印ASCII字符，直接显示
                if 32 <= ord(char) <= 126:
                    display_data += char
                # 如果是换行或回车，保留
                elif char in '\r\n':
                    display_data += char
                # 其他不可打印字符显示为点
                else:
                    display_data += '.'
        
        # 更新显示
        self.receive_text.insert(tk.END, display_data)
        self.receive_text.see(tk.END)  # 滚动到最新内容
    
    def _clear_receive(self):
        """清空接收区域"""
        self.serial_data = []
        self.receive_text.delete(1.0, tk.END)
    
    def _send_data(self):
        """发送数据到串口"""
        if not self.serial_receiver.serial or not self.serial_receiver.serial.is_open:
            messagebox.showerror("错误", "串口未连接")
            return
        
        # 获取要发送的数据
        send_data = self.send_entry.get().strip()
        
        if not send_data:
            return
        
        try:
            # 检查是否使用十六进制发送
            if self.hex_send_var.get():
                # 移除所有空格和换行符
                send_data = send_data.replace(" ", "").replace("\n", "")
                
                # 转换十六进制字符串为字节
                byte_data = bytes.fromhex(send_data)
            else:
                # 文本使用ASCII编码发送
                byte_data = send_data.encode('ascii', errors='replace')
            
            # 发送数据
            self.serial_receiver.serial.write(byte_data)
            self._update_status(f"已发送 {len(byte_data)} 字节数据")
            
            # 清空发送框
            self.send_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("发送错误", str(e))
        
    def _clear_serial_buffer(self):
        """清理串口数据缓冲区"""
        if self.serial_receiver:
            # 记录原缓冲区大小用于显示
            buffer_size = 0
            with self.serial_receiver.data_lock:
                buffer_size = len(self.serial_receiver.data_buffer)
            
            # 使用SerialReceiver提供的方法清空所有数据
            self.serial_receiver.clear_objects()
            
            self.last_data_length = 0  # 添加这一行
            
            # 更新状态
            self._update_status(f"串口缓冲区已清空 (原大小: {buffer_size} 字节)")
            
            # 清空并刷新接收显示
            self.serial_data = []
            self._update_receive_display()
            
            # 清空检测框
            self.box_processor.clear_boxes()
            self._update_image()
    
    def restart_gui(self):
        """重新初始化GUI和所有组件"""
        # 断开当前连接
        if self.serial_receiver and self.serial_receiver.serial and self.serial_receiver.serial.is_open:
            self._disconnect_serial()
        
        # 停止所有线程
        self.is_running = False
        time.sleep(0.5)  # 给线程一些时间来停止
        
        # 清空所有数据
        self.serial_data = []
        self.box_processor.clear_boxes()
        self.serial_receiver.clear_objects()
        
        self.last_data_length = 0  # 添加这一行
        
        # 重新创建串口接收器实例
        self.serial_receiver = SerialReceiver()
        
        # 重新初始化图像处理器
        self.image_processor.create_blank_image()
        
        # 重置界面状态
        self.score_threshold = 0
        self.zoom_factor = 1.0
        self._update_zoom_label()
        
        # 更新接收显示区域
        self.receive_text.delete(1.0, tk.END)
        
        # 刷新串口列表
        self._refresh_ports()
        
        # 重置按钮状态
        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)
        self.port_combobox.config(state=tk.NORMAL)
        self.baudrate_combobox.config(state=tk.NORMAL)
        
        # 更新图像显示
        self._update_image_display(self.image_processor.get_image())
        self.info_text.delete(1.0, tk.END)
        
        # 重新启动线程
        self.is_running = True
        self.update_thread = Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
        self._update_status("GUI已重新初始化")

def main():
    root = tk.Tk()
    app = DetectionGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
    
if __name__ == "__main__":
    main()
