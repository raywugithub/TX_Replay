import pandas as pd
import os
from datetime import datetime

def split_csv_by_date(input_file):
    # 讀取原始CSV檔案，保持所有欄位格式不變
    df = pd.read_csv(input_file, dtype={'Date': str})
    
    # 提取日期部分用於分組（假設格式為"YYYY/MM/DD"）
    df['DateOnly'] = df['Date'].str.split().str[0]
    
    # 為每個日期創建一個CSV檔案
    for date_str in df['DateOnly'].unique():
        # 解析日期確保月份格式正確
        date_obj = datetime.strptime(date_str, "%Y/%m/%d")
        # 格式化為YYYYMMDD（月份保證兩位數）
        date_part = date_obj.strftime("%Y%m%d")
        
        output_filename = f"TX_{date_part}_1K.csv"
        
        # 獲取該日期的所有數據
        group = df[df['DateOnly'] == date_str]
        
        # 只保留原始需要的欄位
        output_df = group[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        # 保存到CSV，保持所有原始格式不變
        output_df.to_csv(output_filename, index=False)
        
        # 檢查行數是否為300行（不含標題行）
        with open(output_filename, 'r', encoding='utf-8') as f:
            line_count = sum(1 for line in f) - 1  # 減去標題行
        
        if line_count == 300:
            print(f"已創建檔案: {output_filename} (行數正確: 300行)")
        else:
            print(f"警告: {output_filename} 行數不正確 (實際: {line_count}行, 預期: 300行)")

# 使用範例
if __name__ == "__main__":
    # 1. 設定路徑
    download_folder = os.path.join(os.environ['USERPROFILE'], 'Downloads')
    today_date = datetime.today().strftime('%Y%m%d')

    # 2. 讀取原始CSV文件（包含欄位名稱）
    input_file = os.path.join(download_folder, "TX00_台指近_分鐘線.csv")

    split_csv_by_date(input_file)
    print("檔案分割完成！")