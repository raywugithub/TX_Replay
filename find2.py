import pandas as pd
import numpy as np
from datetime import time
from datetime import datetime, timedelta
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

def parse_date_input(date_str):
    """解析YYYYMMDD格式的日期並驗證"""
    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        raise ValueError("日期格式錯誤，請輸入YYYYMMDD格式")

def find_valid_previous_data(start_date, max_days_back=30):
    """向前查找有效交易日數據"""
    for i in range(1, max_days_back+1):
        check_date = start_date - timedelta(days=i)
        file_path = Path(f"TX_{check_date.strftime('%Y%m%d')}_1K.csv")
        if file_path.exists():
            df = pd.read_csv(file_path, parse_dates=["Date"])
            return df["High"].max(), df["Low"].min(), check_date
    raise FileNotFoundError(f"前{max_days_back}日內無有效交易數據")

def get_previous_day_data(target_date):
    """獲取前一個有效交易日數據"""
    try:
        prev_high, prev_low, found_date = find_valid_previous_data(target_date)
        print(f"使用 {found_date.strftime('%Y/%m/%d')} 作為前交易日基準")
        return prev_high, prev_low
    except FileNotFoundError as e:
        print(f"警告{target_date}：{e}，將使用預設值計算")
        return 21869, 21769  # 備用預設值

def get_first_day():
    """獲取並驗證首日日期"""
    while True:
        first_day_str = input("請輸入資料集中的首日日期(YYYYMMDD): ")
        try:
            first_day = parse_date_input(first_day_str)
            first_file = Path(f"TX_{first_day_str}_1K.csv")
            if not first_file.exists():
                print(f"錯誤：首日檔案 {first_file.name} 不存在")
                continue
            return first_day_str
        except ValueError as e:
            print(e)

def calculate_features(df, yesterday_high, yesterday_low):
    """核心特徵計算函數"""
    df['Time'] = df['Date'].dt.time
    yesterday_median = (yesterday_high + yesterday_low) / 2
    
    def get_period(t):
        if time(8, 45) <= t <= time(9, 0):
            return 'Period 1'
        elif time(9, 0) < t <= time(10, 45):
            return 'Period 2'
        elif time(10, 45) < t <= time(13, 45):
            return 'Period 3'
        return None
    
    df['Period'] = df['Time'].apply(get_period)
    df = df.dropna(subset=['Period'])
    
    features = {}
    for period in ['Period 1', 'Period 2', 'Period 3']:
        group = df[df['Period'] == period]
        if group.empty:
            features.update({f"{period}_{k}": np.nan for k in ['open_median', 'range', 'volatility', 'volume']})
            continue
            
        features.update({
            f"{period}_open_median": group['Open'].iloc[0] - yesterday_median,
            f"{period}_range": group['High'].max() - group['Low'].min(),
            f"{period}_volatility": group['Close'].std(),
            f"{period}_volume": group['Volume'].sum()
        })
    return features

def main():
    # 獲取首日日期
    first_day_str = get_first_day()
    
    # 獲取目標日期
    target_date_str = input("請輸入分析目標日期(YYYYMMDD): ")
    target_date = parse_date_input(target_date_str)
    
    # 檢查目標日期是否為首日
    if target_date_str == first_day_str:
        print("警告：目標日期為首日，無法計算昨日數據")
        return
    
    # 讀取目標日數據
    target_file = Path(f"TX_{target_date_str}_1K.csv")
    if not target_file.exists():
        raise FileNotFoundError(f"目標檔案 {target_file.name} 不存在")
    
    # 獲取昨日數據
    try:
        yesterday_high, yesterday_low = get_previous_day_data(target_date)
    except FileNotFoundError as e:
        print(f"警告：{e}，將使用預設值計算")
        yesterday_high, yesterday_low = 21869, 21769
    
    # 計算目標日特徵
    df_target = pd.read_csv(target_file, parse_dates=["Date"])
    target_features = calculate_features(df_target, yesterday_high, yesterday_low)
    
    # 收集所有檔案特徵(排除首日)
    all_files = [f for f in Path('.').glob('TX_*_1K.csv') 
                if f != target_file and f.name != f"TX_{first_day_str}_1K.csv"]
    
    similarity_scores = []
    scaler = StandardScaler()
    target_vector = np.array(list(target_features.values())).reshape(1, -1)
    
    # 修正1：全局標準化所有特徵向量
    all_vectors = []
    valid_files = []

    for file in all_files:
        try:
            file_date_str = file.stem.split('_')[1]
            file_date = parse_date_input(file_date_str)
            
            # 跳過首日數據
            if file_date_str == first_day_str:
                continue
                
            # 跳過沒有前日數據的文件
            try:
                prev_high, prev_low = get_previous_day_data(file_date)
            except FileNotFoundError:
                continue
                
            df = pd.read_csv(file, parse_dates=["Date"])
            file_features = calculate_features(df, prev_high, prev_low)
            file_vector = np.array(list(file_features.values()))
            
            # 檢查NaN並填充默認值
            if np.isnan(file_vector).any():
                file_vector = np.nan_to_num(file_vector, nan=0.0)
            
            all_vectors.append(file_vector)
            valid_files.append(file.name)
        except Exception as e:
            print(f"跳過檔案 {file.name}，原因：{str(e)}")
            continue
    
    # 加入目標日向量
    target_vector = np.nan_to_num(np.array(list(target_features.values())).reshape(1, -1))
    all_vectors = np.vstack([target_vector, np.array(all_vectors)])
    
    # 全局標準化
    scaler = StandardScaler()
    scaled_vectors = scaler.fit_transform(all_vectors)
    
    # 分離目標向量和其他向量
    target_scaled = scaled_vectors[0]
    others_scaled = scaled_vectors[1:]
    
    # 計算相似度
    similarity_scores = cosine_similarity([target_scaled], others_scaled)[0]
    
    # 組合結果
    results = list(zip(valid_files, similarity_scores))
    results.sort(key=lambda x: x[1], reverse=True)
    
    print("\n相似度排名前5日(已排除首日)：")
    for i, (filename, score) in enumerate(results[:5], 1):
        print(f"{i}. {filename} : {score:.4f}")

if __name__ == "__main__":
    main()