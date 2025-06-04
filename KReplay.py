import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QPushButton, QHBoxLayout, QFileDialog, QLabel, 
                             QTextEdit, QSplitter, QMessageBox, QSpinBox)
from PyQt5.QtCore import QTimer, Qt
import mplfinance as mpf
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime
import matplotlib.pyplot as plt


class KLinePlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('股票K線模擬交易訓練軟體 (含強度指標)')
        self.setGeometry(100, 100, 1200, 1000)  # 增加高度以容納新指標
        
        # 數據相關變量
        self.df = None
        self.current_idx = 0
        self.playing = False
        self.speed = 500  # 預設播放速度(毫秒)
        self.has_strength = False  # 是否有強度指標
        
        # 交易相關變量
        self.trades = []
        self.positions = []
        self.trade_history = []
        
        # 自定義樣式
        self.style = mpf.make_marketcolors(
            up='red', down='green',
            wick={'up':'red', 'down':'green'},
            volume={'up':'red', 'down':'green'},
            edge={'up':'red', 'down':'green'},
            ohlc='i'
        )
        self.mp_style = mpf.make_mpf_style(marketcolors=self.style)
        
        self.init_ui()
        
    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        splitter = QSplitter(Qt.Vertical)
        
        # 上部份
        top_widget = QWidget()
        top_layout = QVBoxLayout()
        
        # 控制面板
        control_panel = QWidget()
        control_layout = QHBoxLayout()
        
        self.load_btn = QPushButton('載入K線數據')
        self.load_btn.clicked.connect(self.load_data)
        
        self.calc_avg_btn = QPushButton('計算均價')
        self.calc_avg_btn.clicked.connect(self.calculate_average_price)
        
        self.play_btn = QPushButton('開始')
        self.play_btn.clicked.connect(self.toggle_play)
        self.play_btn.setEnabled(False)
        
        self.step_btn = QPushButton('下一步')
        self.step_btn.clicked.connect(self.next_step)
        self.step_btn.setEnabled(False)
        
        self.buy_btn = QPushButton('買入/平空')
        self.buy_btn.clicked.connect(self.buy_action)
        self.buy_btn.setEnabled(False)
        
        self.sell_btn = QPushButton('賣出/做空')
        self.sell_btn.clicked.connect(self.sell_action)
        self.sell_btn.setEnabled(False)
        
        self.result_btn = QPushButton('交易結果')
        self.result_btn.clicked.connect(self.show_results)
        self.result_btn.setEnabled(False)
        
        # 速度調整控制
        self.speed_label = QLabel('速度(ms):')
        self.speed_spinbox = QSpinBox()
        self.speed_spinbox.setRange(100, 5000)  # 設置範圍100-5000毫秒
        self.speed_spinbox.setValue(self.speed)
        self.speed_spinbox.setSingleStep(100)  # 每次增減100毫秒
        self.speed_spinbox.valueChanged.connect(self.update_speed)
        
        control_layout.addWidget(self.load_btn)
        control_layout.addWidget(self.calc_avg_btn)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.step_btn)
        control_layout.addWidget(self.buy_btn)
        control_layout.addWidget(self.sell_btn)
        control_layout.addWidget(self.result_btn)
        control_layout.addWidget(self.speed_label)
        control_layout.addWidget(self.speed_spinbox)
        control_layout.addStretch()
        
        control_panel.setLayout(control_layout)
        
        # K線圖區域 - 增加一個軸用於顯示強度指標
        self.figure = Figure(figsize=(12, 7))
        self.canvas = FigureCanvas(self.figure)
        
        # 創建子圖佈局 (5:1:1比例)
        self.ax1 = self.figure.add_subplot(6, 1, (1, 4))  # K線圖
        self.ax2 = self.figure.add_subplot(6, 1, 5, sharex=self.ax1)  # 成交量
        self.ax3 = self.figure.add_subplot(6, 1, 6, sharex=self.ax1)  # 強度指標
        
        # 添加到上部佈局
        top_layout.addWidget(control_panel)
        top_layout.addWidget(self.canvas)
        top_widget.setLayout(top_layout)
        
        # 下部份
        self.trade_log = QTextEdit()
        self.trade_log.setReadOnly(True)
        self.trade_log.setPlaceholderText('交易記錄將顯示在這裡...')
        
        splitter.addWidget(top_widget)
        splitter.addWidget(self.trade_log)
        splitter.setSizes([750, 250])  # 調整比例
        
        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_step)
    
    def update_speed(self, value):
        """更新播放速度"""
        self.speed = value
        if self.playing:
            self.timer.setInterval(self.speed)
        self.log_trade(f"播放速度已調整為: {self.speed}毫秒")
    
    def calculate_average_price(self):
        """計算加權平均價"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, '選擇要計算均價的數據文件', '', 'CSV文件 (*.csv)')
        
        if not file_path:
            return
            
        try:
            # 讀取數據文件
            df = pd.read_csv(file_path)
            
            # 檢查必要欄位
            if 'Close' not in df.columns or 'Volume' not in df.columns:
                raise ValueError("數據文件必須包含 Close 和 Volume 欄位")
            
            # 計算加權平均價
            total_value = (df['Close'] * df['Volume']).sum()
            total_volume = df['Volume'].sum()
            
            if total_volume == 0:
                raise ValueError("總成交量為0，無法計算均價")
                
            average_price = total_value / total_volume
            
            # 获取Close列的最后一个值
            last_close = df['Close'].iloc[-1]

            today = df['Date'].iloc[-1].split(' ')[0]
            
            # 計算最高價和最低價
            highest_price = df['Close'].max()
            lowest_price = df['Close'].min()

            # 顯示結果
            result_msg = f"{today} 加權平均價計算結果:\n\n"
            # result_msg += f"Close*Volume 總和: {total_value:.2f}\n"
            # result_msg += f"Volume 總和: {total_volume:.2f}\n"
            result_msg += f"加權平均價: {average_price:.2f}\n"
            result_msg += f"昨收: {last_close} , 昨高: {highest_price}, 昨低: {lowest_price}"
            
            # QMessageBox.information(self, "均價計算結果", result_msg)
            self.log_trade(f"\n[均價計算] {result_msg}")
            
        except Exception as e:
            QMessageBox.critical(self, "計算錯誤", f"計算均價時發生錯誤: {str(e)}")
            self.log_trade(f"\n[均價計算錯誤] {str(e)}")
    
    def update_price_labels(self, display_df):
        """更新價格標籤"""
        if len(display_df) > 0:
            current_high = display_df['High'].max()
            current_low = display_df['Low'].min()
            current_close = display_df.iloc[-1]['Close']
            
            # 清除舊標籤
            for artist in self.ax1.texts:
                artist.remove()
            
            # 添加新標籤
            self.ax1.text(1.00, 0.95, f'INT: {current_high-current_low:.2f}', 
                         transform=self.ax1.transAxes, color='orange',
                         bbox=dict(facecolor='white', alpha=0.7))
            self.ax1.text(1.00, 0.90, f'HIGH: {current_high:.2f}', 
                         transform=self.ax1.transAxes, color='red',
                         bbox=dict(facecolor='white', alpha=0.7))
            self.ax1.text(1.00, 0.85, f'LOW: {current_low:.2f}', 
                         transform=self.ax1.transAxes, color='green',
                         bbox=dict(facecolor='white', alpha=0.7))
            self.ax1.text(1.00, 0.80, f'Close: {current_close:.2f}', 
                         transform=self.ax1.transAxes, color='blue',
                         bbox=dict(facecolor='white', alpha=0.7))
            # # 添加速度顯示標籤
            # self.ax1.text(0.01, 0.80, f'播放速度: {self.speed}ms', 
            #              transform=self.ax1.transAxes, color='black',
            #              bbox=dict(facecolor='white', alpha=0.7))

            # 如果存在均價欄位，顯示最後均價
            if 'Average' in display_df.columns:
                current_avg = display_df.iloc[-1]['Average']
                self.ax1.text(1.00, 0.75, f'最新均價: {current_avg:.2f}', 
                             transform=self.ax1.transAxes, color='purple',
                             bbox=dict(facecolor='white', alpha=0.7))
            
            # 如果存在強度欄位，顯示最後強度
            if self.has_strength:
                current_strength = display_df.iloc[-1]['strength']
                # 根據正負值選擇顏色
                strength_color = 'red' if current_strength >= 0 else 'green'
                self.ax1.text(1.00, 0.70, f'最新強度: {current_strength:.2f}', 
                             transform=self.ax1.transAxes, color=strength_color,
                             bbox=dict(facecolor='white', alpha=0.7))

    def load_data(self):
        """載入K線數據"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, '選擇股票K線數據文件', '', 'CSV文件 (*.csv);;Excel文件 (*.xlsx)')
        
        if not file_path:
            return
            
        try:
            # 讀取數據文件
            if file_path.endswith('.csv'):
                self.df = pd.read_csv(file_path, parse_dates=['Date'], index_col='Date')
            else:
                self.df = pd.read_excel(file_path, parse_dates=['Date'], index_col='Date')
                
            # 確保數據包含必要的列
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_cols:
                if col not in self.df.columns:
                    raise ValueError(f"數據文件中缺少必要的列: {col}")
            
            # 檢查是否有Average欄位
            if 'Average' not in self.df.columns:
                self.log_trade("警告: 數據文件中缺少Average欄位，將無法繪製均價線")
            
            # 檢查是否有strength欄位
            self.has_strength = 'strength' in self.df.columns
            if self.has_strength:
                self.log_trade("數據文件中包含strength欄位，將繪製強度指標")
            else:
                self.log_trade("警告: 數據文件中缺少strength欄位，將無法繪製強度指標")
                    
            # 重置狀態
            self.current_idx = 0
            self.playing = False
            self.timer.stop()
            self.trades = []
            self.positions = []
            self.trade_history = []
            self.trade_log.clear()
            
            # 啟用控制按鈕
            self.play_btn.setEnabled(True)
            self.step_btn.setEnabled(True)
            self.buy_btn.setEnabled(True)
            self.sell_btn.setEnabled(True)
            self.result_btn.setEnabled(True)
            self.play_btn.setText('開始')
            
            # 顯示初始K線
            self.update_chart()
            self.log_trade(f"已載入K線數據: {file_path}")

            self.speed_spinbox.setValue(500)
            
        except Exception as e:
            QMessageBox.critical(self, "載入錯誤", f"載入數據時發生錯誤: {str(e)}")
            self.log_trade(f"\n[載入錯誤] {str(e)}")
    
    def toggle_play(self):
        if self.df is not None and not self.df.empty:
            self.playing = not self.playing
            if self.playing:
                self.play_btn.setText('暫停')
                self.timer.start(self.speed)
            else:
                self.play_btn.setText('開始')
                self.timer.stop()
            self.update_chart()
    
    def next_step(self):
        if self.df is not None and self.current_idx < len(self.df):
            self.current_idx += 1
            self.update_chart()
            
            # 如果到達末尾，停止播放
            if self.current_idx >= len(self.df):
                self.playing = False
                self.play_btn.setText('開始')
                self.timer.stop()

    def update_chart(self):
        if self.df is not None and self.current_idx > 0:
            display_df = self.df.iloc[:self.current_idx].copy()
            
            # 清除圖表
            self.ax1.clear()
            self.ax2.clear()
            if self.has_strength:
                self.ax3.clear()
            
            # 繪製K線圖
            mpf.plot(display_df, 
                    type='candle', 
                    ax=self.ax1, 
                    volume=self.ax2, 
                    style=self.mp_style,
                    datetime_format='%Y-%m-%d %H:%M',
                    show_nontrading=True,
                    axtitle=f'K線重播 (共 {len(self.df)} 根K線, 當前 {self.current_idx} 根)')
            
            # 繪製均價線 (如果數據中存在Average欄位)
            if 'Average' in display_df.columns:
                self.ax1.plot(display_df.index, display_df['Average'], 
                             color='purple', linestyle='-', linewidth=1.5, 
                             label='均價線', alpha=0.7)
                self.ax1.legend(loc='best')  # 添加圖例
            
            # 繪製強度指標 (如果存在)
            if self.has_strength:
                # 分離正負值
                positive = display_df[display_df['strength'] >= 0]
                negative = display_df[display_df['strength'] < 0]

                # 計算強度值的範圍用於設置y軸
                strength_min = display_df['strength'].min() * 0.9
                strength_max = display_df['strength'].max() * 1.1
                
                # 繪製柱狀圖
                if not positive.empty:
                    self.ax3.bar(positive.index, positive['strength'], 
                                width=0.0005, color='red', alpha=0.7)
                if not negative.empty:
                    self.ax3.bar(negative.index, negative['strength'], 
                                width=0.0005, color='green', alpha=0.7)
                
                # 設置標題和範圍
                self.ax3.set_ylabel('強度指標')
                self.ax3.set_ylim(strength_min, strength_max)
                
                # 添加零線
                self.ax3.axhline(0, color='gray', linestyle='-', linewidth=0.5)
            
            # 更新價格標籤
            self.update_price_labels(display_df)
            
            # 標記交易點
            for trade in self.trades:
                trade_time = trade['time']
                trade_price = trade['price']
                x_pos = mdates.date2num(trade_time)
                
                if trade['action'] in ('buy', 'buy_to_cover'):
                    self.ax1.plot(x_pos, trade_price, 'g^', markersize=10)
                elif trade['action'] in ('sell', 'sell_short', 'sell_to_close'):
                    self.ax1.plot(x_pos, trade_price, 'rv', markersize=10)

            # 設置時間軸格式
            for ax in [self.ax1, self.ax2, self.ax3]:
                # 旋轉刻度標籤
                ax.tick_params(axis='x', rotation=90)

                # 設置日期格式
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

                # 調整標籤對齊方式
                for label in ax.get_xticklabels():
                    label.set_horizontalalignment('right')

            # 自動調整刻度間距
            self.ax1.xaxis.set_major_locator(mdates.AutoDateLocator())

            self.ax2.set_ylabel('成交量')
            self.figure.subplots_adjust(hspace=0.25)  # 調整子圖間距
            self.canvas.draw_idle()
    
    def buy_action(self):
        if self.df is not None and self.current_idx > 0:
            current_price = self.df.iloc[self.current_idx-1]['Close']
            
            # 檢查是否有做空持倉需要平倉
            short_positions = [p for p in self.positions if p['type'] == 'short']
            if short_positions:
                position = short_positions[0]
                price_diff = position['entry_price'] - current_price
                profit_pct = (price_diff / position['entry_price']) * 100
                
                self.trades.append({
                    'action': 'buy_to_cover',
                    'price': current_price,
                    'time': self.df.index[self.current_idx-1],
                    'index': self.current_idx-1
                })
                
                self.trade_history.append({
                    'type': 'short',
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'entry_time': position['entry_time'],
                    'exit_time': self.df.index[self.current_idx-1],
                    'profit_pct': profit_pct,
                    'profit_points': price_diff
                })
                
                self.positions.remove(position)
                self.log_trade(f"平空 @ {current_price:.2f} (盈虧: {profit_pct:.2f}% / {price_diff:.2f}點)")
            else:
                self.positions.append({
                    'type': 'long',
                    'entry_price': current_price,
                    'entry_time': self.df.index[self.current_idx-1],
                    'entry_index': self.current_idx-1
                })
                self.trades.append({
                    'action': 'buy',
                    'price': current_price,
                    'time': self.df.index[self.current_idx-1],
                    'index': self.current_idx-1
                })
                self.log_trade(f"買入 @ {current_price:.2f}")
            
            self.update_chart()
            
    def sell_action(self):
        if self.df is not None and self.current_idx > 0:
            current_price = self.df.iloc[self.current_idx-1]['Close']
            
            # 檢查是否有多頭持倉需要平倉
            long_positions = [p for p in self.positions if p['type'] == 'long']
            if long_positions:
                position = long_positions[0]
                price_diff = current_price - position['entry_price']
                profit_pct = (price_diff / position['entry_price']) * 100
                
                self.trades.append({
                    'action': 'sell_to_close',
                    'price': current_price,
                    'time': self.df.index[self.current_idx-1],
                    'index': self.current_idx-1
                })
                
                self.trade_history.append({
                    'type': 'long',
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'entry_time': position['entry_time'],
                    'exit_time': self.df.index[self.current_idx-1],
                    'profit_pct': profit_pct,
                    'profit_points': price_diff
                })
                
                self.positions.remove(position)
                self.log_trade(f"賣出 @ {current_price:.2f} (盈虧: {profit_pct:.2f}% / {price_diff:.2f}點)")
            else:
                self.positions.append({
                    'type': 'short',
                    'entry_price': current_price,
                    'entry_time': self.df.index[self.current_idx-1],
                    'entry_index': self.current_idx-1
                })
                self.trades.append({
                    'action': 'sell_short',
                    'price': current_price,
                    'time': self.df.index[self.current_idx-1],
                    'index': self.current_idx-1
                })
                self.log_trade(f"做空 @ {current_price:.2f}")
            
            self.update_chart()
            
    def show_results(self):
        if not self.trade_history:
            self.log_trade("尚未完成任何交易")
            return
            
        total_trades = len(self.trade_history)
        winning_trades = len([t for t in self.trade_history if t['profit_points'] > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        avg_profit_pct = sum(t['profit_pct'] for t in self.trade_history) / total_trades
        avg_profit_points = sum(t['profit_points'] for t in self.trade_history) / total_trades
        total_profit_points = sum(t['profit_points'] for t in self.trade_history)
        
        result_text = "\n=== 交易結果 ===\n"
        result_text += f"總交易次數: {total_trades}\n"
        result_text += f"盈利次數: {winning_trades}\n"
        result_text += f"虧損次數: {losing_trades}\n"
        result_text += f"勝率: {win_rate:.2f}%\n"
        result_text += f"平均報酬率: {avg_profit_pct:.2f}%\n"
        result_text += f"平均盈虧點數: {avg_profit_points:.2f}點\n"
        result_text += f"總盈虧點數: {total_profit_points:.2f}點\n"
        
        for i, trade in enumerate(self.trade_history, 1):
            trade_type = "多頭" if trade['type'] == 'long' else "空頭"
            result_text += (f"\n交易 #{i} ({trade_type}):\n"
                          f"進場價: {trade['entry_price']:.2f} @ {trade['entry_time']}\n"
                          f"出場價: {trade['exit_price']:.2f} @ {trade['exit_time']}\n"
                          f"報酬率: {trade['profit_pct']:.2f}%\n"
                          f"盈虧點數: {trade['profit_points']:.2f}點\n")
        
        self.log_trade(result_text)
    
    def log_trade(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.trade_log.append(f"[{timestamp}] {message}")

    def closeEvent(self, event):
        # 確保停止定時器
        self.timer.stop()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = KLinePlayer()
    player.show()
    sys.exit(app.exec_())