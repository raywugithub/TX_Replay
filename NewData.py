import pandas as pd
import os
from datetime import datetime
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# 1. 設定路徑
download_folder = os.path.join(os.environ['USERPROFILE'], 'Downloads')
today_date = datetime.today().strftime('%Y%m%d')

# 2. 讀取原始CSV文件（包含欄位名稱）
input_csv = os.path.join(download_folder, "TX00_台指近_分鐘線.csv")
df = pd.read_csv(input_csv, encoding='big5')

# # 刪除最後一行（原始欄位名稱）
# df = df.iloc[:-1]  # 刪除最後一行

# 刪除第6、7、9欄（索引5,6,8）
df = df.drop(df.columns[[5, 6, 8]], axis=1)

# 反轉資料順序（將最後一筆變第一筆）
df = df.iloc[::-1].reset_index(drop=True)

# 重新命名欄位
new_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
df.columns = new_columns

# 新增strength和Average欄位
df['strength'] = np.nan
df['largeorder'] = np.nan
df['Average'] = np.nan

# 讀取Excel的多空力道和均價數據
excel_path = os.path.join(download_folder, f"日_看盤_群益_{today_date}.xlsx")
try:
    # 嘗試使用欄位名稱讀取
    raw_data = pd.read_excel(
        excel_path,
        sheet_name='FITX_RAW',
        usecols=['時間', '多空力道', '大單', '均價']  # 讀取4個欄位
    )
except:
    # 如果欄位名稱讀取失敗，改用欄位索引
    raw_data = pd.read_excel(
        excel_path,
        sheet_name='FITX_RAW',
        usecols="AV, G, F, B"  # AV欄(時間), G欄(多空力道), F欄(大單), B欄(均價)
    )
    raw_data.columns = ['時間', '多空力道', '大單', '均價']  # 重命名列

# 處理時間格式
raw_data['分鐘'] = raw_data['時間'].astype(str).str.extract(r'(\d{2}:\d{2})')[0]

# 從DF的Date欄位提取分鐘資訊
df['交易分鐘'] = df['Date'].str.split().str[-1]  # 取出空格後的部分

# 建立分鐘→多空力道的映射字典
minute_strength_map = raw_data.groupby('分鐘')['多空力道'].first().to_dict()

# 建立分鐘→大單的映射字典
minute_largeorder_map = raw_data.groupby('分鐘')['大單'].first().to_dict()

# 建立分鐘→均價的映射字典
minute_average_map = raw_data.groupby('分鐘')['均價'].first().to_dict()

# 映射多空力道
df['strength'] = df['交易分鐘'].map(minute_strength_map)

# 映射大單
df['largeorder'] = df['交易分鐘'].map(minute_largeorder_map)

# 映射均價
df['Average'] = df['交易分鐘'].map(minute_average_map)

# 移除臨時列
df = df.drop(columns=['交易分鐘'])

# 保存結果
output_csv = os.path.join(download_folder, f"TX_{today_date}_1K.csv")
df.to_csv(output_csv, index=False)

print(f"處理完成！結果已保存至: {output_csv}")
backup_csv = os.path.join(download_folder, 'TX_Replay', f"TX_{today_date}_1K.csv")
df.to_csv(backup_csv, index=False, encoding='utf-8')
# print(f"新檔案格式: {df.shape[0]} 行 x {df.shape[1]} 欄")
# print("欄位名稱:", list(df.columns))

# 繪製K線圖、成交量、strength直方圖和均價線
# ------------------------------------------------------------
# 1. 讀取剛剛保存的CSV文件
# output_csv = os.path.join(download_folder, 'TX_Replay', f"TX_20250526_1K.csv")
df_plot = pd.read_csv(output_csv, parse_dates=['Date'], index_col='Date')

try:
        # 2. 創建顏色映射 - strength,colors_largeorder指標
        # 正值紅色，負值綠色
        colors = ['red' if s >= 0 else 'green' for s in df_plot['strength']]
        colors_largeorder = ['red' if s >= 0 else 'green' for s in df_plot['largeorder']]

        # 3. 創建額外的圖表面板
        apds = [
            # 均價線（在主圖面板）
            mpf.make_addplot(df_plot['Average'], panel=0, type='line', color='purple', 
                            width=1.5, alpha=0.8, linestyle='-', label='Average'),
        
            # 成交量柱狀圖（在面板1）
            mpf.make_addplot(df_plot['Volume'], panel=1, type='bar', color='blue', ylabel='Volume'),
        
            # strength指標直方圖（在面板2）
            mpf.make_addplot(df_plot['strength'], panel=2, type='bar', color=colors, ylabel='Strength'),

            # largeorder指標直方圖（在面板3）
            mpf.make_addplot(df_plot['largeorder'], panel=3, type='bar', color=colors_largeorder, ylabel='Largeorder'),
        ]
        # 4. 繪製圖表
        fig, axes = mpf.plot(
            df_plot,
            type='candle',
            volume=False,  # 我們已經自定義了成交量面板
            addplot=apds,
            figratio=(12, 8),
            figscale=1.0,
            title=f'TX Futures 1-min K-line ({today_date})',
            ylabel='Price',
            style='yahoo',
            panel_ratios=(3, 1, 1, 1),  # 主圖:成交量:strength:largeorder = 3:1:1:1
            returnfig=True
        )
except Exception as e:
        # 3. 創建額外的圖表面板
        apds = [
            # 均價線（在主圖面板）
            mpf.make_addplot(df_plot['Average'], panel=0, type='line', color='purple', 
                            width=1.5, alpha=0.8, linestyle='-', label='Average'),
        
            # 成交量柱狀圖（在面板1）
            mpf.make_addplot(df_plot['Volume'], panel=1, type='bar', color='blue', ylabel='Volume'),
        ]

        # 4. 繪製圖表
        fig, axes = mpf.plot(
            df_plot,
            type='candle',
            volume=False,  # 我們已經自定義了成交量面板
            addplot=apds,
            figratio=(12, 8),
            figscale=1.0,
            title=f'TX Futures 1-min K-line ({today_date})',
            ylabel='Price',
            style='yahoo',
            panel_ratios=(3, 1),  # 主圖:成交量 = 3:1
            returnfig=True
        )
        print(f"發生錯誤：{e}")

# 5. 設置日期格式
axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
fig.autofmt_xdate()  # 自動旋轉日期標籤

# 6. 添加網格
for ax in axes:
    ax.grid(True, linestyle='--', alpha=0.7)

# 7. 添加圖例
axes[0].legend(loc='upper left')

# 8. 保存圖表
chart_file = os.path.join(download_folder, 'TX_Replay', f"TX_{today_date}_1K_chart.png")
plt.savefig(chart_file, dpi=300, bbox_inches='tight')
print(f"K線圖已保存至: {chart_file}")

# 9. 顯示圖表（可選）
plt.show()