import os
import re
import pandas as pd
import numpy as np
from datetime import datetime

# 設定特徵權重與對應名稱（用於輸出）
FEATURE_WEIGHTS = {
    'trend_strength': 0.3,
    'volatility': 0.2,
    'volume_spike_am': 0.15,
    'volume_spike_pm': 0.15,
    'support_break': 0.2
}
FEATURE_NAMES = {
    'trend_strength': '趨勢強度',
    'volatility': '波動率',
    'volume_spike_am': '早盤量能突增',
    'volume_spike_pm': '午盤量能突增',
    'support_break': '支撐位突破'
}

def validate_date_input(date_str):
    """驗證日期格式與檔案存在性（與原函數相同）"""
    if not re.match(r'^\d{8}$', date_str):
        return False, "日期格式錯誤，請輸入YYYYMMDD格式"
    target_file = f"TX_{date_str}_1K.csv"
    if not os.path.exists(target_file):
        return False, f"找不到檔案：{target_file}"
    return True, target_file

def load_data(target_date):
    """讀取目標日與其他歷史數據"""
    files = [f for f in os.listdir('.') if re.match(r'TX_\d{8}_1K\.csv', f)]
    
    # 讀取目標日數據
    target_file = f"TX_{target_date}_1K.csv"
    target_df = pd.read_csv(target_file)
    target_features = extract_features(target_df)
    
    # 讀取歷史數據（排除目標日）
    history = {}
    for f in files:
        date_str = f.split('_')[1]
        if date_str == target_date:
            continue
        df = pd.read_csv(f)
        history[date_str] = extract_features(df)
        
    return target_features, history

def extract_features(df):
    """從單日數據提取關鍵特徵（與原函數相同）"""
    features = {}
    features['open'] = df['Open'].iloc[0]
    features['close'] = df['Close'].iloc[-1]
    features['trend_strength'] = (df['Close'].iloc[-1] - df['Open'].iloc[0]) / df['Open'].iloc[0]
    features['max_high'] = df['High'].max()
    features['min_low'] = df['Low'].min()
    features['volatility'] = (features['max_high'] - features['min_low']) / features['open']
    
    # 成交量特徵（修正時間範圍）
    am_volume = df[df['Date'].str.contains(' 09:| 10:| 11:')]['Volume'].max()
    pm_volume = df[df['Date'].str.contains(' 13:| 14:')]['Volume'].max()
    features['volume_spike_am'] = am_volume / df['Volume'].median() if df['Volume'].median() !=0 else 0
    features['volume_spike_pm'] = pm_volume / df['Volume'].median() if df['Volume'].median() !=0 else 0
    
    support_level = df['Low'].quantile(0.25)
    features['support_break'] = int(df['Close'].iloc[-1] < support_level)
    return features

def calculate_similarity(target, candidate):
    """計算相似度並返回各項得分細節"""
    score_details = {}
    total_score = 0
    
    # 數值型特徵計算
    for feature in ['trend_strength', 'volatility', 'volume_spike_am', 'volume_spike_pm']:
        t_val = target[feature]
        c_val = candidate[feature]
        norm_diff = 1 - abs(t_val - c_val) / (abs(t_val) + abs(c_val) + 1e-8)
        feature_score = norm_diff * FEATURE_WEIGHTS[feature]
        score_details[feature] = feature_score
        total_score += feature_score
    
    # 類別型特徵計算
    support_match = (target['support_break'] == candidate['support_break'])
    support_score = support_match * FEATURE_WEIGHTS['support_break']
    score_details['support_break'] = support_score
    total_score += support_score
    
    return total_score, score_details  # 返回總分與細節

def find_similar_days():
    """主函數：輸出包含特徵得分的結果"""
    while True:
        target_date = input("請輸入目標日期（YYYYMMDD，例如20250519）：").strip()
        is_valid, msg = validate_date_input(target_date)
        if is_valid:
            break
        print(f"錯誤：{msg}\n")
    
    target_feat, history = load_data(target_date)
    
    similarities = []
    for date, features in history.items():
        total_score, score_details = calculate_similarity(target_feat, features)
        similarities.append( (date, total_score, score_details) )  # 存儲完整得分細節
    
    # 按總分排序並取前10
    sorted_days = sorted(similarities, key=lambda x: x[1], reverse=True)[1:50]
    
    # 輸出結果
    print(f"\n目標交易日：{target_date}")
    print("相似歷史交易日（前10名）及特徵得分：")
    for rank, (date, total, details) in enumerate(sorted_days, 1):
        print(f"\n第{rank}名｜{date}｜總相似度：{total:.2%}")
        print("特徵得分明細：")
        for feature in FEATURE_WEIGHTS.keys():
            print(f"  - {FEATURE_NAMES[feature]}：{details[feature]:.2%}")

if __name__ == "__main__":
    find_similar_days()