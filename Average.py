import os
import pandas as pd
from datetime import datetime, timedelta

def calculate_average(df):
    """
    計算每一分鐘的累積均價
    公式: (開盤到當前時間每一分鐘的Close*Volume加總) / (開盤到當前時間每一分鐘Volume加總)
    """
    # 計算Close*Volume的累積和
    df['Cumulative_Close_Volume'] = (df['Close'] * df['Volume']).cumsum()
    
    # 計算Volume的累積和
    df['Cumulative_Volume'] = df['Volume'].cumsum()
    
    # 計算均價
    df['Average'] = df['Cumulative_Close_Volume'] / df['Cumulative_Volume']
    
    # 移除臨時列
    df.drop(['Cumulative_Close_Volume', 'Cumulative_Volume'], axis=1, inplace=True)
    
    return df

def process_files():
    # 獲取當前目錄
    current_dir = os.getcwd()
    
    # 設定日期範圍
    end_date = datetime.now()
    start_date = datetime(2023, 8, 1)
    
    # 生成所有可能的日期
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date.strftime('%Y%m%d'))
        current_date += timedelta(days=1)
    
    # 處理每個日期的文件
    for date_str in date_list:
        filename = f"TX_{date_str}_1K.csv"
        filepath = os.path.join(current_dir, filename)
        
        # 檢查文件是否存在
        if not os.path.exists(filepath):
            print(f"文件 {filename} 不存在，跳過...")
            continue
        
        # 讀取CSV文件
        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            print(f"讀取文件 {filename} 時發生錯誤: {e}")
            continue
        
        # 檢查是否已有Average列
        if 'Average' in df.columns:
            print(f"文件 {filename} 已包含Average列，跳過...")
            continue
        
        # 檢查必要的列是否存在
        required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_columns):
            print(f"文件 {filename} 缺少必要列，跳過...")
            continue
        
        # 計算並添加Average列
        df = calculate_average(df)
        
        # 保存文件
        try:
            df.to_csv(filepath, index=False)
            print(f"文件 {filename} 已成功處理並保存")
        except Exception as e:
            print(f"保存文件 {filename} 時發生錯誤: {e}")

if __name__ == "__main__":
    process_files()