import pandas as pd
import os
from datetime import datetime
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# 1. 設定路徑
target_date = input("請輸入目標日期（YYYYMMDD，例如20250519）：").strip()
download_folder = os.path.join(os.environ['USERPROFILE'], 'Downloads')
output_csv = os.path.join(download_folder, 'TX_Replay', f"TX_{target_date}_1K.csv")

# 讀取數據時確保正確解析日期
df_plot = pd.read_csv(output_csv, parse_dates=['Date'])
df_plot['Date'] = pd.to_datetime(df_plot['Date'], format='%Y/%m/%d %H:%M')  # 明確指定日期格式
df_plot.set_index('Date', inplace=True)

# 初始化標籤變數
price_label = None
time_label = None
v_line = None
h_line = None

def on_mouse_move(event):
    global price_label, time_label, v_line, h_line
    
    # 如果滑鼠不在圖表內則返回
    if not event.inaxes:
        return
    
    ax = event.inaxes
    
    # 刪除舊的線條和標籤
    if v_line:
        v_line.remove()
    if h_line:
        h_line.remove()
    if price_label:
        price_label.remove()
    if time_label:
        time_label.remove()
    
    # 獲取滑鼠位置
    x = event.xdata
    y = event.ydata
    
    # 轉換x坐標為日期時間
    date = mdates.num2date(x)
    date_str = date.strftime('%H:%M')
    
    # 繪製十字線
    v_line = ax.axvline(x=x, color='gray', linestyle='--', alpha=0.7)
    h_line = ax.axhline(y=y, color='gray', linestyle='--', alpha=0.7)
    
    # 顯示價格和時間標籤
    price_label = ax.text(0.95, 0.95, f'Price: {y:.2f}', 
                         transform=ax.transAxes, 
                         bbox=dict(facecolor='white', alpha=0.8))
    
    time_label = ax.text(0.95, 0.90, f'Time: {date_str}', 
                        transform=ax.transAxes, 
                        bbox=dict(facecolor='white', alpha=0.8))
    
    plt.draw()

try:
    # 2. 創建顏色映射 - strength指標
    colors = ['red' if s >= 0 else 'green' for s in df_plot['strength']]

    # 3. 創建額外的圖表面板
    apds = [
        mpf.make_addplot(df_plot['Average'], panel=0, type='line', color='purple', 
                        width=1.5, alpha=0.8, linestyle='-', label='Average'),
        mpf.make_addplot(df_plot['Volume'], panel=1, type='bar', color='blue', ylabel='Volume'),
        mpf.make_addplot(df_plot['strength'], panel=2, type='bar', color=colors, ylabel='Strength')
    ]
    
    # 4. 繪製圖表
    fig, axes = mpf.plot(
        df_plot,
        type='candle',
        volume=False,
        addplot=apds,
        figratio=(12, 8),
        figscale=1.0,
        title='TX Futures 1-min K-line',
        ylabel='Price',
        style='yahoo',
        panel_ratios=(3, 1, 1),
        datetime_format='%H:%M',
        returnfig=True
    )
except:
    # 3. 創建額外的圖表面板
    apds = [
        mpf.make_addplot(df_plot['Average'], panel=0, type='line', color='purple', 
                        width=1.5, alpha=0.8, linestyle='-', label='Average'),
        mpf.make_addplot(df_plot['Volume'], panel=1, type='bar', color='blue', ylabel='Volume'),
    ]

    # 4. 繪製圖表
    fig, axes = mpf.plot(
        df_plot,
        type='candle',
        volume=False,
        addplot=apds,
        figratio=(12, 8),
        figscale=1.0,
        title='TX Futures 1-min K-line',
        ylabel='Price',
        style='yahoo',
        panel_ratios=(3, 1),
        datetime_format='%H:%M',
        returnfig=True
    )

# 5. 設置日期格式
fig.autofmt_xdate()

# 6. 添加網格
for ax in axes:
    ax.grid(True, linestyle='--', alpha=0.7)

# 7. 添加圖例
axes[0].legend(loc='upper left')

# 8. 連接滑鼠移動事件
fig.canvas.mpl_connect('motion_notify_event', on_mouse_move)

# 9. 顯示圖表
plt.show()