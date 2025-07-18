import sys
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QPushButton, QHBoxLayout, QFileDialog, QLabel, 
                             QTextEdit, QSplitter)
from PyQt5.QtCore import QTimer, Qt
import mplfinance as mpf
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime


class KLinePlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('股票K線模擬交易訓練軟體 (支持做空)')
        self.setGeometry(100, 100, 1200, 900)
        
        # 數據相關變量
        self.df = None
        self.current_idx = 0
        self.playing = False
        self.speed = 500  # 播放速度(毫秒)
        
        # 交易相關變量
        self.trades = []
        self.positions = []  # 支持多個持倉
        self.trade_history = []
        
        # 自定義樣式 (紅漲綠跌)
        self.style = mpf.make_marketcolors(
            up='red',       # 上漲為紅色
            down='green',   # 下跌為綠色
            wick={'up':'red', 'down':'green'},
            volume={'up':'red', 'down':'green'},
            edge={'up':'red', 'down':'green'},
            ohlc='i'       # 使用實體K線
        )
        self.mp_style = mpf.make_mpf_style(marketcolors=self.style)
        
        # 初始化UI
        self.init_ui()
        
    def init_ui(self):
        # 主部件和佈局
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # 使用分割器讓交易記錄可調整大小
        splitter = QSplitter(Qt.Vertical)
        
        # 上部份 - 圖表和控制面板
        top_widget = QWidget()
        top_layout = QVBoxLayout()
        
        # 控制面板
        control_panel = QWidget()
        control_layout = QHBoxLayout()
        
        # 控制按鈕
        self.load_btn = QPushButton('載入數據')
        self.load_btn.clicked.connect(self.load_data)
        
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
        
        self.speed_label = QLabel(f'速度: {self.speed}ms')
        
        # 添加到控制佈局
        control_layout.addWidget(self.load_btn)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.step_btn)
        control_layout.addWidget(self.buy_btn)
        control_layout.addWidget(self.sell_btn)
        control_layout.addWidget(self.result_btn)
        control_layout.addWidget(self.speed_label)
        control_layout.addStretch()
        
        control_panel.setLayout(control_layout)
        
        # K線圖區域 - 使用新的繪圖方式
        self.figure = Figure(figsize=(12, 6))
        self.canvas = FigureCanvas(self.figure)
        self.ax1 = self.figure.add_subplot(4, 1, (1, 3))
        self.ax2 = self.figure.add_subplot(4, 1, 4, sharex=self.ax1)
        
        # 添加到上部佈局
        top_layout.addWidget(control_panel)
        top_layout.addWidget(self.canvas)
        top_widget.setLayout(top_layout)
        
        # 下部份 - 交易記錄
        self.trade_log = QTextEdit()
        self.trade_log.setReadOnly(True)
        self.trade_log.setPlaceholderText('交易記錄將顯示在這裡...')
        
        # 添加到分割器
        splitter.addWidget(top_widget)
        splitter.addWidget(self.trade_log)
        splitter.setSizes([700, 200])
        
        # 添加到主佈局
        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # 定時器
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_step)
        
    def load_data(self):
        # 打開文件對話框選擇數據文件
        file_path, _ = QFileDialog.getOpenFileName(
            self, '選擇股票數據文件', '', 'CSV文件 (*.csv);;Excel文件 (*.xlsx)')
        
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
            
        except Exception as e:
            print(f"載入數據錯誤: {e}")
            
    def toggle_play(self):
        if self.df is not None and not self.df.empty:
            self.playing = not self.playing
            if self.playing:
                self.play_btn.setText('暫停')
                self.timer.start(self.speed)
            else:
                self.play_btn.setText('開始')
                self.timer.stop()
                
    def next_step(self):
        if self.df is not None and self.current_idx < len(self.df):
            self.current_idx += 1
            self.update_chart()
            
            # 如果到達末尾，停止播放
            if self.current_idx >= len(self.df):
                self.playing = False
                self.play_btn.setText('開始')
                self.timer.stop()
                
    def buy_action(self):
        if self.df is not None and self.current_idx > 0:
            current_price = self.df.iloc[self.current_idx-1]['Close']
            
            # 檢查是否有做空持倉需要平倉
            short_positions = [p for p in self.positions if p['type'] == 'short']
            if short_positions:
                # 平掉最早的做空倉位
                position = short_positions[0]
                profit_pct = ((position['entry_price'] - current_price) / 
                             position['entry_price']) * 100
                
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
                    'profit_pct': profit_pct
                })
                
                self.positions.remove(position)
                self.log_trade(f"平空 @ {current_price:.2f} (盈虧: {profit_pct:.2f}%)")
            else:
                # 新建多頭持倉
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
                # 平掉最早的多頭倉位
                position = long_positions[0]
                profit_pct = ((current_price - position['entry_price']) / 
                             position['entry_price']) * 100
                
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
                    'profit_pct': profit_pct
                })
                
                self.positions.remove(position)
                self.log_trade(f"賣出 @ {current_price:.2f} (盈虧: {profit_pct:.2f}%)")
            else:
                # 新建空頭持倉
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
        winning_trades = len([t for t in self.trade_history if t['profit_pct'] > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        avg_profit = sum(t['profit_pct'] for t in self.trade_history) / total_trades
        
        result_text = "\n=== 交易結果 ===\n"
        result_text += f"總交易次數: {total_trades}\n"
        result_text += f"盈利次數: {winning_trades}\n"
        result_text += f"虧損次數: {losing_trades}\n"
        result_text += f"勝率: {win_rate:.2f}%\n"
        result_text += f"平均報酬率: {avg_profit:.2f}%\n"
        
        for i, trade in enumerate(self.trade_history, 1):
            trade_type = "多頭" if trade['type'] == 'long' else "空頭"
            result_text += (f"\n交易 #{i} ({trade_type}):\n"
                          f"進場價: {trade['entry_price']:.2f} @ {trade['entry_time']}\n"
                          f"出場價: {trade['exit_price']:.2f} @ {trade['exit_time']}\n"
                          f"報酬率: {trade['profit_pct']:.2f}%\n")
        
        self.log_trade(result_text)
        
    def log_trade(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.trade_log.append(f"[{timestamp}] {message}")
        
    def update_chart(self):
        if self.df is not None and self.current_idx > 0:
            # 獲取當前要顯示的數據
            display_df = self.df.iloc[:self.current_idx].copy()
            
            # 清除之前的圖表
            self.ax1.clear()
            self.ax2.clear()
            
            # 繪製K線圖 - 使用新的繪圖方式
            mpf.plot(display_df, 
                    type='candle', 
                    ax=self.ax1, 
                    volume=self.ax2, 
                    style=self.mp_style,
                    datetime_format='%Y-%m-%d %H:%M',
                    show_nontrading=True,
                    update_width_config=dict(candle_linewidth=1.0),
                    warn_too_much_data=len(display_df)+1)
            
            # 設置標題
            self.ax1.set_title(f'K線重播 (共 {len(self.df)} 根K線, 當前 {self.current_idx} 根)')
            
            # 標記交易點
            for trade in self.trades:
                trade_time = trade['time']
                trade_price = trade['price']
                x_pos = mdates.date2num(trade_time)
                
                if trade['action'] in ('buy', 'buy_to_cover'):
                    self.ax1.plot(x_pos, trade_price, 'r^', markersize=10, label='買入/平空')
                elif trade['action'] in ('sell', 'sell_short', 'sell_to_close'):
                    self.ax1.plot(x_pos, trade_price, 'gv', markersize=10, label='賣出/做空')
            
            # 設置成交量圖標題
            self.ax2.set_ylabel('成交量')
            
            # 調整子圖間距
            self.figure.subplots_adjust(hspace=0.1)
            
            # 重繪畫布
            self.canvas.draw_idle()  # 使用draw_idle而不是draw
            
    def closeEvent(self, event):
        # 確保停止定時器
        self.timer.stop()
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = KLinePlayer()
    player.show()
    sys.exit(app.exec_())