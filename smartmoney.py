import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget
)

class ExcelVisualizer(QMainWindow):
    def __init__(self, file_path):
        super().__init__()
        self.setWindowTitle("台股期貨數據分析")
        self.setGeometry(100, 100, 1200, 800)
        
        # 读取 Excel 文件
        self.dfs = self.read_excel(file_path)
        
        # 创建标签页
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # 创建各工作表的可视化
        self.create_roll_cost_tab()
        self.create_retail_force_tab()
        self.create_institutional_tab()
        self.create_market_level_tab()
        self.create_future_position_tab()
        self.create_option_position_tab()

    def read_excel(self, file_path):
        """读取 Excel 文件中的所有工作表"""
        sheets_to_load = [
            "台指期換倉成本計算", "散戶多空力道", "微台多空力道",
            "三大法人買賣金額", "大盤多空點位",
            "期貨大額交易人未沖銷部位", "選擇權買賣權分計"
        ]
        
        dfs = {}
        for sheet in sheets_to_load:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet)
                dfs[sheet] = df
            except:
                print(f"警告: 工作表 '{sheet}' 未找到或读取失败")
        return dfs

    def create_roll_cost_tab(self):
        """创建换仓成本图表"""
        if "台指期換倉成本計算" not in self.dfs:
            return
            
        df = self.dfs["台指期換倉成本計算"]
        tab = QWidget()
        layout = QVBoxLayout()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 提取日期和成本数据
        dates = pd.to_datetime(df["日期"].str.extract(r'(\d{4}/\d{2}/\d{2})')[0])
        cost = df["成本"]
        
        # 绘制折线图
        ax.plot(dates, cost, 'b-o', linewidth=2, markersize=6)
        ax.set_title("台指期換倉成本趨勢", fontsize=14)
        ax.set_ylabel("成本", fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        fig.autofmt_xdate()
        
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "換倉成本")

    def create_retail_force_tab(self):
        """创建散户和微台多空力道图表"""
        if "散戶多空力道" not in self.dfs or "微台多空力道" not in self.dfs:
            return
            
        retail_df = self.dfs["散戶多空力道"]
        micro_df = self.dfs["微台多空力道"]
        tab = QWidget()
        layout = QVBoxLayout()
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # 提取散户数据
        retail_dates = pd.to_datetime(retail_df["日期"].str.extract(r'(\d{4}/\d{2}/\d{2})')[0])
        retail_force = retail_df["散戶多空力道"]
        
        # 提取微台数据
        micro_dates = pd.to_datetime(micro_df["日期"].str.extract(r'(\d{4}/\d{2}/\d{2})')[0])
        micro_force = micro_df["微台多空力道"]
        
        # 绘制散户力道直方图
        colors_retail = ['r' if x >= 0 else 'g' for x in retail_force]
        ax1.bar(retail_dates, retail_force, color=colors_retail, width=0.8)
        ax1.set_title("散戶多空力道", fontsize=12)
        ax1.grid(True, linestyle='--', alpha=0.7)
        fig.autofmt_xdate()
        
        # 绘制微台力道直方图
        colors_micro = ['r' if x >= 0 else 'g' for x in micro_force]
        ax2.bar(micro_dates, micro_force, color=colors_micro, width=0.8)
        ax2.set_title("微台多空力道", fontsize=12)
        ax2.grid(True, linestyle='--', alpha=0.7)
        fig.autofmt_xdate()
        
        fig.suptitle("散戶與微台多空力道分析", fontsize=16)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "散戶/微台力道")

    def create_institutional_tab(self):
        """创建三大法人买卖金额图表"""
        if "三大法人買賣金額" not in self.dfs:
            return
            
        df = self.dfs["三大法人買賣金額"]
        tab = QWidget()
        layout = QVBoxLayout()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 提取数据
        dates = df["日期"].str.extract(r'(\d{4}年\d{2}月\d{2}日)')[0]
        foreign = df["外資"]
        domestic = df["內資"]
        dealer = df["自營商(避險)"]
        
        # 设置位置和宽度
        x = np.arange(len(dates))
        width = 0.25
        
        # 绘制分组直方图
        rects1 = ax.bar(x - width, foreign, width, label='外資', 
                       color=['r' if val >= 0 else 'g' for val in foreign])
        rects2 = ax.bar(x, domestic, width, label='內資',
                       color=['r' if val >= 0 else 'g' for val in domestic])
        rects3 = ax.bar(x + width, dealer, width, label='自營商(避險)',
                       color=['r' if val >= 0 else 'g' for val in dealer])
        
        ax.set_title("三大法人買賣金額", fontsize=14)
        ax.set_ylabel("金額", fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(dates, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7)
        
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "三大法人")

    def create_market_level_tab(self):
        """创建大盤多空點位图表"""
        if "大盤多空點位" not in self.dfs:
            return
            
        df = self.dfs["大盤多空點位"]
        tab = QWidget()
        layout = QVBoxLayout()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 提取数据
        dates = pd.to_datetime(df["日期"].str.extract(r'(\d{4}年\d{2}月\d{2}日)')[0])
        levels = df["隔日多空點位"]
        
        # 绘制折线图
        ax.plot(dates, levels, 'm-', linewidth=2)
        ax.fill_between(dates, levels.min(), levels, alpha=0.2, color='purple')
        ax.set_title("大盤多空點位趨勢", fontsize=14)
        ax.set_ylabel("點位", fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        fig.autofmt_xdate()
        
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "大盤點位")

    def create_future_position_tab(self):
        """创建期貨大額交易人部位图表"""
        if "期貨大額交易人未沖銷部位" not in self.dfs:
            return
            
        df = self.dfs["期貨大額交易人未沖銷部位"]
        tab = QWidget()
        layout = QVBoxLayout()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 提取数据
        dates = pd.to_datetime(df["日期"].str.extract(r'(\d{4}/\d{2}/\d{2})')[0])
        
        # 检查列是否存在
        if "九大多空淨額增減" in df.columns and "外資交易多空淨額" in df.columns:
            top9 = df["九大多空淨額增減"]
            foreign = df["外資交易多空淨額"]
            
            # 设置位置和宽度
            x = np.arange(len(dates))
            width = 0.35
            
            # 绘制分组直方图
            rects1 = ax.bar(x - width/2, top9, width, label='九大多空淨額增減',
                           color=['r' if val >= 0 else 'g' for val in top9])
            rects2 = ax.bar(x + width/2, foreign, width, label='外資交易多空淨額',
                           color=['r' if val >= 0 else 'g' for val in foreign])
            
            ax.set_title("期貨大額交易人未沖銷部位", fontsize=14)
            ax.set_ylabel("部位", fontsize=12)
            ax.set_xticks(x)
            ax.set_xticklabels(dates.dt.strftime('%Y-%m-%d'), rotation=45, ha='right')
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.7)
        else:
            ax.text(0.5, 0.5, "缺少所需數據列", ha='center', va='center', fontsize=16)
        
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "期貨部位")

    def create_option_position_tab(self):
        """创建选择权买卖权分计图表"""
        if "選擇權買賣權分計" not in self.dfs:
            return
            
        df = self.dfs["選擇權買賣權分計"]
        tab = QWidget()
        layout = QVBoxLayout()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 提取数据
        dates = pd.to_datetime(df["日期"].str.extract(r'(\d{4}/\d{2}/\d{2})')[0])
        
        # 检查列是否存在
        if "外資" in df.columns and "自營商" in df.columns:
            foreign = df["外資"]
            dealer = df["自營商"]
            
            # 设置位置和宽度
            x = np.arange(len(dates))
            width = 0.35
            
            # 绘制分组直方图
            rects1 = ax.bar(x - width/2, foreign, width, label='外資',
                           color=['r' if val >= 0 else 'g' for val in foreign])
            rects2 = ax.bar(x + width/2, dealer, width, label='自營商',
                           color=['r' if val >= 0 else 'g' for val in dealer])
            
            ax.set_title("選擇權買賣權分計", fontsize=14)
            ax.set_ylabel("金額", fontsize=12)
            ax.set_xticks(x)
            ax.set_xticklabels(dates.dt.strftime('%Y-%m-%d'), rotation=45, ha='right')
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.7)
        else:
            ax.text(0.5, 0.5, "缺少所需數據列", ha='center', va='center', fontsize=16)
        
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "選擇權部位")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    file_path = "everyday_ver2.xlsx"  # 更改为实际文件路径
    window = ExcelVisualizer(file_path)
    window.show()
    sys.exit(app.exec_())