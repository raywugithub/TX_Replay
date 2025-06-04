import os
import pandas as pd
from datetime import datetime, timedelta, time
import numpy as np

# 模組1: 資料載入函數 (保持不變)
def load_data(start_date, end_date, data_folder='.'):
    """
    載入指定日期範圍內的期貨資料
    :param start_date: str, 起始日期(YYYYMMDD)
    :param end_date: str, 結束日期(YYYYMMDD)
    :param data_folder: str, 資料存放目錄
    :return: dict, {日期: DataFrame}
    """
    data_dict = {}
    current_date = datetime.strptime(start_date, '%Y%m%d')
    end_date = datetime.strptime(end_date, '%Y%m%d')
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        filename = f"TX_{date_str}_1K.csv"
        filepath = os.path.join(data_folder, filename)
        
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath)
                # 確保DateTime是時間格式
                df['DateTime'] = pd.to_datetime(df['Date'])
                data_dict[date_str] = df
                print(f"已載入: {filename}")
            except Exception as e:
                print(f"載入失敗 {filename}: {str(e)}")
        else:
            print(f"檔案不存在: {filename}")
        
        current_date += timedelta(days=1)
    
    return data_dict

# 模組2: 條件判斷函數 (重新設計高低點計算)
class ConditionChecker:
    """條件檢查器，包含單K棒條件和整日條件"""
    
    # ========== 單K棒條件 ==========
    @staticmethod
    def long_red_candle(row, min_body=10):
        """
        長紅K棒條件
        :param row: DataFrame row
        :param min_body: 最小實體長度(點)
        :return: bool
        """
        body_size = abs(row['Close'] - row['Open'])
        is_red = row['Close'] > row['Open']
        return body_size >= min_body and is_red
    
    @staticmethod
    def volume_spike(row, df, current_index, window=5, multiplier=2.0):
        """
        成交量突增條件
        :param row: 當前K棒
        :param df: 當日DataFrame
        :param current_index: 當前K棒索引
        :param window: 計算平均的K棒數量
        :param multiplier: 成交量倍數
        :return: bool
        """
        if current_index < window:
            return False
        
        prev_volume = df.iloc[current_index-window:current_index]['Volume'].mean()
        return row['Volume'] >= prev_volume * multiplier
    
    @staticmethod
    def breakout(row, df, current_index, lookback=30):
        """
        突破近期高點條件
        :param lookback: 回溯期數
        :return: bool
        """
        if current_index < lookback:
            return False
        
        prev_high = df.iloc[current_index-lookback:current_index]['High'].max()
        return row['High'] > prev_high
    
    # ========== 整日條件 ==========
    @staticmethod
    def day_high_volatility(day_df, min_range=150):
        """
        整日高波動性條件
        :param day_df: 整日資料DataFrame
        :param min_range: 最小波動範圍(點)
        :return: bool
        """
        day_range = day_df['High'].max() - day_df['Low'].min()
        return day_range >= min_range
    
    @staticmethod
    def day_strong_trend(day_df, min_body_ratio=0.7):
        """
        整日強趨勢條件
        :param day_df: 整日資料DataFrame
        :param min_body_ratio: 實體佔全日波幅最小比例
        :return: bool
        """
        day_range = day_df['High'].max() - day_df['Low'].min()
        if day_range == 0:
            return False
        
        body_size = abs(day_df['Close'].iloc[-1] - day_df['Open'].iloc[0])
        return (body_size / day_range) >= min_body_ratio
    
    @staticmethod
    def day_high_volume(day_df, multiplier=1.5, lookback_days=5):
        """
        整日高成交量條件
        :param day_df: 整日資料DataFrame
        :param multiplier: 成交量倍數
        :param lookback_days: 參照天數
        :return: bool
        """
        # 此處簡化處理，實際應用中需要多日數據
        avg_volume = day_df['Volume'].mean()
        total_volume = day_df['Volume'].sum()
        return total_volume >= avg_volume * multiplier
    
    @staticmethod
    def day_reversal(day_df, min_body_ratio=0.5):
        """
        整日反轉條件
        :param day_df: 整日資料DataFrame
        :param min_body_ratio: 反轉幅度最小比例
        :return: bool
        """
        open_price = day_df['Open'].iloc[0]
        close_price = day_df['Close'].iloc[-1]
        day_high = day_df['High'].max()
        day_low = day_df['Low'].min()
        
        # 上漲日反轉
        if close_price < open_price:
            reversal_range = day_high - open_price
            body_size = open_price - close_price
            return reversal_range > 0 and (body_size / reversal_range) >= min_body_ratio
        
        # 下跌日反轉
        elif close_price > open_price:
            reversal_range = open_price - day_low
            body_size = close_price - open_price
            return reversal_range > 0 and (body_size / reversal_range) >= min_body_ratio
        
        return False

    @staticmethod
    def day_time_segment_ratio(day_df):
        """
        分析三個時段的價格在平均線上下的時間比例，並計算高低點
        :param day_df: 整日資料DataFrame
        :return: (是否符合, 特徵字典)
        """
        # 確保數據按時間排序
        day_df = day_df.sort_values('DateTime')
        day_df['Time'] = day_df['DateTime'].dt.time
        
        # 定義三個時段
        segments = [
            {'name': 'first_trade', 'start': time(8, 45), 'end': time(9, 15)},  # 開盤到9:15
            {'name': 'second_trade', 'start': time(9, 15), 'end': time(9, 45)},  # 9:15到9:45
            {'name': 'final_trade', 'start': time(9, 45), 'end': time(13, 45)}   # 9:45到收盤
        ]
        
        results = {}
        
        # 存儲各時段的高低點
        segment_highs = {}
        segment_lows = {}
        
        for segment in segments:
            # 篩選出時段內的數據
            seg_df = day_df[(day_df['Time'] >= segment['start']) & 
                            (day_df['Time'] < segment['end'])]
            
            if len(seg_df) == 0:
                results[f"{segment['name']}_ratio"] = np.nan
                results[f"{segment['name']}_start_close"] = np.nan
                results[f"{segment['name']}_end_close"] = np.nan
                results[f"{segment['name']}_high"] = np.nan
                results[f"{segment['name']}_low"] = np.nan
                continue
            
            # 獲取時段開始和結束的收盤價
            start_close = seg_df.iloc[0]['Close']
            end_close = seg_df.iloc[-1]['Close']
            
            # 計算時段內最高價和最低價
            seg_high = seg_df['High'].max()
            seg_low = seg_df['Low'].min()
            
            # 存儲高低點用於後續分析
            segment_highs[segment['name']] = seg_high
            segment_lows[segment['name']] = seg_low
            
            # 根據價格變化方向決定計算方式
            if end_close >= start_close:
                # 上漲時段：計算close >= average的比例
                condition_met = seg_df['Close'] >= seg_df['Average']
            else:
                # 下跌時段：計算close <= average的比例
                condition_met = seg_df['Close'] <= seg_df['Average']
            
            ratio = condition_met.mean()
            
            # 儲存結果
            results[f"{segment['name']}_ratio"] = ratio
            results[f"{segment['name']}_start_close"] = start_close
            results[f"{segment['name']}_end_close"] = end_close
            results[f"{segment['name']}_high"] = seg_high
            results[f"{segment['name']}_low"] = seg_low
        
        # 計算全日最高點和最低點
        daily_high = max(segment_highs.values())
        daily_low = min(segment_lows.values())
        
        # 計算收盤時段是否創全日最高點
        results['final_high_is_daily_high'] = segment_highs['final_trade'] == daily_high
        
        # 計算收盤時段是否創全日最低點
        results['final_low_is_daily_low'] = segment_lows['final_trade'] == daily_low
        
        return True, results  # 總是返回True，因為我們需要這些特徵值

