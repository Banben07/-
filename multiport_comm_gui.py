#!/usr/bin/env python3
"""
多端口串口通信GUI界面
专注于串口通信功能，支持多端口数据收发
"""

import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from threading import Thread
import serial

# 导入自定义模块
from serial_receive import MultiPortManager, SerialReceiver

class MultiPortCommGUI:
    """
    多端口串口通信GUI界面
    专注于串口通信，支持数据收发、波特率检测等功能
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("多端口串口通信工具")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        
        # 初始化多端口管理器
        self.port_manager = MultiPortManager(max_ports=2)
        
        # 界面刷新间隔(毫秒)
        self.update_interval = 100
        
        # 端口配置
        self.port_configs = {
            'port1': {'name': '端口1', 'color': '#FF6B6B', 'enabled': True},
            'port2': {'name': '端口2', 'color': '#4ECDC4', 'enabled': True}
        }
        
        # 数据存储
        self.port_data = {
            'port1': [],
            'port2': []
        }
        
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
        control_frame = ttk.LabelFrame(main_frame, text="串口控制")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 右侧显示区域
        display_frame = ttk.LabelFrame(main_frame, text="数据通信")
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
        global_frame = ttk.LabelFrame(parent, text="全局操作")
        global_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_global_controls(global_frame)
        
        # 数据发送
        send_frame = ttk.LabelFrame(parent, text="数据发送")
        send_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_send_controls(send_frame)
        
        # 状态显示
        status_frame = ttk.LabelFrame(parent, text="状态信息")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_status_display(status_frame)
    
    def _create_port_controls(self, parent, port_id):
        """创建单个端口的控制组件"""
        # 端口选择
        ttk.Label(parent, text="串口:").pack(anchor=tk.W, padx=5, pady=2)
        port_combo = ttk.Combobox(parent, width=15)
        port_combo.pack(fill=tk.X, padx=5, pady=2)
        setattr(self, f'{port_id}_combo', port_combo)
        
        # 波特率设置
        baudrate_frame = ttk.Frame(parent)
        baudrate_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(baudrate_frame, text="波特率:").pack(anchor=tk.W)
        
        baud_control_frame = ttk.Frame(baudrate_frame)
        baud_control_frame.pack(fill=tk.X)
        
        baudrate_combo = ttk.Combobox(baud_control_frame, width=8)
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
        connect_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        setattr(self, f'{port_id}_connect_btn', connect_btn)
        
        disconnect_btn = ttk.Button(button_frame, text="断开", 
                                   command=lambda: self._disconnect_port(port_id))
        disconnect_btn.pack(side=tk.RIGHT, padx=2, fill=tk.X, expand=True)
        disconnect_btn.config(state=tk.DISABLED)
        setattr(self, f'{port_id}_disconnect_btn', disconnect_btn)
        
        # 端口单独发送按钮
        send_frame = ttk.Frame(parent)
        send_frame.pack(fill=tk.X, padx=5, pady=2)
        
        port_send_btn = ttk.Button(send_frame, text=f"发送到{self.port_configs[port_id]['name']}", 
                                  command=lambda: self._send_to_port(port_id))
        port_send_btn.pack(fill=tk.X)
        setattr(self, f'{port_id}_send_btn', port_send_btn)
        
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
        refresh_btn = ttk.Button(parent, text="刷新端口列表", command=self._refresh_all_ports)
        refresh_btn.pack(fill=tk.X, padx=5, pady=2)
        
        # 全局连接/断开按钮
        global_button_frame = ttk.Frame(parent)
        global_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        connect_all_btn = ttk.Button(global_button_frame, text="连接所有", command=self._connect_all_ports)
        connect_all_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        disconnect_all_btn = ttk.Button(global_button_frame, text="断开所有", command=self._disconnect_all_ports)
        disconnect_all_btn.pack(side=tk.RIGHT, padx=2, fill=tk.X, expand=True)
        
        # 清理数据按钮
        clear_button_frame = ttk.Frame(parent)
        clear_button_frame.pack(fill=tk.X, padx=5, pady=2)
        
        clear_data_btn = ttk.Button(clear_button_frame, text="清空数据", command=self._clear_all_data)
        clear_data_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        clear_buffer_btn = ttk.Button(clear_button_frame, text="清空缓冲", command=self._clear_all_buffers)
        clear_buffer_btn.pack(side=tk.RIGHT, padx=2, fill=tk.X, expand=True)
    
    def _create_send_controls(self, parent):
        """创建数据发送控制组件"""
        # 发送数据输入框
        ttk.Label(parent, text="发送数据:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.send_text = scrolledtext.ScrolledText(parent, height=4, width=30)
        self.send_text.pack(fill=tk.X, padx=5, pady=5)
        
        # 发送选项
        options_frame = ttk.Frame(parent)
        options_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # 十六进制发送选项
        self.hex_send_var = tk.BooleanVar(value=False)
        hex_send_check = ttk.Checkbutton(
            options_frame, 
            text="十六进制", 
            variable=self.hex_send_var
        )
        hex_send_check.pack(side=tk.LEFT)
        
        # 自动换行选项
        self.auto_newline_var = tk.BooleanVar(value=True)
        newline_check = ttk.Checkbutton(
            options_frame, 
            text="自动换行", 
            variable=self.auto_newline_var
        )
        newline_check.pack(side=tk.RIGHT)
        
        # 发送按钮
        send_button_frame = ttk.Frame(parent)
        send_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        send_all_btn = ttk.Button(send_button_frame, text="发送到所有端口", command=self._send_to_all_ports)
        send_all_btn.pack(fill=tk.X, pady=2)
        
        clear_send_btn = ttk.Button(send_button_frame, text="清空发送框", command=self._clear_send_text)
        clear_send_btn.pack(fill=tk.X, pady=2)
    
    def _create_status_display(self, parent):
        """创建状态显示组件"""
        # 创建状态文本框
        self.status_text = scrolledtext.ScrolledText(parent, height=6, width=35)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 自动滚动选项
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(
            parent, 
            text="自动滚动", 
            variable=self.auto_scroll_var
        )
        auto_scroll_check.pack(anchor=tk.W, padx=5, pady=2)
    
    def _init_display_area(self, parent):
        """初始化显示区域"""
        # 创建notebook用于标签页显示
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 数据接收标签页
        receive_frame = ttk.Frame(self.notebook)
        self.notebook.add(receive_frame, text="数据接收")
        
        # 数据统计标签页
        stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(stats_frame, text="数据统计")
        
        # 初始化各个标签页
        self._init_receive_tab(receive_frame)
        self._init_stats_tab(stats_frame)
    
    def _init_receive_tab(self, parent):
        """初始化数据接收标签页"""
        # 创建双栏布局显示两个端口的数据
        paned_window = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 端口1数据显示
        port1_frame = ttk.LabelFrame(paned_window, text="端口1接收数据")
        paned_window.add(port1_frame, weight=1)
        
        self.port1_data_text = scrolledtext.ScrolledText(port1_frame, height=25, width=40)
        self.port1_data_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 端口1控制按钮
        port1_control_frame = ttk.Frame(port1_frame)
        port1_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        port1_clear_btn = ttk.Button(port1_control_frame, text="清空", 
                                    command=lambda: self._clear_port_data('port1'))
        port1_clear_btn.pack(side=tk.LEFT, padx=5)
        
        port1_save_btn = ttk.Button(port1_control_frame, text="保存", 
                                   command=lambda: self._save_port_data('port1'))
        port1_save_btn.pack(side=tk.RIGHT, padx=5)
        
        # 端口2数据显示
        port2_frame = ttk.LabelFrame(paned_window, text="端口2接收数据")
        paned_window.add(port2_frame, weight=1)
        
        self.port2_data_text = scrolledtext.ScrolledText(port2_frame, height=25, width=40)
        self.port2_data_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 端口2控制按钮
        port2_control_frame = ttk.Frame(port2_frame)
        port2_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        port2_clear_btn = ttk.Button(port2_control_frame, text="清空", 
                                    command=lambda: self._clear_port_data('port2'))
        port2_clear_btn.pack(side=tk.LEFT, padx=5)
        
        port2_save_btn = ttk.Button(port2_control_frame, text="保存", 
                                   command=lambda: self._save_port_data('port2'))
        port2_save_btn.pack(side=tk.RIGHT, padx=5)
    
    def _init_stats_tab(self, parent):
        """初始化统计信息标签页"""
        # 统计信息显示
        self.stats_text = scrolledtext.ScrolledText(parent, height=25, width=80)
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 统计控制按钮
        stats_control_frame = ttk.Frame(parent)
        stats_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        refresh_stats_btn = ttk.Button(stats_control_frame, text="刷新统计", command=self._update_statistics)
        refresh_stats_btn.pack(side=tk.LEFT, padx=5)
        
        export_stats_btn = ttk.Button(stats_control_frame, text="导出统计", command=self._export_statistics)
        export_stats_btn.pack(side=tk.RIGHT, padx=5)
    
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
                
                self._update_status(f"{self.port_configs[port_id]['name']}连接成功 ({port_path})")
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
    
    def _send_to_port(self, port_id):
        """发送数据到指定端口"""
        try:
            # 获取发送数据
            send_data = self.send_text.get(1.0, tk.END).strip()
            if not send_data:
                messagebox.showwarning("警告", "请输入要发送的数据")
                return
            
            # 添加换行符（如果启用）
            if self.auto_newline_var.get() and not self.hex_send_var.get():
                send_data += "\n"
            
            # 发送数据
            success = self.port_manager.send_data_to_port(port_id, send_data, self.hex_send_var.get())
            
            if success:
                format_type = "十六进制" if self.hex_send_var.get() else "文本"
                self._update_status(f"向{self.port_configs[port_id]['name']}发送{format_type}数据成功")
            else:
                self._update_status(f"向{self.port_configs[port_id]['name']}发送数据失败")
                
        except Exception as e:
            self._update_status(f"发送数据到{port_id}异常: {e}")
    
    def _send_to_all_ports(self):
        """发送数据到所有端口"""
        try:
            # 获取发送数据
            send_data = self.send_text.get(1.0, tk.END).strip()
            if not send_data:
                messagebox.showwarning("警告", "请输入要发送的数据")
                return
            
            # 添加换行符（如果启用）
            if self.auto_newline_var.get() and not self.hex_send_var.get():
                send_data += "\n"
            
            # 发送到所有端口
            results = self.port_manager.send_data_to_all_ports(send_data, self.hex_send_var.get())
            
            # 统计结果
            connected_ports = sum(1 for port_id in ['port1', 'port2'] 
                                 if self.port_manager.port_configs.get(port_id, {}).get('connected', False))
            success_count = sum(1 for success in results.values() if success)
            
            format_type = "十六进制" if self.hex_send_var.get() else "文本"
            self._update_status(f"批量发送{format_type}数据: {success_count}/{connected_ports} 成功")
            
        except Exception as e:
            self._update_status(f"批量发送数据异常: {e}")
    
    def _clear_send_text(self):
        """清空发送文本框"""
        self.send_text.delete(1.0, tk.END)
    
    def _clear_all_data(self):
        """清理所有数据显示"""
        self.port1_data_text.delete(1.0, tk.END)
        self.port2_data_text.delete(1.0, tk.END)
        self.port_data['port1'] = []
        self.port_data['port2'] = []
        self._update_status("已清空所有显示数据")
    
    def _clear_all_buffers(self):
        """清空所有端口缓冲区"""
        results = self.port_manager.clear_all_port_buffers()
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        self._update_status(f"清空缓冲区: {success_count}/{total_count} 成功")
    
    def _clear_port_data(self, port_id):
        """清空指定端口的数据显示"""
        if port_id == 'port1':
            self.port1_data_text.delete(1.0, tk.END)
            self.port_data['port1'] = []
        elif port_id == 'port2':
            self.port2_data_text.delete(1.0, tk.END)
            self.port_data['port2'] = []
        
        self._update_status(f"已清空{self.port_configs[port_id]['name']}数据")
    
    def _save_port_data(self, port_id):
        """保存指定端口的数据"""
        try:
            # 获取要保存的数据
            text_widget = getattr(self, f'{port_id}_data_text')
            data_content = text_widget.get(1.0, tk.END)
            
            if not data_content.strip():
                messagebox.showwarning("警告", f"{self.port_configs[port_id]['name']}没有数据可保存")
                return
            
            # 选择保存文件
            file_path = filedialog.asksaveasfilename(
                title=f"保存{self.port_configs[port_id]['name']}数据",
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(data_content)
                
                self._update_status(f"{self.port_configs[port_id]['name']}数据已保存: {file_path}")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存{self.port_configs[port_id]['name']}数据失败: {e}")
    
    def _update_statistics(self):
        """更新统计信息"""
        try:
            status_info = self.port_manager.get_port_status()
            
            stats_text = "=== 多端口通信统计信息 ===\n\n"
            stats_text += f"更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for port_id, status in status_info.items():
                port_name = self.port_configs.get(port_id, {}).get('name', port_id)
                stats_text += f"--- {port_name} ---\n"
                stats_text += f"端口路径: {status.get('port_path', 'N/A')}\n"
                stats_text += f"波特率: {status.get('baudrate', 'N/A')}\n"
                stats_text += f"连接状态: {'已连接' if status.get('connected', False) else '未连接'}\n"
                stats_text += f"自动检测: {'是' if status.get('auto_detect', False) else '否'}\n"
                
                if status.get('connected', False):
                    # 获取接收数据统计
                    received_data = self.port_manager.get_received_data(port_id)
                    stats_text += f"接收行数: {len(received_data)}\n"
                    
                    # 计算数据量
                    total_chars = sum(len(line) for line in received_data)
                    stats_text += f"接收字符数: {total_chars}\n"
                    
                    last_update = status.get('last_update', 0)
                    if last_update > 0:
                        elapsed = time.time() - last_update
                        stats_text += f"最后活动: {elapsed:.1f}秒前\n"
                    else:
                        stats_text += "最后活动: 从未\n"
                
                stats_text += "\n"
            
            # 系统信息
            stats_text += f"--- 系统信息 ---\n"
            active_ports = sum(1 for s in status_info.values() if s.get('connected', False))
            stats_text += f"活跃端口数: {active_ports}\n"
            stats_text += f"总端口数: {len(status_info)}\n"
            
            # 更新显示
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, stats_text)
            
        except Exception as e:
            self._update_status(f"更新统计信息失败: {e}")
    
    def _export_statistics(self):
        """导出统计信息"""
        try:
            file_path = filedialog.asksaveasfilename(
                title="导出统计信息",
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            
            if file_path:
                stats_content = self.stats_text.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(stats_content)
                
                self._update_status(f"统计信息已导出: {file_path}")
                
        except Exception as e:
            messagebox.showerror("错误", f"导出统计信息失败: {e}")
    
    def _update_status(self, message):
        """更新状态信息"""
        timestamp = time.strftime("%H:%M:%S")
        status_message = f"[{timestamp}] {message}\n"
        
        self.status_text.insert(tk.END, status_message)
        
        # 自动滚动到底部
        if self.auto_scroll_var.get():
            self.status_text.see(tk.END)
        
        # 限制状态显示行数
        lines = self.status_text.get(1.0, tk.END).split('\n')
        if len(lines) > 500:  # 保留最新500行
            self.status_text.delete(1.0, f"{len(lines) - 500}.0")
    
    def _update_loop(self):
        """主更新循环"""
        while self.is_running:
            try:
                # 获取所有端口的接收数据
                all_data = self.port_manager.get_all_received_data(100)
                
                # 更新端口1数据显示
                if 'port1' in all_data:
                    self._update_port_data_display('port1', all_data['port1'])
                
                # 更新端口2数据显示
                if 'port2' in all_data:
                    self._update_port_data_display('port2', all_data['port2'])
                
                # 定期更新统计信息
                if hasattr(self, '_last_stats_update'):
                    if time.time() - self._last_stats_update > 10.0:  # 每10秒更新一次
                        self._update_statistics()
                        self._last_stats_update = time.time()
                else:
                    self._last_stats_update = time.time()
                
            except Exception as e:
                print(f"更新循环异常: {e}")
            
            time.sleep(self.update_interval / 1000.0)
    
    def _update_port_data_display(self, port_id, new_data):
        """更新端口数据显示"""
        try:
            if not new_data:
                return
            
            # 检查是否有新数据
            current_data = self.port_data.get(port_id, [])
            if len(new_data) <= len(current_data):
                return  # 没有新数据
            
            # 获取新增的数据
            new_lines = new_data[len(current_data):]
            self.port_data[port_id] = new_data
            
            # 更新显示
            text_widget = getattr(self, f'{port_id}_data_text')
            timestamp = time.strftime("%H:%M:%S")
            
            for line in new_lines:
                if line.strip():  # 忽略空行
                    display_line = f"[{timestamp}] {line}\n"
                    text_widget.insert(tk.END, display_line)
            
            # 自动滚动到底部
            text_widget.see(tk.END)
            
            # 限制显示行数，避免内存过多占用
            lines = text_widget.get(1.0, tk.END).split('\n')
            if len(lines) > 1000:  # 保留最新1000行
                text_widget.delete(1.0, f"{len(lines) - 1000}.0")
                
        except Exception as e:
            self._update_status(f"更新{port_id}显示失败: {e}")
    
    def on_closing(self):
        """窗口关闭处理"""
        self.is_running = False
        self.port_manager.stop_all_receiving()
        self.root.destroy()

def start_multiport_comm_gui():
    """启动多端口通信GUI"""
    root = tk.Tk()
    gui = MultiPortCommGUI(root)
    
    # 设置关闭处理
    root.protocol("WM_DELETE_WINDOW", gui.on_closing)
    
    # 启动GUI
    root.mainloop()

if __name__ == "__main__":
    start_multiport_comm_gui() 