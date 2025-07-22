import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash_bootstrap_components as dbc

# =============================================================================
# 1. 資料載入與準備 (從 advisor.py 移植)
# =============================================================================
# 預先載入數據，避免在回呼中重複讀取
PROB_DF = None
DETAILED_DF = None
DATA_LOADED = False
DATA_LOAD_ERROR = ""

def load_data_globally(prob_path="segment_probability_analysis.csv", detailed_path="segment_detailed_dates.csv"):
    """在應用程式啟動時載入數據"""
    global PROB_DF, DETAILED_DF, DATA_LOADED, DATA_LOAD_ERROR
    
    if os.path.exists(prob_path) and os.path.exists(detailed_path):
        try:
            PROB_DF = pd.read_csv(prob_path)
            DETAILED_DF = pd.read_csv(detailed_path)
            DATA_LOADED = True
        except Exception as e:
            DATA_LOAD_ERROR = f"數據載入失敗: {str(e)}"
            DATA_LOADED = False
    else:
        error_msg = []
        if not os.path.exists(prob_path):
            error_msg.append(f"檔案不存在: {prob_path}")
        if not os.path.exists(detailed_path):
            error_msg.append(f"檔案不存在: {detailed_path}")
        DATA_LOAD_ERROR = " | ".join(error_msg)
        DATA_LOADED = False

# 應用程式啟動時執行一次
load_data_globally()


# =============================================================================
# 2. Dash 應用程式定義
# =============================================================================
# 使用 dash-bootstrap-components 的 CYBORG 暗色主題
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], suppress_callback_exceptions=True)
app.title = "當沖日内交易顧問 (Dash版)"

# =============================================================================
# 3. 應用程式佈局 (Layout)
# =============================================================================
app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("當沖日内交易顧問 (Dash版)", className="text-center my-4"))),
    
    # 狀態顯示區
    dbc.Row(dbc.Col(html.Div(id='data-load-status', className="text-center mb-4"))),
    
    dbc.Row([
        # 控制面板
        dbc.Col(dbc.Card([
            dbc.CardHeader(html.H4("設置", className="m-0")),
            dbc.CardBody([
                dbc.Label("當前交易時段:"),
                dcc.Dropdown(
                    id='time-selector',
                    options=[
                        {'label': '8:45 (開盤前)', 'value': '8:45'},
                        {'label': '9:15 (開盤時段結束)', 'value': '9:15'},
                        {'label': '9:45 (中間時段結束)', 'value': '9:45'},
                        {'label': '13:00 (盤後分析)', 'value': '13:00'}
                    ],
                    value='9:15',
                    clearable=False
                ),
                html.Hr(),
                dbc.Label("開盤時段 (8:45-9:15):"),
                dcc.Dropdown(id='ft-class-dropdown', placeholder="選擇比例類別...", disabled=True, className="mb-2"),
                dcc.Dropdown(id='ft-change-dropdown', placeholder="選擇價格變動...", disabled=True, className="mb-2"),
                dbc.Label("中間時段 (9:15-9:45):"),
                dcc.Dropdown(id='st-class-dropdown', placeholder="選擇比例類別...", disabled=True, className="mb-2"),
                dcc.Dropdown(id='st-change-dropdown', placeholder="選擇價格變動...", disabled=True, className="mb-2"),
                dbc.Label("收盤時段 (9:45-13:45):"),
                dcc.Dropdown(id='tt-class-dropdown', placeholder="選擇比例類別...", disabled=True, className="mb-2"),
                dcc.Dropdown(id='tt-change-dropdown', placeholder="選擇價格變動...", disabled=True, className="mb-2"),
                dbc.Label("高低點特徵:"),
                dcc.Dropdown(
                    id='high-point-dropdown',
                    options=[{'label': s, 'value': s} for s in ["創全日最高", "未創全日最高"]],
                    placeholder="選擇高點特徵...",
                    disabled=True,
                    className="mb-2"
                ),
                dcc.Dropdown(
                    id='low-point-dropdown',
                    options=[{'label': s, 'value': s} for s in ["創全日最低", "未創全日最低"]],
                    placeholder="選擇低點特徵...",
                    disabled=True,
                    className="mb-2"
                ),
                html.Br(),
                dbc.Row([
                    dbc.Col(dbc.Button('查詢概率', id='query-button', n_clicks=0, color="primary", className="w-100")),
                    dbc.Col(dbc.Button('重置選擇', id='reset-button', n_clicks=0, color="secondary", className="w-100")),
                ])
            ])
        ]), width=12, lg=2),
        
        # 結果顯示區
        dbc.Col(dbc.Card([
            dbc.CardHeader(html.H4("結果分析", className="m-0")),
            dbc.CardBody(
                dcc.Loading(
                    id="loading-results",
                    type="circle",
                    children=[
                        dbc.Row([
                            dbc.Col(
                                html.Div(id='results-text-output', children="請選擇條件並點擊查詢。"),
                                width=12, md=5
                            ),
                            dbc.Col(
                                dcc.Graph(id='results-chart-output'),
                                width=12, md=7
                            )
                        ])
                    ]
                )
            )
        ]), width=12, lg=10, className="mt-3 mt-lg-0"),
    ])
], fluid=True, className="dbc")