# 模組3: 條件掃描引擎 (更新以處理特徵值)
def scan_conditions(data_dict, intraday_config=None, daily_config=None):
    """
    掃描資料並檢查條件
    :param data_dict: 載入的期貨資料
    :param intraday_config: 單K棒條件配置列表
    :param daily_config: 整日條件配置列表
    :return: 符合條件的結果 (單K棒結果, 整日結果)
    """
    intraday_results = []
    daily_results = []
    
    # 掃描整日條件
    if daily_config:
        print("\n開始掃描整日條件...")
        for date_str, day_df in data_dict.items():
            matched_daily_conditions = []
            daily_features = {}  # 儲存所有特徵值
            
            for config in daily_config:
                condition_func = getattr(ConditionChecker, config['name'])
                kwargs = config.get('params', {})
                
                # 執行條件函數
                result = condition_func(day_df, **kwargs)
                
                # 處理不同類型的返回值
                if isinstance(result, tuple):
                    condition_met, features = result
                else:
                    condition_met = result
                    features = {}
                
                # 儲存特徵值
                for key, value in features.items():
                    daily_features[key] = value
                
                if condition_met:
                    matched_daily_conditions.append(config['name'])
            
            if matched_daily_conditions:
                daily_result = {
                    'date': date_str,
                    'open': day_df['Open'].iloc[0],
                    'high': day_df['High'].max(),
                    'low': day_df['Low'].min(),
                    'close': day_df['Close'].iloc[-1],
                    'volume': day_df['Volume'].sum(),
                    'range': day_df['High'].max() - day_df['Low'].min(),
                    'conditions': ', '.join(matched_daily_conditions)
                }
                # 合併特徵值
                daily_result.update(daily_features)
                daily_results.append(daily_result)
                print(f"整日條件符合: {date_str} - {', '.join(matched_daily_conditions)}")
    
    # 掃描單K棒條件 (保持不變)
    if intraday_config:
        print("\n開始掃描單K棒條件...")
        for date_str, df in data_dict.items():
            for i, row in df.iterrows():
                matched_intraday_conditions = []
                
                for config in intraday_config:
                    condition_func = getattr(ConditionChecker, config['name'])
                    kwargs = config.get('params', {})
                    
                    # 根據條件需求傳遞不同參數
                    if 'df' in condition_func.__code__.co_varnames:
                        kwargs['df'] = df
                        kwargs['current_index'] = i
                    
                    if condition_func(row, **kwargs):
                        matched_intraday_conditions.append(config['name'])
                
                if matched_intraday_conditions:
                    result = {
                        'date': date_str,
                        'datetime': row['DateTime'],
                        'open': row['Open'],
                        'high': row['High'],
                        'low': row['Low'],
                        'close': row['Close'],
                        'volume': row['Volume'],
                        'conditions': ', '.join(matched_intraday_conditions)
                    }
                    intraday_results.append(result)
    
    return intraday_results, daily_results

