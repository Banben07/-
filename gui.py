import sys
import os
import time
from threading import Thread
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import serial

# 导入自定义模块
from serial_receive import SerialReceiver, MultiPortManager
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

class MultiPortGUI:
    """
    多端口GUI界面
    支持同时管理和显示两个串口的数据
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("双端口串口目标检测显示器")
        self.root.geometry("1200x700")
        self.root.resizable(True, True)
        
        # 初始化多端口管理器
        self.port_manager = MultiPortManager(max_ports=2)
        self.image_processor = ImageProcessor()
        self.box_processor = BoxProcessor()
        
        # 创建空白图像
        self.image_processor.create_blank_image()
        
        # 界面刷新间隔(毫秒)
        self.update_interval = 100
        
        # 是否自动更新图像
        self.auto_update = True
        
        # 检测阈值
        self.score_threshold = 0
        
        # 缩放比例
        self.zoom_factor = 1.0
        
        # 端口配置
        self.port_configs = {
            'port1': {'name': '端口1', 'color': 'red', 'enabled': True},
            'port2': {'name': '端口2', 'color': 'blue', 'enabled': True}
        }
        
        # 串口数据存储
        self.port1_data = []
        self.port2_data = []
        
        # 初始化界面
        self._init_ui()
        
        # 启动更新线程
        self.is_running = True
        self.update_thread = Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
    
    def _init_ui(self):
        """初始化多端口GUI界面"""
        # 创建主窗口框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧控制面板
        control_frame = ttk.LabelFrame(main_frame, text="多端口控制面板")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 右侧显示区域
        display_frame = ttk.LabelFrame(main_frame, text="数据显示")
        display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建控制面板内容
        self._init_control_panel(control_frame)
        
        # 创建显示区域内容
        self._init_display_area(display_frame)
    
    def _init_control_panel(self, parent):
        """初始化控制面板"""
        # 端口1设置
        port1_frame = ttk.LabelFrame(parent, text="端口1设置")
        port1_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_port_controls(port1_frame, 'port1')
        
        # 端口2设置
        port2_frame = ttk.LabelFrame(parent, text="端口2设置")
        port2_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_port_controls(port2_frame, 'port2')
        
        # 全局控制
        global_frame = ttk.LabelFrame(parent, text="全局控制")
        global_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_global_controls(global_frame)
        
        # 状态显示
        status_frame = ttk.LabelFrame(parent, text="端口状态")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_status_display(status_frame)
        
        # 图像控制
        image_frame = ttk.LabelFrame(parent, text="图像控制")
        image_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_image_controls(image_frame)
    
    def _create_port_controls(self, parent, port_id):
        """创建单个端口的控制组件"""
        # 端口选择
        ttk.Label(parent, text="选择串口:").pack(anchor=tk.W, padx=5, pady=2)
        port_combo = ttk.Combobox(parent, width=15)
        port_combo.pack(fill=tk.X, padx=5, pady=2)
        setattr(self, f'{port_id}_combo', port_combo)
        
        # 波特率设置
        baudrate_frame = ttk.Frame(parent)
        baudrate_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(baudrate_frame, text="波特率:").pack(anchor=tk.W)
        
        baud_control_frame = ttk.Frame(baudrate_frame)
        baud_control_frame.pack(fill=tk.X)
        
        baudrate_combo = ttk.Combobox(baud_control_frame, width=10)
        baudrate_combo['values'] = ('9600', '19200', '38400', '57600', '115200', '230400', '460800', '921600')
        baudrate_combo.current(4)  # 设置为115200
        baudrate_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        setattr(self, f'{port_id}_baudrate', baudrate_combo)
        
        # 自动检测波特率
        auto_detect_var = tk.BooleanVar(value=False)
        auto_detect_check = ttk.Checkbutton(
            baud_control_frame, 
            text="自动", 
            variable=auto_detect_var
        )
        auto_detect_check.pack(side=tk.RIGHT, padx=(5, 0))
        setattr(self, f'{port_id}_auto_detect', auto_detect_var)
        
        # 端口操作按钮
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        connect_btn = ttk.Button(button_frame, text="连接", 
                                command=lambda: self._connect_port(port_id))
        connect_btn.pack(side=tk.LEFT, padx=2)
        setattr(self, f'{port_id}_connect_btn', connect_btn)
        
        disconnect_btn = ttk.Button(button_frame, text="断开", 
                                   command=lambda: self._disconnect_port(port_id))
        disconnect_btn.pack(side=tk.LEFT, padx=2)
        disconnect_btn.config(state=tk.DISABLED)
        setattr(self, f'{port_id}_disconnect_btn', disconnect_btn)
        
        # 端口启用状态
        enabled_var = tk.BooleanVar(value=True)
        enabled_check = ttk.Checkbutton(
            parent, 
            text="启用此端口", 
            variable=enabled_var,
            command=lambda: self._toggle_port_enabled(port_id)
        )
        enabled_check.pack(anchor=tk.W, padx=5, pady=2)
        setattr(self, f'{port_id}_enabled', enabled_var)
    
    def _create_global_controls(self, parent):
        """创建全局控制组件"""
        # 刷新端口按钮
        refresh_btn = ttk.Button(parent, text="刷新所有端口", command=self._refresh_all_ports)
        refresh_btn.pack(fill=tk.X, padx=5, pady=2)
        
        # 全局连接/断开按钮
        global_button_frame = ttk.Frame(parent)
        global_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        connect_all_btn = ttk.Button(global_button_frame, text="连接所有", command=self._connect_all_ports)
        connect_all_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        disconnect_all_btn = ttk.Button(global_button_frame, text="断开所有", command=self._disconnect_all_ports)
        disconnect_all_btn.pack(side=tk.RIGHT, padx=2, fill=tk.X, expand=True)
        
        # 清理数据按钮
        clear_btn = ttk.Button(parent, text="清理所有数据", command=self._clear_all_data)
        clear_btn.pack(fill=tk.X, padx=5, pady=2)
    
    def _create_status_display(self, parent):
        """创建状态显示组件"""
        # 创建状态文本框
        self.status_text = scrolledtext.ScrolledText(parent, height=6, width=40)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 自动滚动到底部
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(
            parent, 
            text="自动滚动", 
            variable=self.auto_scroll_var
        )
        auto_scroll_check.pack(anchor=tk.W, padx=5, pady=2)
    
    def _create_image_controls(self, parent):
        """创建图像控制组件"""
        # 加载图像按钮
        load_image_btn = ttk.Button(parent, text="加载背景图像", command=self._load_image)
        load_image_btn.pack(fill=tk.X, padx=5, pady=2)
        
        # 自动更新选项
        self.auto_update_var = tk.BooleanVar(value=True)
        auto_update_check = ttk.Checkbutton(
            parent, 
            text="自动更新图像", 
            variable=self.auto_update_var,
            command=self._toggle_auto_update
        )
        auto_update_check.pack(anchor=tk.W, padx=5, pady=2)
        
        # 手动更新按钮
        self.manual_update_btn = ttk.Button(parent, text="手动更新", command=self._update_image)
        self.manual_update_btn.pack(fill=tk.X, padx=5, pady=2)
        self.manual_update_btn.config(state=tk.DISABLED)
        
        # 保存图像按钮
        save_image_btn = ttk.Button(parent, text="保存图像", command=self._save_image)
        save_image_btn.pack(fill=tk.X, padx=5, pady=2)
        
        # 显示选项
        display_options_frame = ttk.LabelFrame(parent, text="显示选项")
        display_options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 端口1显示选项
        self.port1_show_var = tk.BooleanVar(value=True)
        port1_check = ttk.Checkbutton(
            display_options_frame, 
            text="显示端口1", 
            variable=self.port1_show_var
        )
        port1_check.pack(anchor=tk.W, padx=5, pady=2)
        
        # 端口2显示选项
        self.port2_show_var = tk.BooleanVar(value=True)
        port2_check = ttk.Checkbutton(
            display_options_frame, 
            text="显示端口2", 
            variable=self.port2_show_var
        )
        port2_check.pack(anchor=tk.W, padx=5, pady=2)
    
    def _init_display_area(self, parent):
        """初始化显示区域"""
        # 创建notebook用于标签页显示
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 图像显示标签页
        image_frame = ttk.Frame(self.notebook)
        self.notebook.add(image_frame, text="图像显示")
        
        # 数据显示标签页
        data_frame = ttk.Frame(self.notebook)
        self.notebook.add(data_frame, text="串口数据")
        
        # 初始化各个标签页
        self._init_image_tab(image_frame)
        self._init_data_tab(data_frame)
    
    def _init_image_tab(self, parent):
        """初始化图像显示标签页"""
        # 缩放控制
        zoom_frame = ttk.Frame(parent)
        zoom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(zoom_frame, text="缩放:").pack(side=tk.LEFT)
        
        zoom_out_btn = ttk.Button(zoom_frame, text="-", width=2, command=self._zoom_out)
        zoom_out_btn.pack(side=tk.LEFT, padx=5)
        
        self.zoom_label = ttk.Label(zoom_frame, text="100%")
        self.zoom_label.pack(side=tk.LEFT, padx=5)
        
        zoom_in_btn = ttk.Button(zoom_frame, text="+", width=2, command=self._zoom_in)
        zoom_in_btn.pack(side=tk.LEFT, padx=5)
        
        reset_zoom_btn = ttk.Button(zoom_frame, text="重置", width=5, command=self._reset_zoom)
        reset_zoom_btn.pack(side=tk.LEFT, padx=5)
        
        # 图像显示画布
        self.image_canvas = tk.Canvas(parent, bg="white")
        self.image_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _init_data_tab(self, parent):
        """初始化数据显示标签页"""
        # 创建双栏布局显示两个端口的数据
        paned_window = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 端口1数据显示
        port1_frame = ttk.LabelFrame(paned_window, text="端口1数据")
        paned_window.add(port1_frame, weight=1)
        
        self.port1_data_text = scrolledtext.ScrolledText(port1_frame, height=20, width=40)
        self.port1_data_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 端口2数据显示
        port2_frame = ttk.LabelFrame(paned_window, text="端口2数据")
        paned_window.add(port2_frame, weight=1)
        
        self.port2_data_text = scrolledtext.ScrolledText(port2_frame, height=20, width=40)
        self.port2_data_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 数据控制按钮
        data_control_frame = ttk.Frame(parent)
        data_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        clear_port1_btn = ttk.Button(data_control_frame, text="清空端口1", 
                                    command=lambda: self._clear_port_data('port1'))
        clear_port1_btn.pack(side=tk.LEFT, padx=5)
        
        clear_port2_btn = ttk.Button(data_control_frame, text="清空端口2", 
                                    command=lambda: self._clear_port_data('port2'))
        clear_port2_btn.pack(side=tk.LEFT, padx=5)
        
        clear_all_data_btn = ttk.Button(data_control_frame, text="清空所有数据", 
                                       command=self._clear_all_data_display)
        clear_all_data_btn.pack(side=tk.RIGHT, padx=5)
    
    def _refresh_all_ports(self):
        """刷新所有串口列表"""
        try:
            # 创建临时接收器获取端口列表
            temp_receiver = SerialReceiver()
            ports = temp_receiver.list_ports()
            
            # 更新两个端口的下拉列表
            self.port1_combo['values'] = ports
            self.port2_combo['values'] = ports
            
            self._update_status("已刷新串口列表")
            
        except Exception as e:
            self._update_status(f"刷新串口列表失败: {e}")
    
    def _connect_port(self, port_id):
        """连接指定端口"""
        try:
            port_combo = getattr(self, f'{port_id}_combo')
            baudrate_combo = getattr(self, f'{port_id}_baudrate')
            auto_detect_var = getattr(self, f'{port_id}_auto_detect')
            
            port_path = port_combo.get()
            if not port_path:
                messagebox.showwarning("警告", f"请选择{self.port_configs[port_id]['name']}的串口")
                return
            
            baudrate = int(baudrate_combo.get())
            auto_detect = auto_detect_var.get()
            
            # 添加端口到管理器
            if not self.port_manager.add_port(port_id, port_path, baudrate, auto_detect):
                self._update_status(f"{self.port_configs[port_id]['name']}添加失败")
                return
            
            # 连接端口
            if self.port_manager.connect_port(port_id):
                # 开始接收数据
                receiver = self.port_manager.get_receiver(port_id)
                if receiver:
                    receiver.start_receiving()
                
                # 更新按钮状态
                connect_btn = getattr(self, f'{port_id}_connect_btn')
                disconnect_btn = getattr(self, f'{port_id}_disconnect_btn')
                connect_btn.config(state=tk.DISABLED)
                disconnect_btn.config(state=tk.NORMAL)
                
                self._update_status(f"{self.port_configs[port_id]['name']}连接成功")
            else:
                self.port_manager.remove_port(port_id)
                self._update_status(f"{self.port_configs[port_id]['name']}连接失败")
                
        except Exception as e:
            self._update_status(f"{self.port_configs[port_id]['name']}连接异常: {e}")
    
    def _disconnect_port(self, port_id):
        """断开指定端口"""
        try:
            if self.port_manager.disconnect_port(port_id):
                self.port_manager.remove_port(port_id)
                
                # 更新按钮状态
                connect_btn = getattr(self, f'{port_id}_connect_btn')
                disconnect_btn = getattr(self, f'{port_id}_disconnect_btn')
                connect_btn.config(state=tk.NORMAL)
                disconnect_btn.config(state=tk.DISABLED)
                
                self._update_status(f"{self.port_configs[port_id]['name']}已断开连接")
            else:
                self._update_status(f"{self.port_configs[port_id]['name']}断开连接失败")
                
        except Exception as e:
            self._update_status(f"{self.port_configs[port_id]['name']}断开连接异常: {e}")
    
    def _connect_all_ports(self):
        """连接所有端口"""
        for port_id in ['port1', 'port2']:
            enabled_var = getattr(self, f'{port_id}_enabled')
            if enabled_var.get():
                self._connect_port(port_id)
    
    def _disconnect_all_ports(self):
        """断开所有端口连接"""
        for port_id in ['port1', 'port2']:
            self._disconnect_port(port_id)
    
    def _toggle_port_enabled(self, port_id):
        """切换端口启用状态"""
        enabled_var = getattr(self, f'{port_id}_enabled')
        enabled = enabled_var.get()
        self.port_configs[port_id]['enabled'] = enabled
        
        # 如果禁用端口且已连接，则断开连接
        if not enabled:
            self._disconnect_port(port_id)
        
        self._update_status(f"{self.port_configs[port_id]['name']}{'启用' if enabled else '禁用'}")
    
    def _clear_all_data(self):
        """清理所有端口数据"""
        self.port_manager.clear_all_objects()
        self._clear_all_data_display()
        self._update_status("已清理所有端口数据")
    
    def _clear_port_data(self, port_id):
        """清空指定端口的数据显示"""
        if port_id == 'port1':
            self.port1_data_text.delete(1.0, tk.END)
            self.port1_data = []
        elif port_id == 'port2':
            self.port2_data_text.delete(1.0, tk.END)
            self.port2_data = []
    
    def _clear_all_data_display(self):
        """清空所有数据显示"""
        self.port1_data_text.delete(1.0, tk.END)
        self.port2_data_text.delete(1.0, tk.END)
        self.port1_data = []
        self.port2_data = []
    
    def _load_image(self):
        """加载背景图像"""
        try:
            file_path = filedialog.askopenfilename(
                title="选择图像文件",
                filetypes=[("图像文件", "*.jpg *.jpeg *.png *.bmp *.gif"), ("所有文件", "*.*")]
            )
            
            if file_path:
                self.image_processor.load_image(file_path)
                self._update_image()
                self._update_status(f"已加载图像: {file_path}")
                
        except Exception as e:
            messagebox.showerror("错误", f"加载图像失败: {e}")
    
    def _update_image(self):
        """更新图像显示"""
        try:
            # 获取所有端口的检测目标
            all_objects = self.port_manager.get_all_detected_objects()
            
            # 根据显示选项过滤目标
            filtered_objects = []
            
            if self.port1_show_var.get() and 'port1' in all_objects:
                for obj in all_objects['port1']:
                    obj_copy = obj.copy()
                    obj_copy['color'] = self.port_configs['port1']['color']
                    obj_copy['source'] = 'port1'
                    filtered_objects.append(obj_copy)
            
            if self.port2_show_var.get() and 'port2' in all_objects:
                for obj in all_objects['port2']:
                    obj_copy = obj.copy()
                    obj_copy['color'] = self.port_configs['port2']['color']
                    obj_copy['source'] = 'port2'
                    filtered_objects.append(obj_copy)
            
            # 更新图像处理器的目标
            self.box_processor.set_objects(filtered_objects)
            
            # 绘制图像
            result_image = self.image_processor.get_image()
            if result_image:
                # 在图像上绘制检测框
                result_image = self.box_processor.draw_boxes_on_image(result_image, filtered_objects)
                self._update_image_display(result_image)
                
        except Exception as e:
            self._update_status(f"更新图像失败: {e}")
    
    def _update_image_display(self, image):
        """更新图像显示到画布"""
        try:
            # 应用缩放
            width = int(image.width * self.zoom_factor)
            height = int(image.height * self.zoom_factor)
            resized_image = image.resize((width, height), Image.Resampling.LANCZOS)
            
            # 转换为Tkinter格式
            photo = ImageTk.PhotoImage(resized_image)
            
            # 清空画布并显示图像
            self.image_canvas.delete("all")
            self.image_canvas.config(scrollregion=(0, 0, width, height))
            self.image_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            
            # 保持引用防止垃圾回收
            self.image_canvas.image = photo
            
        except Exception as e:
            self._update_status(f"显示图像失败: {e}")
    
    def _save_image(self):
        """保存当前图像"""
        try:
            result_image = self.image_processor.get_image()
            if result_image:
                file_path = filedialog.asksaveasfilename(
                    title="保存图像",
                    defaultextension=".png",
                    filetypes=[("PNG文件", "*.png"), ("JPEG文件", "*.jpg"), ("所有文件", "*.*")]
                )
                
                if file_path:
                    result_image.save(file_path)
                    self._update_status(f"图像已保存: {file_path}")
            else:
                messagebox.showwarning("警告", "没有可保存的图像")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存图像失败: {e}")
    
    def _toggle_auto_update(self):
        """切换自动更新状态"""
        self.auto_update = self.auto_update_var.get()
        self.manual_update_btn.config(state=tk.DISABLED if self.auto_update else tk.NORMAL)
        self._update_status(f"自动更新: {'开启' if self.auto_update else '关闭'}")
    
    def _zoom_in(self):
        """放大图像"""
        if self.zoom_factor < 3.0:
            self.zoom_factor *= 1.2
            self._update_zoom_label()
            if self.auto_update:
                self._update_image()
    
    def _zoom_out(self):
        """缩小图像"""
        if self.zoom_factor > 0.1:
            self.zoom_factor /= 1.2
            self._update_zoom_label()
            if self.auto_update:
                self._update_image()
    
    def _reset_zoom(self):
        """重置缩放比例"""
        self.zoom_factor = 1.0
        self._update_zoom_label()
        if self.auto_update:
            self._update_image()
    
    def _update_zoom_label(self):
        """更新缩放标签"""
        self.zoom_label.config(text=f"{int(self.zoom_factor * 100)}%")
    
    def _update_status(self, message):
        """更新状态信息"""
        timestamp = time.strftime("%H:%M:%S")
        status_message = f"[{timestamp}] {message}\n"
        
        self.status_text.insert(tk.END, status_message)
        
        # 自动滚动到底部
        if self.auto_scroll_var.get():
            self.status_text.see(tk.END)
    
    def _update_loop(self):
        """主更新循环"""
        while self.is_running:
            try:
                # 检查是否有新数据
                if self.port_manager.has_new_data_any_port():
                    # 更新串口数据显示
                    self._update_serial_data_display()
                    
                    # 自动更新图像
                    if self.auto_update:
                        self._update_image()
                
            except Exception as e:
                print(f"更新循环异常: {e}")
            
            time.sleep(self.update_interval / 1000.0)
    
    def _update_serial_data_display(self):
        """更新串口数据显示"""
        try:
            # 获取所有端口的检测目标
            all_objects = self.port_manager.get_all_detected_objects()
            
            # 更新端口1数据
            if 'port1' in all_objects and all_objects['port1']:
                self._append_port_data('port1', all_objects['port1'])
            
            # 更新端口2数据
            if 'port2' in all_objects and all_objects['port2']:
                self._append_port_data('port2', all_objects['port2'])
                
        except Exception as e:
            self._update_status(f"更新串口数据显示失败: {e}")
    
    def _append_port_data(self, port_id, objects):
        """添加端口数据到显示区域"""
        try:
            text_widget = getattr(self, f'{port_id}_data_text')
            timestamp = time.strftime("%H:%M:%S")
            
            for obj in objects:
                data_line = f"[{timestamp}] 类别:{obj['class']} 置信度:{obj['score']} 位置:{obj['bbox']}\n"
                text_widget.insert(tk.END, data_line)
            
            # 自动滚动到底部
            text_widget.see(tk.END)
            
            # 限制显示行数，避免内存过多占用
            lines = text_widget.get(1.0, tk.END).split('\n')
            if len(lines) > 1000:  # 保留最新1000行
                text_widget.delete(1.0, f"{len(lines) - 1000}.0")
                
        except Exception as e:
            self._update_status(f"添加{port_id}数据失败: {e}")
    
    def on_closing(self):
        """窗口关闭处理"""
        self.is_running = False
        self.port_manager.stop_all_receiving()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = DetectionGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

def start_multi_port_gui():
    """启动多端口GUI"""
    root = tk.Tk()
    gui = MultiPortGUI(root)
    
    # 设置关闭处理
    root.protocol("WM_DELETE_WINDOW", gui.on_closing)
    
    # 启动GUI
    root.mainloop()
    
if __name__ == "__main__":
    # 根据参数选择启动模式
    if len(sys.argv) > 1 and sys.argv[1] == "--multi":
        start_multi_port_gui()
    else:
        main()