# =============================================================================
# 4. 核心計算邏輯 (重構為返回 Dash 元件)
# =============================================================================
def query_for_915(ft_class, ft_change):
    if not ft_class or not ft_change:
        return [dbc.Alert("請選擇開盤時段的類別和變動方向", color="warning")], None
    
    ft_desc = f"{ft_class}({ft_change})"
    condition = (DETAILED_DF['first_trade_class'] == ft_class) & \
                (DETAILED_DF['first_trade_change'] == ft_change)
    subset = DETAILED_DF[condition]

    if subset.empty:
        return [dbc.Alert(f"沒有找到開盤時段為 {ft_desc} 的數據", color="danger")], None

    total_count = len(subset)
    
    # 計算邏輯不變
    st_group = subset.groupby(['second_trade_class', 'second_trade_change']).size().reset_index(name='count')
    st_group['probability'] = st_group['count'] / total_count
    tt_group = subset.groupby(['final_trade_class', 'final_trade_change']).size().reset_index(name='count')
    tt_group['probability'] = tt_group['count'] / total_count
    high_prob = subset['final_high_is_daily_high'].mean()
    low_prob = subset['final_low_is_daily_low'].mean()

    # --- 使用 dbc.Table 建立表格 ---
    st_df_display = st_group.sort_values('probability', ascending=False).rename(columns={
        'second_trade_class': '類別', 'second_trade_change': '變動', 'probability': '機率'
    })
    st_df_display['機率'] = st_df_display['機率'].map('{:.2%}'.format)
    st_table = dbc.Table.from_dataframe(
        st_df_display[['類別', '變動', '機率']],
        striped=True, bordered=True, hover=True, responsive=True, className="table-dark"
    )

    tt_df_display = tt_group.sort_values('probability', ascending=False).rename(columns={
        'final_trade_class': '類別', 'final_trade_change': '變動', 'probability': '機率'
    })
    tt_df_display['機率'] = tt_df_display['機率'].map('{:.2%}'.format)
    tt_table = dbc.Table.from_dataframe(
        tt_df_display[['類別', '變動', '機率']],
        striped=True, bordered=True, hover=True, responsive=True, className="table-dark"
    )

    # --- 組合輸出元件 ---
    output_components = [
        html.H5("當前時間: 9:15 (開盤時段結束)"),
        html.Ul([html.Li(f"開盤時段: {ft_desc}"), html.Li(f"分析基於 {total_count} 個歷史交易日")]),
        html.Hr(),
        html.H6("中間時段 (9:15-9:45) 預測:"),
        st_table,
        html.Hr(),
        html.H6("收盤時段 (9:45-13:45) 預測:"),
        tt_table,
        html.Hr(),
        html.H6("高低點特徵預測:"),
        html.Ul([html.Li(f"創全日最高點概率: {high_prob:.2%}"), html.Li(f"創全日最低點概率: {low_prob:.2%}")])
    ]
    
    return output_components, (st_group, tt_group, high_prob, low_prob)