# 新增模組4: 時段比例統計分析
# ... 前面的代码保持不变 ...

# 更新模組4: 時段比例統計分析 (加入價格變動維度)
def analyze_segment_probability(daily_results, output_folder='.'):
    """
    分析三个时段的比例组合概率，包含高低点分析
    :param daily_results: 整日结果列表
    :param output_folder: 输出目录
    :return: 组合概率DataFrame
    """
    if not daily_results:
        print("没有整日结果可用于分析")
        return None
    
    # 创建DataFrame
    df = pd.DataFrame(daily_results)
    
    # 确保有需要的字段
    required_columns = ['date', 'first_trade_ratio', 'second_trade_ratio', 'final_trade_ratio',
                        'first_trade_start_close', 'first_trade_end_close', 'first_trade_high', 'first_trade_low',
                        'second_trade_start_close', 'second_trade_end_close', 'second_trade_high', 'second_trade_low',
                        'final_trade_start_close', 'final_trade_end_close', 'final_trade_high', 'final_trade_low',
                        'final_high_is_daily_high', 'final_low_is_daily_low']
    
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        print(f"缺少必要字段: {', '.join(missing_cols)}")
        return None
    
    print("\n开始分析时段比例组合概率...")
    
    # 定义比例分类函数
    def classify_ratio(ratio):
        if ratio < 0.4:
            return "Low"
        elif ratio < 0.8:
            return "Medium"
        else:
            return "High"
    
    # 定义价格变动分类函数
    def classify_price_change(start_close, end_close):
        change = end_close - start_close
        if change > 0:
            return "Up"
        elif change < 0:
            return "Down"
        else:
            return "Flat"
    
    # 应用比例分类
    df['first_trade_class'] = df['first_trade_ratio'].apply(classify_ratio)
    df['second_trade_class'] = df['second_trade_ratio'].apply(classify_ratio)
    df['final_trade_class'] = df['final_trade_ratio'].apply(classify_ratio)
    
    # 应用价格变动分类
    df['first_trade_change'] = df.apply(
        lambda x: classify_price_change(x['first_trade_start_close'], x['first_trade_end_close']), axis=1)
    df['second_trade_change'] = df.apply(
        lambda x: classify_price_change(x['second_trade_start_close'], x['second_trade_end_close']), axis=1)
    df['final_trade_change'] = df.apply(
        lambda x: classify_price_change(x['final_trade_start_close'], x['final_trade_end_close']), axis=1)

    # 创建组合列 (比例分类 + 价格变动 + 高低点特征)
    df['combination'] = df.apply(
        lambda x: (
            f"{x['first_trade_class']}_{x['first_trade_change']}_"
            f"{x['second_trade_class']}_{x['second_trade_change']}_"
            f"{x['final_trade_class']}_{x['final_trade_change']}_"
            f"{'H' if x['final_high_is_daily_high'] else 'Nh'}_"
            f"{'L' if x['final_low_is_daily_low'] else 'Nl'}"
        ), 
        axis=1
    )
    
    # 按组合分组并收集日期
    combo_groups = df.groupby('combination')['date'].apply(list).reset_index()
    combo_groups.columns = ['combination', 'dates']
    
    # 统计组合出现次数
    combo_counts = df['combination'].value_counts().reset_index()
    combo_counts.columns = ['combination', 'count']
    
    # 合并日期信息
    combo_counts = pd.merge(combo_counts, combo_groups, on='combination', how='left')
    
    # 计算概率
    total_days = len(df)
    combo_counts['probability'] = combo_counts['count'] / total_days
    
    # 计算组合描述
    # 拆分组合为三个独立描述列
    combo_counts['first_trade_description'] = combo_counts['combination'].apply(
        lambda x: f"{x.split('_')[0]}({x.split('_')[1]})")
    combo_counts['second_trade_description'] = combo_counts['combination'].apply(
        lambda x: f"{x.split('_')[2]}({x.split('_')[3]})")
    combo_counts['final_trade_description'] = combo_counts['combination'].apply(
        lambda x: f"{x.split('_')[4]}({x.split('_')[5]})")
    
    # 添加高低点特征描述
    combo_counts['high_point'] = combo_counts['combination'].apply(
        lambda x: "创全日最高" if x.split('_')[6] == 'H' else "未创全日最高")
    combo_counts['low_point'] = combo_counts['combination'].apply(
        lambda x: "创全日最低" if x.split('_')[7] == 'L' else "未创全日最低")
    
    # 创建日期字符串列 (用于显示)
    combo_counts['date_list'] = combo_counts['dates'].apply(lambda x: ", ".join(x))
    
    # 计算平均价格变动
    combo_avg_change = df.groupby('combination').agg({
        'first_trade_end_close': lambda x: x.mean() - df.loc[x.index, 'first_trade_start_close'].mean(),
        'second_trade_end_close': lambda x: x.mean() - df.loc[x.index, 'second_trade_start_close'].mean(),
        'final_trade_end_close': lambda x: x.mean() - df.loc[x.index, 'final_trade_start_close'].mean()
    }).reset_index()
    combo_avg_change.columns = [
        'combination', 
        'avg_first_change', 
        'avg_second_change', 
        'avg_final_change'
    ]
    
    # 合并平均变动信息
    combo_counts = pd.merge(combo_counts, combo_avg_change, on='combination', how='left')
    
    # 计算全天价格变动
    df['daily_change'] = df['close'] - df['open']
    combo_daily_change = df.groupby('combination')['daily_change'].mean().reset_index()
    combo_daily_change.columns = ['combination', 'avg_daily_change']
    combo_counts = pd.merge(combo_counts, combo_daily_change, on='combination', how='left')

    # 计算高低点特征的概率
    high_is_daily_prob = df['final_high_is_daily_high'].mean()
    low_is_daily_prob = df['final_low_is_daily_low'].mean()

    # 排序并重置索引
    combo_counts = combo_counts.sort_values('probability', ascending=False).reset_index(drop=True)
    
    # 输出结果
    print("\n时段比例与价格变动组合概率统计 (含高低点分析):")
    print(combo_counts[['first_trade_description', 'second_trade_description', 
                        'final_trade_description', 'high_point', 'low_point',
                        'count', 'probability', 'avg_daily_change']])
    
    print(f"\n收盘时段创全日最高点的概率: {high_is_daily_prob:.2%}")
    print(f"收盘时段创全日最低点的概率: {low_is_daily_prob:.2%}")
    
    # 保存到CSV
    output_file = os.path.join(output_folder, "segment_probability_analysis.csv")
    # 选择要保存的列
    save_columns = [
        'combination', 'count', 'probability', 'dates', 'date_list',
        'first_trade_description', 'second_trade_description', 'final_trade_description',
        'high_point', 'low_point',
        'avg_first_change', 'avg_second_change', 'avg_final_change', 'avg_daily_change'
    ]
    combo_counts[save_columns].to_csv(output_file, index=False)
    print(f"分析结果已保存至: {output_file}")
    
    # 保存详细日期文件
    detailed_file = os.path.join(output_folder, "segment_detailed_dates.csv")
    # 选择要保存的详细字段
    detailed_columns = [
        'date', 
        'first_trade_class', 'first_trade_change', 'first_trade_high', 'first_trade_low',
        'second_trade_class', 'second_trade_change', 'second_trade_high', 'second_trade_low',
        'final_trade_class', 'final_trade_change', 'final_trade_high', 'final_trade_low',
        'final_high_is_daily_high', 'final_low_is_daily_low',
        'combination'
    ]
    df[detailed_columns].to_csv(detailed_file, index=False)
    print(f"详细日期分类已保存至: {detailed_file}")

    # import matplotlib.pyplot as plt
    # 
    # # 创建概率分布直方图
    # plt.figure(figsize=(12, 8))
    # combo_counts.set_index('description')['probability'].plot(kind='bar')
    # plt.title('時段比例組合概率分布')
    # plt.ylabel('概率')
    # plt.xticks(rotation=45, ha='right')
    # plt.tight_layout()
    # plt.savefig(os.path.join(output_folder, 'segment_probability.png'))
    
    return combo_counts

