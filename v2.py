import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 页面配置
st.set_page_config(layout="wide", page_title="Professional Volume Profile")

st.title("🎯 专业筹码分布分析 (含 POC 控制点)")

# 侧边栏
with st.sidebar:
    st.header("控制面板")
    symbol = st.text_input("股票代码", value="TSLA")
    period = st.selectbox("分析周期", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
    bins = st.slider("价格灵敏度 (Bins)", 30, 150, 70)

@st.cache_data
def get_data(ticker, p):
    df = yf.download(ticker, period=p)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

try:
    df = get_data(symbol, period)
    
    # --- 筹码分布核心计算 ---
    price_min, price_max = df['Low'].min(), df['High'].max()
    df['bin'] = pd.cut(df['Close'], bins=bins)
    
    # 聚合每个价格区间的成交量
    volume_profile = df.groupby('bin', observed=True)['Volume'].sum().reset_index()
    volume_profile['price_mid'] = volume_profile['bin'].apply(lambda x: x.mid)
    
    # 查找 POC (成交量最大的行)
    poc_idx = volume_profile['Volume'].idxmax()
    poc_price = volume_profile.loc[poc_idx, 'price_mid']
    max_vol = volume_profile['Volume'].max()

    # --- 绘图 ---
    fig = make_subplots(
        rows=1, cols=2, shared_yaxes=True, 
        column_widths=[0.75, 0.25], horizontal_spacing=0.02
    )

    # 1. K线图
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], 
        low=df['Low'], close=df['Close'], name="K线"
    ), row=1, col=1)

    # 在K线上画出 POC 横线
    fig.add_shape(
        type="line", x0=df.index[0], x1=df.index[-1],
        y0=poc_price, y1=poc_price,
        line=dict(color="Gold", width=2, dash="dash"),
        row=1, col=1
    )

    # 2. 筹码分布柱状图
    # 为 POC 柱子设置特殊颜色
    colors = ['rgba(100, 149, 237, 0.5)'] * len(volume_profile)
    colors[poc_idx] = 'rgba(255, 215, 0, 0.9)' # 金色高亮 POC

    fig.add_trace(go.Bar(
        x=volume_profile['Volume'],
        y=volume_profile['price_mid'],
        orientation='h',
        marker_color=colors,
        name="成交量分布",
        hoverinfo="x+y"
    ), row=1, col=2)

    # 布局美化
    fig.update_layout(
        template="plotly_dark",
        height=750,
        showlegend=False,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=30, b=10)
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # 底部数据卡片
    c1, c2, c3 = st.columns(3)
    c1.metric("当前价", f"${df['Close'].iloc[-1]:.2f}")
    c2.metric("POC 密集区价格", f"${poc_price:.2f}", help="成交量最集中的价格点")
    c3.metric("总成交量", f"{df['Volume'].sum()/1e6:.1f}M")

except Exception as e:
    st.error(f"分析失败: {e}")