def query_for_945(ft_class, ft_change, st_class, st_change):
    if not all([ft_class, ft_change, st_class, st_change]):
        return [dbc.Alert("請選擇開盤和中間時段的類別及變動方向", color="warning")], None

    ft_desc = f"{ft_class}({ft_change})"
    st_desc = f"{st_class}({st_change})"
    condition = (DETAILED_DF['first_trade_class'] == ft_class) & \
                (DETAILED_DF['first_trade_change'] == ft_change) & \
                (DETAILED_DF['second_trade_class'] == st_class) & \
                (DETAILED_DF['second_trade_change'] == st_change)
    subset = DETAILED_DF[condition]

    if subset.empty:
        return [dbc.Alert(f"沒有找到開盤為 {ft_desc} 且中間為 {st_desc} 的數據", color="danger")], None

    total_count = len(subset)
    
    # 計算邏輯不變
    tt_group = subset.groupby(['final_trade_class', 'final_trade_change']).size().reset_index(name='count')
    tt_group['probability'] = tt_group['count'] / total_count
    high_prob = subset['final_high_is_daily_high'].mean()
    low_prob = subset['final_low_is_daily_low'].mean()

    tt_df_display = tt_group.sort_values('probability', ascending=False).rename(columns={
        'final_trade_class': '類別', 'final_trade_change': '變動', 'probability': '機率'
    })
    tt_df_display['機率'] = tt_df_display['機率'].map('{:.2%}'.format)
    tt_table = dbc.Table.from_dataframe(
        tt_df_display[['類別', '變動', '機率']],
        striped=True, bordered=True, hover=True, responsive=True, className="table-dark"
    )

    output_components = [
        html.H5("當前時間: 9:45 (中間時段結束)"),
        html.Ul([html.Li(f"開盤時段: {ft_desc}"), html.Li(f"中間時段: {st_desc}"), html.Li(f"分析基於 {total_count} 個歷史交易日")]),
        html.Hr(),
        html.H6("收盤時段 (9:45-13:45) 預測:"),
        tt_table,
        html.Hr(),
        html.H6("高低點特徵預測:"),
        html.Ul([html.Li(f"創全日最高點概率: {high_prob:.2%}"), html.Li(f"創全日最低點概率: {low_prob:.2%}")])
    ]
    
    return output_components, (None, tt_group, high_prob, low_prob)