# 主程式 (更新支援特徵值)
def main():
    # 參數配置
    data_folder = '.'  # 當前目錄
    start_date = '20230801'  # 起始日期
    # end_date = '20250603'   # 結束日期
    today_date = datetime.today().strftime('%Y%m%d')
    end_date = str(today_date)
    
    # 條件配置
    intraday_config = [
        {'name': 'long_red_candle', 'params': {'min_body': 15}},
        {'name': 'volume_spike', 'params': {'window': 5, 'multiplier': 2.5}},
        {'name': 'breakout', 'params': {'lookback': 30}}
    ]
    
    # 新增時段分析條件
    daily_config = [
        {'name': 'day_high_volatility', 'params': {'min_range': 200}},
        {'name': 'day_strong_trend', 'params': {'min_body_ratio': 0.6}},
        {'name': 'day_reversal', 'params': {'min_body_ratio': 0.5}},
        {'name': 'day_time_segment_ratio'}
    ]
    
    # 執行流程
    print("開始載入資料...")
    data_dict = load_data(start_date, end_date, data_folder)
    
    if not data_dict:
        print("無有效資料可處理!")
        return
    
    # 掃描條件
    intraday_results, daily_results = scan_conditions(
        data_dict, 
        intraday_config=intraday_config,
        daily_config=daily_config
    )
    
    # 輸出結果
    print("\n掃描完成! 結果:")
    
    # 單K棒結果
    if intraday_results:
        intraday_df = pd.DataFrame(intraday_results)
        print(f"找到 {len(intraday_df)} 筆符合單K棒條件的K棒")
        
        # 輸出結果到CSV
        output_file = f"intraday_results_{start_date}_{end_date}.csv"
        intraday_df.to_csv(output_file, index=False)
        print(f"單K棒結果已保存至: {output_file}")
    else:
        print("未找到符合單K棒條件的K棒")
    
    # 整日結果
    if daily_results:
        daily_df = pd.DataFrame(daily_results)
        print(f"找到 {len(daily_df)} 筆符合整日條件的交易日")
        
        # 輸出結果到CSV
        output_file = f"daily_results_{start_date}_{end_date}.csv"
        daily_df.to_csv(output_file, index=False)
        print(f"整日結果已保存至: {output_file}")
        
        # # 顯示時段比例結果
        # print("\n時段比例分析結果:")
        # segment_columns = [col for col in daily_df.columns if 'ratio' in col]
        # print(daily_df[['date'] + segment_columns])
        
        # 新增: 执行時段比例組合概率分析
        analyze_segment_probability(daily_results, output_folder=data_folder)
    else:
        print("未找到符合整日條件的交易日")

if __name__ == "__main__":
    main()