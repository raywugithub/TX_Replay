import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class IntradayAdvisor:
    def __init__(self, master):
        self.master = master
        master.title("当冲日内交易顾问")
        master.geometry("1200x800")
        
        # 创建标签框架
        self.setup_frame = ttk.LabelFrame(master, text="设置", padding=10)
        self.setup_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.result_frame = ttk.LabelFrame(master, text="结果分析", padding=10)
        self.result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 初始化数据
        self.data_loaded = False
        self.prob_df = None
        self.detailed_df = None
        
        # 创建UI控件
        self.create_controls()
        
        # 尝试自动加载数据
        self.try_load_data()
    
    def create_controls(self):
        # 数据加载部分
        ttk.Label(self.setup_frame, text="数据文件路径:").grid(row=0, column=0, sticky=tk.W)
        
        self.data_path_var = tk.StringVar(value="segment_probability_analysis.csv")
        ttk.Entry(self.setup_frame, textvariable=self.data_path_var, width=50).grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(self.setup_frame, text="详细数据文件:").grid(row=1, column=0, sticky=tk.W)
        
        self.detailed_path_var = tk.StringVar(value="segment_detailed_dates.csv")
        ttk.Entry(self.setup_frame, textvariable=self.detailed_path_var, width=50).grid(row=1, column=1, sticky=tk.W)
        
        ttk.Button(self.setup_frame, text="加载数据", command=self.load_data).grid(row=1, column=2, padx=5)
        
        # 分隔线
        ttk.Separator(self.setup_frame, orient='horizontal').grid(row=2, column=0, columnspan=3, pady=10, sticky=tk.EW)
        
        # 交易时段选择
        ttk.Label(self.setup_frame, text="当前交易时段:").grid(row=3, column=0, sticky=tk.W)
        
        self.time_var = tk.StringVar(value="9:15")
        time_combo = ttk.Combobox(self.setup_frame, textvariable=self.time_var, 
                                 values=["8:45", "9:15", "9:45", "10:00", "13:00"], width=10)
        time_combo.grid(row=3, column=1, sticky=tk.W)
        time_combo.bind("<<ComboboxSelected>>", self.update_selection_ui)
        
        # 初始化选择框
        self.create_selection_ui()
        
        # 查询按钮
        ttk.Button(self.setup_frame, text="查询概率", command=self.query_probabilities).grid(row=10, column=0, pady=10)
        ttk.Button(self.setup_frame, text="重置选择", command=self.reset_selection).grid(row=10, column=1, pady=10)
        
        # 结果部分
        self.result_text = tk.Text(self.result_frame, height=15, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 图表框架
        self.chart_frame = ttk.Frame(self.result_frame)
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_selection_ui(self):
        # 创建选择框架
        self.selection_frame = ttk.Frame(self.setup_frame)
        self.selection_frame.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # 第一时段选择
        ttk.Label(self.selection_frame, text="开盘时段 (8:45-9:15):").grid(row=0, column=0, sticky=tk.W)
        
        self.ft_class_var = tk.StringVar()
        ft_class_combo = ttk.Combobox(self.selection_frame, textvariable=self.ft_class_var, 
                                     values=["", "Low", "Medium", "High"], width=10)
        ft_class_combo.grid(row=0, column=1, padx=5)
        
        self.ft_change_var = tk.StringVar()
        ft_change_combo = ttk.Combobox(self.selection_frame, textvariable=self.ft_change_var, 
                                      values=["", "Up", "Down", "Flat"], width=10)
        ft_change_combo.grid(row=0, column=2, padx=5)
        
        # 第二时段选择
        ttk.Label(self.selection_frame, text="中间时段 (9:15-9:45):").grid(row=1, column=0, sticky=tk.W)
        
        self.st_class_var = tk.StringVar()
        st_class_combo = ttk.Combobox(self.selection_frame, textvariable=self.st_class_var, 
                                     values=["", "Low", "Medium", "High"], width=10)
        st_class_combo.grid(row=1, column=1, padx=5)
        
        self.st_change_var = tk.StringVar()
        st_change_combo = ttk.Combobox(self.selection_frame, textvariable=self.st_change_var, 
                                      values=["", "Up", "Down", "Flat"], width=10)
        st_change_combo.grid(row=1, column=2, padx=5)
        
        # 第三时段选择
        ttk.Label(self.selection_frame, text="收盘时段 (9:45-13:45):").grid(row=2, column=0, sticky=tk.W)
        
        self.tt_class_var = tk.StringVar()
        tt_class_combo = ttk.Combobox(self.selection_frame, textvariable=self.tt_class_var, 
                                     values=["", "Low", "Medium", "High"], width=10)
        tt_class_combo.grid(row=2, column=1, padx=5)
        
        self.tt_change_var = tk.StringVar()
        tt_change_combo = ttk.Combobox(self.selection_frame, textvariable=self.tt_change_var, 
                                      values=["", "Up", "Down", "Flat"], width=10)
        tt_change_combo.grid(row=2, column=2, padx=5)
        
        # 高低点选择
        ttk.Label(self.selection_frame, text="高低点特征:").grid(row=3, column=0, sticky=tk.W)
        
        self.high_point_var = tk.StringVar()
        high_point_combo = ttk.Combobox(self.selection_frame, textvariable=self.high_point_var, 
                                       values=["", "创全日最高", "未创全日最高"], width=15)
        high_point_combo.grid(row=3, column=1, padx=5)
        
        self.low_point_var = tk.StringVar()
        low_point_combo = ttk.Combobox(self.selection_frame, textvariable=self.low_point_var, 
                                      values=["", "创全日最低", "未创全日最低"], width=15)
        low_point_combo.grid(row=3, column=2, padx=5)
    
    def update_selection_ui(self, event=None):
        current_time = self.time_var.get()
        
        # 根据当前时间禁用相关选择
        if current_time == "8:45":
            # 开盘前，禁用所有选择
            self.disable_all_selections()
        elif current_time == "9:15":
            # 开盘时段结束，只能选择开盘时段
            self.enable_selection(0)  # 开盘时段
            self.disable_selection(1) # 中间时段
            self.disable_selection(2) # 收盘时段
            self.disable_selection(3) # 高低点
        elif current_time == "9:45":
            # 中间时段结束，可以选择开盘和中间时段
            self.enable_selection(0)  # 开盘时段
            self.enable_selection(1)  # 中间时段
            self.disable_selection(2) # 收盘时段
            self.disable_selection(3) # 高低点
        else:
            # 其他时间，可以全选
            self.enable_all_selections()
    
    def disable_all_selections(self):
        for i in range(4):  # 0-3: ft, st, tt, hl
            self.disable_selection(i)
    
    def enable_all_selections(self):
        for i in range(4):
            self.enable_selection(i)
    
    def disable_selection(self, index):
        if index == 0:  # 开盘时段
            self.ft_class_var.set("")
            self.ft_change_var.set("")
            self.ft_class_var.set("")
            self.ft_change_var.set("")
            self.set_combo_state(self.selection_frame.grid_slaves(row=0, column=1)[0], "disabled")
            self.set_combo_state(self.selection_frame.grid_slaves(row=0, column=2)[0], "disabled")
        elif index == 1:  # 中间时段
            self.st_class_var.set("")
            self.st_change_var.set("")
            self.set_combo_state(self.selection_frame.grid_slaves(row=1, column=1)[0], "disabled")
            self.set_combo_state(self.selection_frame.grid_slaves(row=1, column=2)[0], "disabled")
        elif index == 2:  # 收盘时段
            self.tt_class_var.set("")
            self.tt_change_var.set("")
            self.set_combo_state(self.selection_frame.grid_slaves(row=2, column=1)[0], "disabled")
            self.set_combo_state(self.selection_frame.grid_slaves(row=2, column=2)[0], "disabled")
        elif index == 3:  # 高低点
            self.high_point_var.set("")
            self.low_point_var.set("")
            self.set_combo_state(self.selection_frame.grid_slaves(row=3, column=1)[0], "disabled")
            self.set_combo_state(self.selection_frame.grid_slaves(row=3, column=2)[0], "disabled")
    
    def enable_selection(self, index):
        if index == 0:  # 开盘时段
            self.set_combo_state(self.selection_frame.grid_slaves(row=0, column=1)[0], "readonly")
            self.set_combo_state(self.selection_frame.grid_slaves(row=0, column=2)[0], "readonly")
        elif index == 1:  # 中间时段
            self.set_combo_state(self.selection_frame.grid_slaves(row=1, column=1)[0], "readonly")
            self.set_combo_state(self.selection_frame.grid_slaves(row=1, column=2)[0], "readonly")
        elif index == 2:  # 收盘时段
            self.set_combo_state(self.selection_frame.grid_slaves(row=2, column=1)[0], "readonly")
            self.set_combo_state(self.selection_frame.grid_slaves(row=2, column=2)[0], "readonly")
        elif index == 3:  # 高低点
            self.set_combo_state(self.selection_frame.grid_slaves(row=3, column=1)[0], "readonly")
            self.set_combo_state(self.selection_frame.grid_slaves(row=3, column=2)[0], "readonly")
    
    def set_combo_state(self, widget, state):
        if isinstance(widget, ttk.Combobox):
            widget.configure(state=state)
    
    def try_load_data(self):
        # 尝试加载数据文件
        prob_path = self.data_path_var.get()
        detailed_path = self.detailed_path_var.get()
        
        if os.path.exists(prob_path) and os.path.exists(detailed_path):
            try:
                self.prob_df = pd.read_csv(prob_path)
                self.detailed_df = pd.read_csv(detailed_path)
                self.data_loaded = True
                self.result_text.insert(tk.END, "数据加载成功!\n")
                self.result_text.insert(tk.END, f"找到 {len(self.prob_df)} 种组合模式\n")
                self.result_text.insert(tk.END, f"包含 {len(self.detailed_df)} 个交易日数据\n")
            except Exception as e:
                self.result_text.insert(tk.END, f"数据加载失败: {str(e)}\n")
                self.data_loaded = False
        else:
            self.result_text.insert(tk.END, "数据文件不存在，请加载数据\n")
            self.data_loaded = False
    
    def load_data(self):
        prob_path = self.data_path_var.get()
        detailed_path = self.detailed_path_var.get()
        
        if not os.path.exists(prob_path):
            messagebox.showerror("错误", f"文件不存在: {prob_path}")
            return
        
        if not os.path.exists(detailed_path):
            messagebox.showerror("错误", f"文件不存在: {detailed_path}")
            return
        
        try:
            self.prob_df = pd.read_csv(prob_path)
            self.detailed_df = pd.read_csv(detailed_path)
            self.data_loaded = True
            
            # 更新结果文本框
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "数据加载成功!\n")
            self.result_text.insert(tk.END, f"组合模式文件: {prob_path}\n")
            self.result_text.insert(tk.END, f"详细数据文件: {detailed_path}\n")
            self.result_text.insert(tk.END, f"找到 {len(self.prob_df)} 种组合模式\n")
            self.result_text.insert(tk.END, f"包含 {len(self.detailed_df)} 个交易日数据\n")
            
            # 更新选择框的值
            self.update_combo_values()
            
        except Exception as e:
            messagebox.showerror("错误", f"数据加载失败: {str(e)}")
            self.data_loaded = False
    
    def update_combo_values(self):
        # 更新选择框的值
        if self.data_loaded:
            # 开盘时段类别
            ft_classes = sorted(self.detailed_df['first_trade_class'].dropna().unique())
            self.set_combo_values(self.selection_frame.grid_slaves(row=0, column=1)[0], [""] + ft_classes)
            
            # 开盘时段变动
            ft_changes = sorted(self.detailed_df['first_trade_change'].dropna().unique())
            self.set_combo_values(self.selection_frame.grid_slaves(row=0, column=2)[0], [""] + ft_changes)
            
            # 中间时段类别
            st_classes = sorted(self.detailed_df['second_trade_class'].dropna().unique())
            self.set_combo_values(self.selection_frame.grid_slaves(row=1, column=1)[0], [""] + st_classes)
            
            # 中间时段变动
            st_changes = sorted(self.detailed_df['second_trade_change'].dropna().unique())
            self.set_combo_values(self.selection_frame.grid_slaves(row=1, column=2)[0], [""] + st_changes)
            
            # 收盘时段类别
            tt_classes = sorted(self.detailed_df['final_trade_class'].dropna().unique())
            self.set_combo_values(self.selection_frame.grid_slaves(row=2, column=1)[0], [""] + tt_classes)
            
            # 收盘时段变动
            tt_changes = sorted(self.detailed_df['final_trade_change'].dropna().unique())
            self.set_combo_values(self.selection_frame.grid_slaves(row=2, column=2)[0], [""] + tt_changes)
    
    def set_combo_values(self, combo, values):
        if isinstance(combo, ttk.Combobox):
            combo.configure(values=values)
    
    def reset_selection(self):
        # 重置所有选择
        self.ft_class_var.set("")
        self.ft_change_var.set("")
        self.st_class_var.set("")
        self.st_change_var.set("")
        self.tt_class_var.set("")
        self.tt_change_var.set("")
        self.high_point_var.set("")
        self.low_point_var.set("")
        
        # 根据当前时间更新UI状态
        self.update_selection_ui()
    
    def query_probabilities(self):
        if not self.data_loaded:
            messagebox.showwarning("警告", "请先加载数据")
            return
        
        # 获取当前选择
        current_time = self.time_var.get()
        
        # 根据当前时间执行不同的查询
        if current_time == "9:15":
            self.query_for_915()
        elif current_time == "9:45":
            self.query_for_945()
        else:
            self.query_general()
    
    def query_for_915(self):
        """9:15时的查询 - 开盘时段结束"""
        # 获取开盘时段选择
        ft_class = self.ft_class_var.get()
        ft_change = self.ft_change_var.get()
        
        if not ft_class or not ft_change:
            messagebox.showwarning("警告", "请选择开盘时段的类别和变动方向")
            return
        
        # 创建筛选条件
        ft_desc = f"{ft_class}({ft_change})"
        
        # 筛选数据
        condition = (self.detailed_df['first_trade_class'] == ft_class) & \
                   (self.detailed_df['first_trade_change'] == ft_change)
        
        subset = self.detailed_df[condition]
        
        if subset.empty:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"没有找到开盘时段为 {ft_desc} 的数据\n")
            return
        
        total_count = len(subset)
        
        # 计算中间时段的概率分布
        st_group = subset.groupby(['second_trade_class', 'second_trade_change']).size().reset_index(name='count')
        st_group['probability'] = st_group['count'] / total_count
        
        # 计算收盘时段的概率分布
        tt_group = subset.groupby(['final_trade_class', 'final_trade_change']).size().reset_index(name='count')
        tt_group['probability'] = tt_group['count'] / total_count
        
        # 计算创全日最高/最低点的概率
        high_prob = subset['final_high_is_daily_high'].mean()
        low_prob = subset['final_low_is_daily_low'].mean()
        
        # 显示结果
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"当前时间: 9:15 (开盘时段结束)\n")
        self.result_text.insert(tk.END, f"开盘时段: {ft_desc}\n")
        self.result_text.insert(tk.END, f"分析基于 {total_count} 个历史交易日\n\n")
        
        self.result_text.insert(tk.END, "中间时段 (9:15-9:45) 预测:\n")
        self.result_text.insert(tk.END, "类别\t变动\t概率\t\n")
        self.result_text.insert(tk.END, "-" * 40 + "\n")
        
        for _, row in st_group.sort_values('probability', ascending=False).iterrows():
            self.result_text.insert(tk.END, f"{row['second_trade_class']}\t{row['second_trade_change']}\t{row['probability']:.2%}\n")
        
        self.result_text.insert(tk.END, "\n收盘时段 (9:45-13:45) 预测:\n")
        self.result_text.insert(tk.END, "类别\t变动\t概率\t\n")
        self.result_text.insert(tk.END, "-" * 40 + "\n")
        
        for _, row in tt_group.sort_values('probability', ascending=False).iterrows():
            self.result_text.insert(tk.END, f"{row['final_trade_class']}\t{row['final_trade_change']}\t{row['probability']:.2%}\n")
        
        self.result_text.insert(tk.END, "\n高低点特征预测:\n")
        self.result_text.insert(tk.END, f"创全日最高点概率: {high_prob:.2%}\n")
        self.result_text.insert(tk.END, f"创全日最低点概率: {low_prob:.2%}\n")
        
        # 创建图表
        self.create_charts(st_group, tt_group, high_prob, low_prob, "9:15 时段预测")
    
    def query_for_945(self):
        """9:45时的查询 - 中间时段结束"""
        # 获取开盘和中间时段选择
        ft_class = self.ft_class_var.get()
        ft_change = self.ft_change_var.get()
        st_class = self.st_class_var.get()
        st_change = self.st_change_var.get()
        
        if not ft_class or not ft_change or not st_class or not st_change:
            messagebox.showwarning("警告", "请选择开盘时段和中间时段的类别及变动方向")
            return
        
        # 创建筛选条件
        ft_desc = f"{ft_class}({ft_change})"
        st_desc = f"{st_class}({st_change})"
        
        # 筛选数据
        condition = (self.detailed_df['first_trade_class'] == ft_class) & \
                   (self.detailed_df['first_trade_change'] == ft_change) & \
                   (self.detailed_df['second_trade_class'] == st_class) & \
                   (self.detailed_df['second_trade_change'] == st_change)
        
        subset = self.detailed_df[condition]
        
        if subset.empty:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"没有找到开盘时段为 {ft_desc} 且中间时段为 {st_desc} 的数据\n")
            return
        
        total_count = len(subset)
        
        # 计算收盘时段的概率分布
        tt_group = subset.groupby(['final_trade_class', 'final_trade_change']).size().reset_index(name='count')
        tt_group['probability'] = tt_group['count'] / total_count
        
        # 计算创全日最高/最低点的概率
        high_prob = subset['final_high_is_daily_high'].mean()
        low_prob = subset['final_low_is_daily_low'].mean()
        
        # 显示结果
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"当前时间: 9:45 (中间时段结束)\n")
        self.result_text.insert(tk.END, f"开盘时段: {ft_desc}\n")
        self.result_text.insert(tk.END, f"中间时段: {st_desc}\n")
        self.result_text.insert(tk.END, f"分析基于 {total_count} 个历史交易日\n\n")
        
        self.result_text.insert(tk.END, "收盘时段 (9:45-13:45) 预测:\n")
        self.result_text.insert(tk.END, "类别\t变动\t概率\t\n")
        self.result_text.insert(tk.END, "-" * 40 + "\n")
        
        for _, row in tt_group.sort_values('probability', ascending=False).iterrows():
            self.result_text.insert(tk.END, f"{row['final_trade_class']}\t{row['final_trade_change']}\t{row['probability']:.2%}\n")
        
        self.result_text.insert(tk.END, "\n高低点特征预测:\n")
        self.result_text.insert(tk.END, f"创全日最高点概率: {high_prob:.2%}\n")
        self.result_text.insert(tk.END, f"创全日最低点概率: {low_prob:.2%}\n")
        
        # 创建图表
        self.create_charts(None, tt_group, high_prob, low_prob, "9:45 时段预测")
    
    def query_general(self):
        """通用查询 - 任意时段"""
        # 获取所有选择
        ft_class = self.ft_class_var.get()
        ft_change = self.ft_change_var.get()
        st_class = self.st_class_var.get()
        st_change = self.st_change_var.get()
        tt_class = self.tt_class_var.get()
        tt_change = self.tt_change_var.get()
        high_point = self.high_point_var.get()
        low_point = self.low_point_var.get()
        
        # 创建筛选条件
        conditions = []
        
        if ft_class:
            conditions.append(self.detailed_df['first_trade_class'] == ft_class)
        if ft_change:
            conditions.append(self.detailed_df['first_trade_change'] == ft_change)
        if st_class:
            conditions.append(self.detailed_df['second_trade_class'] == st_class)
        if st_change:
            conditions.append(self.detailed_df['second_trade_change'] == st_change)
        if tt_class:
            conditions.append(self.detailed_df['final_trade_class'] == tt_class)
        if tt_change:
            conditions.append(self.detailed_df['final_trade_change'] == tt_change)
        if high_point:
            # 将中文转换为布尔值
            high_bool = (high_point == "创全日最高")
            conditions.append(self.detailed_df['final_high_is_daily_high'] == high_bool)
        if low_point:
            low_bool = (low_point == "创全日最低")
            conditions.append(self.detailed_df['final_low_is_daily_low'] == low_bool)
        
        if not conditions:
            messagebox.showwarning("警告", "请至少选择一个条件")
            return
        
        # 组合所有条件
        combined_condition = pd.Series(True, index=self.detailed_df.index)
        for cond in conditions:
            combined_condition &= cond
        
        subset = self.detailed_df[combined_condition]
        
        if subset.empty:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "没有找到匹配条件的数据\n")
            return
        
        total_count = len(subset)
        total_days = len(self.detailed_df)
        probability = total_count / total_days
        
        # 显示结果
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"当前时间: {self.time_var.get()}\n")
        
        if ft_class or ft_change:
            self.result_text.insert(tk.END, f"开盘时段: {ft_class or '任意'} ({ft_change or '任意'})\n")
        if st_class or st_change:
            self.result_text.insert(tk.END, f"中间时段: {st_class or '任意'} ({st_change or '任意'})\n")
        if tt_class or tt_change:
            self.result_text.insert(tk.END, f"收盘时段: {tt_class or '任意'} ({tt_change or '任意'})\n")
        if high_point:
            self.result_text.insert(tk.END, f"创全日最高点: {high_point}\n")
        if low_point:
            self.result_text.insert(tk.END, f"创全日最低点: {low_point}\n")
        
        self.result_text.insert(tk.END, f"\n匹配条件的天数: {total_count}\n")
        self.result_text.insert(tk.END, f"总天数: {total_days}\n")
        self.result_text.insert(tk.END, f"出现概率: {probability:.2%}\n")
        
        # 显示匹配的日期
        self.result_text.insert(tk.END, f"\n匹配日期: {', '.join(subset['date'].astype(str).tolist())}\n")
    
    def create_charts(self, st_group, tt_group, high_prob, low_prob, title):
        # 清除现有图表
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.suptitle(title, fontsize=16)
        
        # 第一图表：中间时段预测
        if st_group is not None:
            ax1 = axes[0]
            st_group['description'] = st_group['second_trade_class'] + '(' + st_group['second_trade_change'] + ')'
            st_group = st_group.sort_values('probability', ascending=False)
            
            colors = plt.cm.viridis(st_group['probability'] / st_group['probability'].max())
            bars = ax1.bar(st_group['description'], st_group['probability'], color=colors)
            
            ax1.set_title('9:15-9:45') # 中间时段预测
            ax1.set_ylabel('Probability') # 概率
            ax1.tick_params(axis='x', rotation=45)
            
            # 添加数值标签
            for bar in bars:
                height = bar.get_height()
                ax1.annotate(f'{height:.1%}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom')
        
        # 第二图表：收盘时段预测
        if tt_group is not None:
            ax2 = axes[1]
            tt_group['description'] = tt_group['final_trade_class'] + '(' + tt_group['final_trade_change'] + ')'
            tt_group = tt_group.sort_values('probability', ascending=False)
            
            colors = plt.cm.plasma(tt_group['probability'] / tt_group['probability'].max())
            bars = ax2.bar(tt_group['description'], tt_group['probability'], color=colors)
            
            ax2.set_title('9:45-13:45') # 收盘时段预测
            ax2.set_ylabel('Probability') # 概率
            ax2.tick_params(axis='x', rotation=45)
            
            # 添加数值标签
            for bar in bars:
                height = bar.get_height()
                ax2.annotate(f'{height:.1%}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom')
        
        # 第三图表：高低点预测
        ax3 = axes[2]
        labels = ['H Breakout', 'L Breakout'] # '创全日最高点', '创全日最低点'
        values = [high_prob, low_prob]
        colors = ['#ff9999', '#66b3ff']
        
        bars = ax3.bar(labels, values, color=colors)
        ax3.set_title('H/L Breakout') # 高低点预测
        ax3.set_ylabel('Probability') # 概率
        
        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            ax3.annotate(f'{height:.1%}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
        
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        
        # 嵌入图表到Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = IntradayAdvisor(root)
    root.mainloop()