def query_general(selections):
    conditions, desc = [], []
    # ... (條件組合邏輯不變)
    if selections['ft_class']:
        conditions.append(DETAILED_DF['first_trade_class'] == selections['ft_class']); desc.append(f"開盤類別: {selections['ft_class']}")
    if selections['ft_change']:
        conditions.append(DETAILED_DF['first_trade_change'] == selections['ft_change']); desc.append(f"開盤變動: {selections['ft_change']}")
    if selections['st_class']:
        conditions.append(DETAILED_DF['second_trade_class'] == selections['st_class']); desc.append(f"中間類別: {selections['st_class']}")
    if selections['st_change']:
        conditions.append(DETAILED_DF['second_trade_change'] == selections['st_change']); desc.append(f"中間變動: {selections['st_change']}")
    if selections['tt_class']:
        conditions.append(DETAILED_DF['final_trade_class'] == selections['tt_class']); desc.append(f"收盤類別: {selections['tt_class']}")
    if selections['tt_change']:
        conditions.append(DETAILED_DF['final_trade_change'] == selections['tt_change']); desc.append(f"收盤變動: {selections['tt_change']}")
    if selections['high_point']:
        conditions.append(DETAILED_DF['final_high_is_daily_high'] == (selections['high_point'] == "創全日最高")); desc.append(f"高點特徵: {selections['high_point']}")
    if selections['low_point']:
        conditions.append(DETAILED_DF['final_low_is_daily_low'] == (selections['low_point'] == "創全日最低")); desc.append(f"低點特徵: {selections['low_point']}")

    if not conditions:
        return [dbc.Alert("請至少選擇一個條件", color="warning")], None

    combined_condition = pd.Series(True, index=DETAILED_DF.index)
    for cond in conditions: combined_condition &= cond
    subset = DETAILED_DF[combined_condition]

    if subset.empty:
        return [dbc.Alert("沒有找到匹配條件的數據", color="danger")], None

    total_count, total_days = len(subset), len(DETAILED_DF)
    probability = total_count / total_days
    
    output_components = [
        html.H5("通用查詢結果"),
        html.Ul([
            html.Li(f"查詢條件: {', '.join(desc)}"),
            html.Li(f"匹配天數: {total_count}"),
            html.Li(f"總天數: {total_days}"),
            html.Li(f"出現概率: {probability:.2%}")
        ]),
        html.Hr(),
        html.H6("匹配日期:"),
        html.P(f"{', '.join(subset['date'].astype(str).tolist())}", style={'wordBreak': 'break-all'})
    ]
    return output_components, None

def create_charts(chart_data, title):
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=("中間時段預測", "收盤時段預測", "高低點預測"),
        specs=[[{"type": "bar"}, {"type": "bar"}, {"type": "bar"}]]
    )
    fig.update_layout(
        template="plotly_dark", 
        title_text=title, 
        showlegend=False, 
        height=450,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="white")
    )

    if chart_data is None:
        return fig.update_layout(annotations=[dict(text="無圖表數據", showarrow=False, font=dict(size=20))])

    st_group, tt_group, high_prob, low_prob = chart_data
    
    if st_group is not None and not st_group.empty:
        st_group['description'] = st_group['second_trade_class'] + '(' + st_group['second_trade_change'] + ')'
        st_group = st_group.sort_values('probability', ascending=False)
        fig.add_trace(go.Bar(x=st_group['description'], y=st_group['probability'], name='中間時段', text=st_group['probability'].apply(lambda x: f'{x:.1%}'), textposition='auto'), row=1, col=1)
    if tt_group is not None and not tt_group.empty:
        tt_group['description'] = tt_group['final_trade_class'] + '(' + tt_group['final_trade_change'] + ')'
        tt_group = tt_group.sort_values('probability', ascending=False)
        fig.add_trace(go.Bar(x=tt_group['description'], y=tt_group['probability'], name='收盤時段', text=tt_group['probability'].apply(lambda x: f'{x:.1%}'), textposition='auto'), row=1, col=2)
    
    fig.add_trace(go.Bar(x=['創全日最高', '創全日最低'], y=[high_prob, low_prob], name='高低點', text=[f'{high_prob:.1%}', f'{low_prob:.1%}'], textposition='auto', marker_color=['#636EFA', '#EF553B']), row=1, col=3)
    fig.update_yaxes(title_text="機率", tickformat=".0%", gridcolor='rgba(255, 255, 255, 0.3)')
    fig.update_xaxes(tickangle=45)
    return fig

# =============================================================================
# 5. 互動邏輯 (Callbacks)
# =============================================================================
@app.callback(Output('data-load-status', 'children'), Input('query-button', 'n_clicks'))
def update_load_status(_):
    if DATA_LOADED: return dbc.Alert(f"數據載入成功 (共 {len(DETAILED_DF)} 天數據)", color="success")
    return dbc.Alert(f"數據載入失敗: {DATA_LOAD_ERROR}", color="danger")

