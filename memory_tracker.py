import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import psutil
import time
import threading
import csv
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import matplotlib.font_manager as fm


class MultiProcessMemoryMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("多进程内存监控工具 - 操作记录版")
        self.root.geometry("1200x800")

        # 核心数据
        self.selected_pids = set()  # 选中的进程PID
        self.process_info = {}  # 进程信息缓存 {pid: {'name': ..., 'status': ..., 'memory': ...}}
        self.operation_start_time = None
        self.operation_end_time = None
        self.operation_name = ""
        self.memory_samples = {}  # 内存采样数据 {pid: [(time, mem), ...]}
        self.is_monitoring = False
        self.is_recording = False  # 明确记录状态
        self.monitor_thread = None

        # 内存指标选择 (rss:物理内存, vms:虚拟内存, uss:独占内存)
        self.memory_metric = "rss"

        # 新增：记录开始和结束的时间差
        self.operation_time_diff = 0

        # 设置matplotlib中文字体
        self.setup_matplotlib_fonts()

        # 创建UI
        self.create_widgets()
        self.refresh_processes()

    def setup_matplotlib_fonts(self):
        """设置matplotlib支持中文显示的字体"""
        # 尝试查找系统中的中文字体
        font_paths = fm.findSystemFonts()
        chinese_fonts = []

        # 常见中文字体名称
        chinese_font_names = ['SimHei', 'WenQuanYi Micro Hei', 'Heiti TC',
                              'Microsoft YaHei', 'SimSun', 'WenQuanYi Micro Hei']

        for font_path in font_paths:
            try:
                font = fm.FontProperties(fname=font_path)
                font_name = font.get_name()
                if font_name in chinese_font_names:
                    chinese_fonts.append(font_path)
            except:
                continue

        # 设置matplotlib使用找到的第一个中文字体
        if chinese_fonts:
            plt.rcParams['font.family'] = [fm.FontProperties(fname=chinese_fonts[0]).get_name()]
        else:
            # 如果没找到中文字体，尝试使用通用sans-serif字体并设置回退
            plt.rcParams['font.family'] = ['sans-serif']
            plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Micro Hei',
                                               'Heiti TC', 'Microsoft YaHei',
                                               'SimSun', 'Arial'] + plt.rcParams['font.sans-serif']

        # 确保负号正常显示
        plt.rcParams['axes.unicode_minus'] = False

    def create_widgets(self):
        # 主框架分割
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧：进程选择和控制
        left_frame = ttk.Frame(main_frame, width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)

        # 右侧：监控和图表
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 进程选择区域
        process_frame = ttk.LabelFrame(left_frame, text="选择目标进程")
        process_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(process_frame, text="搜索进程:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        ttk.Entry(process_frame, textvariable=self.search_var, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(process_frame, text="搜索", command=self.filter_processes).pack(side=tk.LEFT, padx=5)
        ttk.Button(process_frame, text="刷新", command=self.refresh_processes).pack(side=tk.LEFT, padx=5)

        # 内存指标选择
        ttk.Label(process_frame, text="内存指标:").pack(side=tk.LEFT, padx=5)
        self.metric_var = tk.StringVar(value="rss")
        metric_combo = ttk.Combobox(process_frame, textvariable=self.metric_var,
                                    values=["rss (物理内存)", "vms (虚拟内存)", "uss (独占内存)"],
                                    state="readonly", width=15)
        metric_combo.pack(side=tk.LEFT, padx=5)
        metric_combo.bind("<<ComboboxSelected>>", self.on_metric_change)

        # 手动刷新按钮
        self.sync_btn = ttk.Button(process_frame, text="同步任务管理器", command=self.sync_with_task_manager)
        self.sync_btn.pack(side=tk.LEFT, padx=5)

        # 进程列表
        columns = ("pid", "name", "memory", "status")
        self.tree = ttk.Treeview(
            left_frame,
            columns=columns,
            show="headings",
            height=12
        )

        self.tree.heading("pid", text="PID")
        self.tree.heading("name", text="进程名称")
        self.tree.heading("memory", text="内存 (MB)")
        self.tree.heading("status", text="状态")

        self.tree.column("pid", width=60, anchor=tk.CENTER)
        self.tree.column("name", width=180, anchor=tk.W)
        self.tree.column("memory", width=80, anchor=tk.E)
        self.tree.column("status", width=60, anchor=tk.CENTER)

        self.tree.pack(fill=tk.X, padx=5, pady=5)

        # 绑定状态列点击
        self.tree.bind("<Button-1>", self.on_status_click)

        # 控制按钮
        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(control_frame, text="全选", command=self.select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="取消全选", command=self.deselect_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="清除未运行进程", command=self.clean_processes).pack(side=tk.LEFT, padx=5)

        # 选中进程信息
        selected_frame = ttk.LabelFrame(left_frame, text="选中的进程")
        selected_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.selected_processes_text = scrolledtext.ScrolledText(selected_frame, height=8)
        self.selected_processes_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.selected_processes_text.config(state=tk.DISABLED)

        # 总内存显示
        self.total_mem_var = tk.StringVar(value="总内存: 0 MB")
        ttk.Label(left_frame, textvariable=self.total_mem_var, font=("Arial", 12, "bold")).pack(anchor=tk.W, padx=10,
                                                                                                pady=5)

        # 操作记录区域
        operation_frame = ttk.LabelFrame(left_frame, text="操作记录")
        operation_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(operation_frame, text="操作名称:").pack(side=tk.LEFT, padx=5)
        self.operation_name_var = tk.StringVar()
        ttk.Entry(operation_frame, textvariable=self.operation_name_var, width=20).pack(side=tk.LEFT, padx=5)

        self.start_btn = ttk.Button(operation_frame, text="开始记录", command=self.start_recording)
        self.start_btn.pack(side=tk.LEFT, padx=10)

        self.stop_btn = ttk.Button(operation_frame, text="停止记录", state=tk.DISABLED, command=self.stop_recording)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = ttk.Button(operation_frame, text="保存记录", state=tk.DISABLED, command=self.save_recording)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        # 状态显示
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(left_frame, textvariable=self.status_var, font=("Arial", 10, "bold"))
        status_label.pack(anchor=tk.W, padx=10, pady=5)

        # 内存变化图表
        chart_frame = ttk.LabelFrame(right_frame, text="内存变化图表")
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建matplotlib图表
        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 统计信息
        stats_frame = ttk.LabelFrame(right_frame, text="内存变化统计")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        self.start_mem_var = tk.StringVar(value="操作前总内存: 0 MB")
        ttk.Label(stats_frame, textvariable=self.start_mem_var).pack(anchor=tk.W, padx=5, pady=2)

        self.end_mem_var = tk.StringVar(value="操作后总内存: 0 MB")
        ttk.Label(stats_frame, textvariable=self.end_mem_var).pack(anchor=tk.W, padx=5, pady=2)

        self.change_var = tk.StringVar(value="总内存变化: 0 MB")
        ttk.Label(stats_frame, textvariable=self.change_var, foreground="red").pack(anchor=tk.W, padx=5, pady=2)

        self.max_change_var = tk.StringVar(value="最大总变化: 0 MB")
        ttk.Label(stats_frame, textvariable=self.max_change_var).pack(anchor=tk.W, padx=5, pady=2)

        # 新增：时间差显示
        self.time_diff_var = tk.StringVar(value="操作时间差: 0.00 秒")
        ttk.Label(stats_frame, textvariable=self.time_diff_var).pack(anchor=tk.W, padx=5, pady=2)

    def on_metric_change(self, event):
        """切换内存指标"""
        metric_map = {
            "rss (物理内存)": "rss",
            "vms (虚拟内存)": "vms",
            "uss (独占内存)": "uss"
        }
        self.memory_metric = metric_map.get(self.metric_var.get(), "rss")
        self.refresh_processes()  # 刷新进程列表，使用新指标

    def sync_with_task_manager(self):
        """同步与任务管理器的采样时间"""
        self.status_var.set("已同步采样时间，请对比任务管理器")
        self.update_selected_processes()  # 立即更新显示
        # 高亮提示用户
        self.sync_btn.configure(style="TButton")
        self.root.after(1000, lambda: self.sync_btn.configure(style=""))

    def on_status_click(self, event):
        """处理状态列点击"""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        if column != "#4":  # 状态列
            return

        item = self.tree.identify_row(event.y)
        if not item:
            return

        pid = int(self.tree.item(item, "values")[0])

        if pid in self.selected_pids:
            self.selected_pids.remove(pid)
            self.tree.set(item, "status", "")
        else:
            self.selected_pids.add(pid)
            self.tree.set(item, "status", "√")

        # 更新选中进程显示
        self.update_selected_processes()

    def refresh_processes(self):
        """刷新进程列表"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        def load_processes():
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'ppid']):
                try:
                    pid = proc.pid
                    ppid = proc.ppid()  # 获取父进程PID
                    name = proc.name()

                    # 获取内存指标
                    mem_info = proc.memory_info()
                    if self.memory_metric == "rss":
                        mem = mem_info.rss / 1024 / 1024  # 物理内存
                    elif self.memory_metric == "vms":
                        mem = mem_info.vms / 1024 / 1024  # 虚拟内存
                    elif self.memory_metric == "uss":
                        try:
                            mem = proc.memory_full_info().uss / 1024 / 1024  # 独占内存
                        except:
                            mem = mem_info.rss / 1024 / 1024  # 不支持USS时回退到RSS

                    # 简单去重：不显示System Idle Process的子进程
                    if name != 'System Idle Process':
                        processes.append((pid, name, mem, ppid))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # 在主线程更新UI
            self.root.after(0, self._update_treeview, processes)

        threading.Thread(target=load_processes, daemon=True).start()

    def _update_treeview(self, processes):
        """更新Treeview显示"""
        # 清空当前进程信息缓存
        self.process_info = {}

        # 更新进程信息缓存
        for pid, name, mem, ppid in processes:
            status = "√" if pid in self.selected_pids else ""
            self.tree.insert(
                parent="",
                index=tk.END,
                values=(pid, name, f"{mem:.2f}", status)
            )

            # 更新进程信息缓存，增加状态字段
            self.process_info[pid] = {
                'name': name,
                'memory': mem,
                'ppid': ppid,
                'status': 'running'  # 默认为运行中
            }

        # 过滤掉不存在的进程PID
        active_pids = {pid for pid, _, _, _ in processes}
        self.selected_pids = {pid for pid in self.selected_pids if pid in active_pids}

        # 更新选中进程显示
        self.update_selected_processes()

    def filter_processes(self):
        """根据搜索框内容过滤进程"""
        keyword = self.search_var.get().lower().strip()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for pid, name, mem, ppid in self._get_all_processes():
            if keyword in str(pid) or keyword in name.lower():
                status = "√" if pid in self.selected_pids else ""
                self.tree.insert(
                    parent="",
                    index=tk.END,
                    values=(pid, name, f"{mem:.2f}", status)
                )

    def _get_all_processes(self):
        """获取所有进程"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'ppid']):
            try:
                pid = proc.pid
                ppid = proc.ppid()
                name = proc.name()

                # 获取内存指标
                mem_info = proc.memory_info()
                if self.memory_metric == "rss":
                    mem = mem_info.rss / 1024 / 1024
                elif self.memory_metric == "vms":
                    mem = mem_info.vms / 1024 / 1024
                elif self.memory_metric == "uss":
                    try:
                        mem = proc.memory_full_info().uss / 1024 / 1024
                    except:
                        mem = mem_info.rss / 1024 / 1024

                if name != 'System Idle Process':
                    processes.append((pid, name, mem, ppid))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes

    def select_all(self):
        """全选当前显示的进程"""
        for item in self.tree.get_children():
            pid = int(self.tree.item(item, "values")[0])
            self.selected_pids.add(pid)
            self.tree.set(item, "status", "√")

        self.update_selected_processes()

    def deselect_all(self):
        """取消全选当前显示的进程"""
        for item in self.tree.get_children():
            pid = int(self.tree.item(item, "values")[0])
            self.selected_pids.discard(pid)
            self.tree.set(item, "status", "")

        self.update_selected_processes()

    def clean_processes(self):
        """清除未运行的进程"""
        active_pids = set()

        for proc in psutil.process_iter(['pid']):
            active_pids.add(proc.pid)

        # 移除未运行的选中进程
        removed = False
        for pid in list(self.selected_pids):
            if pid not in active_pids:
                self.selected_pids.discard(pid)
                removed = True

        if removed:
            messagebox.showinfo("提示", "已清除未运行的进程")
            self.refresh_processes()
        else:
            messagebox.showinfo("提示", "所有选中的进程都在运行中")

    def update_selected_processes(self):
        """更新选中进程的显示"""
        # 先禁用编辑
        self.selected_processes_text.config(state=tk.NORMAL)
        self.selected_processes_text.delete(1.0, tk.END)

        # 获取当前活动进程
        active_pids = set()
        for proc in psutil.process_iter(['pid']):
            active_pids.add(proc.pid)

        total_mem = 0
        for pid in sorted(self.selected_pids):
            if pid in self.process_info:
                name = self.process_info[pid]['name']
                mem = self.process_info[pid]['memory']
                status = "运行中" if pid in active_pids else "已终止"

                # 统一显示两位小数
                self.selected_processes_text.insert(
                    tk.END,
                    f"PID: {pid} | {name} | {mem:.2f} MB | {status}\n"
                )

                if pid in active_pids:
                    total_mem += mem

        # 更新总内存显示（统一两位小数）
        self.total_mem_var.set(f"总内存: {total_mem:.2f} MB")

        # 重新禁用编辑
        self.selected_processes_text.config(state=tk.DISABLED)

    def start_monitoring(self):
        """开始监控选中的进程"""
        if not self.selected_pids:
            messagebox.showinfo("提示", "请先选择至少一个进程")
            return

        # 初始化内存采样数据
        self.memory_samples = {pid: [] for pid in self.selected_pids}

        # 启动监控线程
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_memory, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """停止监控选中的进程"""
        self.is_monitoring = False

    def monitor_memory(self):
        """监控选中进程的内存"""
        while self.is_monitoring and self.selected_pids:
            current_time = time.time()

            # 临时存储有效进程的内存数据
            valid_processes = []
            total_mem = 0

            # 遍历前复制集合，避免迭代时修改原集合
            pids_to_check = list(self.selected_pids)

            # 获取当前活动进程
            active_pids = set()
            for proc in psutil.process_iter(['pid']):
                active_pids.add(proc.pid)

            # 检查每个选中的进程
            for pid in pids_to_check:
                # 跳过已不存在的进程
                if pid not in active_pids:
                    if pid in self.selected_pids:
                        self.selected_pids.discard(pid)
                    if pid in self.memory_samples:
                        del self.memory_samples[pid]
                    continue

                try:
                    process = psutil.Process(pid)

                    # 使用当前选择的内存指标
                    mem_info = process.memory_info()
                    if self.memory_metric == "rss":
                        mem = mem_info.rss / 1024 / 1024
                    elif self.memory_metric == "vms":
                        mem = mem_info.vms / 1024 / 1024
                    elif self.memory_metric == "uss":
                        try:
                            mem = process.memory_full_info().uss / 1024 / 1024
                        except:
                            mem = mem_info.rss / 1024 / 1024

                    # 更新进程信息缓存
                    if pid in self.process_info:
                        self.process_info[pid]['memory'] = mem

                    # 添加到采样数据
                    if pid in self.memory_samples:
                        self.memory_samples[pid].append((current_time, mem))

                    # 累加总内存
                    total_mem += mem

                    # 记录有效进程
                    valid_processes.append(pid)

                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    # 处理进程可能已终止的情况
                    if pid in self.selected_pids:
                        self.selected_pids.discard(pid)
                    if pid in self.memory_samples:
                        del self.memory_samples[pid]

            # 只保留有效进程在选中列表中
            self.selected_pids = set(valid_processes)

            # 更新UI
            self.root.after(0, lambda m=total_mem: self.total_mem_var.set(f"总内存: {m:.2f} MB"))
            self.root.after(0, self.update_selected_processes)

            # 如果正在记录操作，更新图表
            if self.is_recording:
                self.root.after(0, self.update_chart)

            # 检查是否还有选中的进程
            if not self.selected_pids:
                self.root.after(0, lambda: messagebox.showinfo("提示", "所有选中的进程都已终止"))
                self.root.after(0, self.stop_monitoring)
                break

            time.sleep(0.5)  # 每0.5秒更新一次

    def update_chart(self):
        """更新内存变化图表"""
        # 过滤掉没有采样数据的进程
        active_samples = {pid: samples for pid, samples in self.memory_samples.items() if samples}

        if not active_samples:
            return

        # 清除旧图表
        self.ax.clear()

        # 计算开始和结束时间
        start_times = []
        end_times = []

        for pid, samples in active_samples.items():
            if samples:
                start_times.append(min(t for t, _ in samples))
                end_times.append(max(t for t, _ in samples))

        if not start_times or not end_times:
            return

        start_time = min(start_times)
        end_time = max(end_times)
        duration = end_time - start_time

        # 如果持续时间小于10秒，显示到0.1秒精度
        if duration < 10:
            time_labels = [f"{t - start_time:.1f}" for t, _ in active_samples[list(active_samples.keys())[0]]]
        else:
            time_labels = [f"{t - start_time:.0f}" for t, _ in active_samples[list(active_samples.keys())[0]]]

        # 绘制每个进程的内存曲线
        for pid, samples in active_samples.items():
            if not samples:
                continue

            times = [t - start_time for t, _ in samples]
            mems = [m for _, m in samples]

            name = self.process_info.get(pid, {}).get('name', f"PID:{pid}")
            self.ax.plot(times, mems, label=f"{name} (PID:{pid})")

        # 绘制总内存曲线
        if len(active_samples) > 1:
            times = []
            total_mems = []

            # 获取所有时间点
            all_times = set()
            for pid, samples in active_samples.items():
                for t, _ in samples:
                    all_times.add(t)

            all_times = sorted(all_times)

            # 计算每个时间点的总内存
            for t in all_times:
                total_mem = 0
                valid_pids = 0  # 有效进程计数

                for pid, samples in active_samples.items():
                    # 只处理有采样数据的进程
                    if samples:
                        # 找到最接近当前时间的样本
                        closest_sample = min(samples, key=lambda x: abs(x[0] - t))
                        total_mem += closest_sample[1]
                        valid_pids += 1

                # 只有当有有效进程时才添加数据点
                if valid_pids > 0:
                    times.append(t - start_time)
                    total_mems.append(total_mem)

            # 只有当有足够的数据点时才绘制曲线
            if len(times) > 1:
                self.ax.plot(times, total_mems, 'k-', linewidth=2, label="总内存")

                # 新增：绘制内存变化差值曲线
                if len(total_mems) > 1:
                    diffs = [total_mems[i] - total_mems[0] for i in range(len(total_mems))]
                    self.ax.plot(times, diffs, 'r--', label="内存变化差")

        # 设置图表属性
        self.ax.set_xlabel('时间 (秒)')
        self.ax.set_ylabel('内存 (MB)')
        self.ax.set_title(f'{self.operation_name} 内存变化')
        self.ax.grid(True)

        # 只有当有数据点时才添加图例
        if len(active_samples) > 0:
            self.ax.legend(loc='upper left', bbox_to_anchor=(1, 1))

        # 调整布局
        self.fig.tight_layout()
        self.canvas.draw()

    def start_recording(self):
        """开始记录操作"""
        # 过滤掉不存在的进程PID
        active_pids = set(self.process_info.keys())
        self.selected_pids = {pid for pid in self.selected_pids if pid in active_pids}

        if not self.selected_pids:
            messagebox.showinfo("提示", "请先选择至少一个有效进程")
            return

        operation_name = self.operation_name_var.get().strip()
        if not operation_name:
            messagebox.showinfo("提示", "请输入操作名称")
            return

        # 开始监控（如果尚未启动）
        if not self.is_monitoring:
            self.start_monitoring()

        # 清空之前的记录
        self.memory_samples = {pid: [] for pid in self.selected_pids}

        # 记录开始时间
        self.operation_name = operation_name
        self.operation_start_time = time.time()
        self.operation_end_time = None  # 重置结束时间

        # 更新状态
        self.is_recording = True
        self.status_var.set("记录中...")

        # 更新UI（统一两位小数）
        total_start_mem = sum(
            self.process_info[pid]['memory'] for pid in self.selected_pids if pid in self.process_info)
        self.start_mem_var.set(f"操作前总内存: {total_start_mem:.2f} MB")
        self.end_mem_var.set(f"操作后总内存: {total_start_mem:.2f} MB")
        self.change_var.set(f"总内存变化: 0.00 MB")
        self.max_change_var.set(f"最大总变化: 0.00 MB")

        # 确保按钮状态正确设置
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.DISABLED)

        messagebox.showinfo("开始记录",
                            f"已开始记录 '{operation_name}' 的内存变化\n请执行相应操作，完成后点击'停止记录'")

    def stop_recording(self):
        """停止记录操作"""
        if not self.is_recording:
            return

        # 记录结束时间
        self.operation_end_time = time.time()
        self.is_recording = False

        # 计算时间差
        self.operation_time_diff = self.operation_end_time - self.operation_start_time

        # 更新状态
        self.status_var.set("记录已完成")

        # 更新UI（统一两位小数）
        total_start_mem = sum(
            self.process_info[pid]['memory'] for pid in self.selected_pids if pid in self.process_info)
        self.start_mem_var.set(f"操作前总内存: {total_start_mem:.2f} MB")

        total_end_mem = sum(self.process_info[pid]['memory'] for pid in self.selected_pids if pid in self.process_info)
        self.end_mem_var.set(f"操作后总内存: {total_end_mem:.2f} MB")

        change = total_end_mem - total_start_mem
        self.change_var.set(f"总内存变化: {change:+.2f} MB")

        # 计算最大变化
        max_total_mem = 0
        for pid, samples in self.memory_samples.items():
            if samples:
                pid_max_mem = max(m for _, m in samples)
                pid_start_mem = samples[0][1]
                max_total_mem += pid_max_mem - pid_start_mem

        self.max_change_var.set(f"最大总变化: {max_total_mem:+.2f} MB")

        # 更新时间差显示
        self.time_diff_var.set(f"操作时间差: {self.operation_time_diff:.2f} 秒")

        # 确保按钮状态正确设置
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.NORMAL)

        # 最后更新一次图表
        self.update_chart()

        messagebox.showinfo("记录完成", f"'{self.operation_name}' 操作的内存变化记录已完成")

    def save_recording(self):
        """保存记录"""
        # 过滤掉没有采样数据的进程
        active_samples = {pid: samples for pid, samples in self.memory_samples.items() if samples}

        if not active_samples or not self.operation_end_time or not self.operation_name:
            messagebox.showinfo("提示", "没有可保存的记录")
            return

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        operation_name = self.operation_name.replace(" ", "_")
        filename = f"memory_change_{operation_name}_{timestamp}.csv"

        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)

                # 写入表头
                headers = ["时间戳", "相对时间(秒)"]
                for pid in active_samples:
                    name = self.process_info.get(pid, {}).get('name', f"PID:{pid}")
                    headers.append(f"{name} (PID:{pid})")

                writer.writerow(headers)

                # 获取所有时间点
                all_times = set()
                for pid, samples in active_samples.items():
                    for t, _ in samples:
                        all_times.add(t)

                all_times = sorted(all_times)
                start_time = min(all_times) if all_times else 0

                # 写入数据（统一四位小数，提高精度）
                for t in all_times:
                    row = [t, t - start_time]

                    for pid in active_samples:
                        samples = active_samples[pid]
                        if not samples:
                            row.append(0)
                            continue

                        # 找到最接近当前时间的样本
                        closest_sample = min(samples, key=lambda x: abs(x[0] - t))
                        row.append(closest_sample[1])

                    writer.writerow(row)

            messagebox.showinfo("保存成功", f"内存变化记录已保存到: {filename}")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存记录时出错: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MultiProcessMemoryMonitor(root)
    root.mainloop()