@app.callback(
    [Output('ft-class-dropdown', 'options'), Output('ft-change-dropdown', 'options'),
     Output('st-class-dropdown', 'options'), Output('st-change-dropdown', 'options'),
     Output('tt-class-dropdown', 'options'), Output('tt-change-dropdown', 'options')],
    Input('data-load-status', 'children')
)
def update_dropdown_options(_):
    if not DATA_LOADED: return [[] for _ in range(6)]
    def get_options(col): return [{'label': i, 'value': i} for i in sorted(DETAILED_DF[col].dropna().unique())]
    return (get_options('first_trade_class'), get_options('first_trade_change'),
            get_options('second_trade_class'), get_options('second_trade_change'),
            get_options('final_trade_class'), get_options('final_trade_change'))

@app.callback(
    [Output('ft-class-dropdown', 'disabled'), Output('ft-change-dropdown', 'disabled'),
     Output('st-class-dropdown', 'disabled'), Output('st-change-dropdown', 'disabled'),
     Output('tt-class-dropdown', 'disabled'), Output('tt-change-dropdown', 'disabled'),
     Output('high-point-dropdown', 'disabled'), Output('low-point-dropdown', 'disabled')],
    Input('time-selector', 'value')
)
def update_dropdown_disabled_state(selected_time):
    if selected_time == '8:45': return [True] * 8
    if selected_time == '9:15': return [False, False] + [True] * 6
    if selected_time == '9:45': return [False, False, False, False] + [True] * 4
    return [False] * 8

@app.callback(
    [Output('results-text-output', 'children'), Output('results-chart-output', 'figure')],
    Input('query-button', 'n_clicks'),
    [State('time-selector', 'value'), State('ft-class-dropdown', 'value'), State('ft-change-dropdown', 'value'),
     State('st-class-dropdown', 'value'), State('st-change-dropdown', 'value'), State('tt-class-dropdown', 'value'),
     State('tt-change-dropdown', 'value'), State('high-point-dropdown', 'value'), State('low-point-dropdown', 'value')],
    prevent_initial_call=True
)
def handle_query(n_clicks, time, ft_class, ft_change, st_class, st_change, tt_class, tt_change, high_point, low_point):
    if not DATA_LOADED:
        return [dbc.Alert("數據尚未載入，無法查詢。", color="danger")], go.Figure().update_layout(title="結果圖表", template="plotly_dark")

    if time == '9:15':
        text_components, chart_data = query_for_915(ft_class, ft_change)
        fig = create_charts(chart_data, f"9:15 預測 (基於開盤: {ft_class}({ft_change}))")
        return text_components, fig
    elif time == '9:45':
        text_components, chart_data = query_for_945(ft_class, ft_change, st_class, st_change)
        fig = create_charts(chart_data, f"9:45 預測 (基於前兩時段)")
        return text_components, fig
    else:
        selections = {'ft_class': ft_class, 'ft_change': ft_change, 'st_class': st_class, 'st_change': st_change,
                      'tt_class': tt_class, 'tt_change': tt_change, 'high_point': high_point, 'low_point': low_point}
        text_components, _ = query_general(selections)
        fig = create_charts(None, "通用查詢無預測圖表")
        return text_components, fig

@app.callback(
    [Output('ft-class-dropdown', 'value'), Output('ft-change-dropdown', 'value'),
     Output('st-class-dropdown', 'value'), Output('st-change-dropdown', 'value'),
     Output('tt-class-dropdown', 'value'), Output('tt-change-dropdown', 'value'),
     Output('high-point-dropdown', 'value'), Output('low-point-dropdown', 'value')],
    Input('reset-button', 'n_clicks'),
    prevent_initial_call=True
)
def reset_dropdowns(n_clicks):
    return [None] * 8

# =============================================================================
# 6. 應用程式啟動
# =============================================================================
if __name__ == '__main__':
    app.run(debug=True, port=8051)