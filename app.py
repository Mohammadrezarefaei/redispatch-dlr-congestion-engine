import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.redispatch_optimizer import run_redispatch_simulation
import streamlit as st

st.set_page_config(
    page_title='Redispatch 2.0 & DLR Congestion Engine',
    page_icon='⚡',
    layout='wide',
)

st.markdown(
    """
<style>
    div[data-testid="stMetric"] {
        background-color: #050b1f;
        border: 2px solid #0055ff;
        padding: 16px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 14px rgba(0, 85, 255, 0.25);
    }
    div[data-testid="stMetricLabel"] {
        color: #ffffff;
        font-size: 0.9rem;
        font-weight: 600;
    }
    div[data-testid="stMetricValue"] {
        color: #ffffff;
        font-size: 1.6rem;
        font-weight: 700;
    }
    hr {
        border-top: 1px solid #0044ff;
        margin: 25px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title('⚡ Redispatch 2.0 & Dynamic Line Rating (DLR) Engine')
st.markdown(
    "<p style='color: #cbd5e1; font-size: 1.05rem; margin-top: -10px;'>"
    'Physics-based power flow bottleneck management across German transmission'
    " corridors using <b style='color: #00ddff;'>Dynamic Line Rating (IEEE"
    ' 738)</b>.</p>',
    unsafe_allow_html=True,
)

# Sidebar
st.sidebar.markdown('### ⚙️ Grid & Simulation Controls')
horizon_days = st.sidebar.slider(
    'Simulation Horizon (Days)', min_value=3, max_value=14, value=7, step=1
)
wind_scaling = st.sidebar.slider(
    'Wind Infeed Multiplier', min_value=0.8, max_value=2.0, value=1.2, step=0.1
)
static_limit = st.sidebar.number_input(
    'Static Line Capacity (MVA)', min_value=50.0, max_value=120.0, value=75.0
)

# Simulation Horizon
n_hours = horizon_days * 24
dates = pd.date_range('2026-08-01 00:00:00', periods=n_hours, freq='h')
hours = dates.hour.to_numpy()

wind_infeed = (
    45.0
    + 55.0
    * np.clip(
        np.sin(np.linspace(0, horizon_days * np.pi, n_hours))
        + np.random.normal(0, 0.15, n_hours),
        0,
        None,
    )
) * wind_scaling
south_load = (
    65.0
    + 30.0 * np.sin((hours - 6) * np.pi / 12)
    + np.random.normal(0, 2.0, n_hours)
)
ambient_temp = 18.0 + 8.0 * np.sin((hours - 9) * np.pi / 12)
wind_speed = 3.5 + 4.5 * np.abs(
    np.sin(np.linspace(0, horizon_days / 2 * np.pi, n_hours))
)

df = run_redispatch_simulation(
    dates,
    wind_infeed,
    south_load,
    ambient_temp,
    wind_speed,
    static_limit_mva=static_limit,
)

total_static_cost = df['cost_static_eur'].sum()
total_dlr_cost = df['cost_dlr_eur'].sum()
savings_eur = total_static_cost - total_dlr_cost
savings_pct = (
    (savings_eur / total_static_cost * 100) if total_static_cost > 0 else 0
)
energy_saved = (
    df['curtailment_static_mw'].sum() - df['curtailment_dlr_mw'].sum()
)

# KPI Cards
k1, k2, k3, k4 = st.columns(4)
k1.metric('Static Redispatch Cost', f'€{total_static_cost:,.2f}')
k2.metric('DLR-Optimized Cost', f'€{total_dlr_cost:,.2f}')
k3.metric('Congestion Cost Savings', f'{savings_pct:.1f}%')
k4.metric('Green Energy Recovered', f'{energy_saved:,.1f} MWh')

st.markdown('<hr>', unsafe_allow_html=True)

# Legend & Tooltip Styling
pure_blue_legend = dict(
    orientation='h',
    yanchor='bottom',
    y=1.05,
    xanchor='right',
    x=1.0,
    bgcolor='#003cd2',
    bordercolor='#ffffff',
    borderwidth=2,
    font=dict(color='#ffffff', size=12, family='Arial, sans-serif'),
)

pure_blue_hover = dict(
    bgcolor='#002db3',
    bordercolor='#ffffff',
    font=dict(color='#ffffff', size=13, family='Arial, sans-serif'),
)

# Plot 1: Corridor Power Flow vs DLR Capacity
st.markdown(
    '#### 1. Corridor Bottleneck Flow vs. Weather-Aware DLR Capacity (MVA)'
)
fig1 = go.Figure()
fig1.add_trace(
    go.Scatter(
        x=df['timestamp'],
        y=df['dlr_limit_mva'],
        name='Dynamic Line Rating (DLR MVA)',
        line=dict(color='#10b981', width=2.4),
    )
)
fig1.add_trace(
    go.Scatter(
        x=df['timestamp'],
        y=df['corridor_flow_mw'],
        name='Corridor Flow (MW)',
        line=dict(color='#ffffff', width=2.0),
    )
)
fig1.add_trace(
    go.Scatter(
        x=df['timestamp'],
        y=df['static_limit_mva'],
        name='Static Limit (75 MVA)',
        line=dict(color='#ef4444', width=1.8, dash='dash'),
    )
)

fig1.update_layout(
    template='plotly_dark',
    plot_bgcolor='#060913',
    paper_bgcolor='#060913',
    height=400,
    margin=dict(l=20, r=20, t=60, b=20),
    legend=pure_blue_legend,
    hoverlabel=pure_blue_hover,
    xaxis=dict(gridcolor='#1e293b', title='Timeline'),
    yaxis=dict(gridcolor='#1e293b', title='Power / Capacity [MVA]'),
    hovermode='x unified',
)
st.plotly_chart(fig1, use_container_width=True)

# Plot 2: Redispatch Cost Subplots
st.markdown(
    '#### 2. Redispatch 2.0 Congestion Mitigation & Curtailment Reduction'
)
fig2 = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.12,
    subplot_titles=(
        'Hourly Redispatch Cost Comparison (€/h)',
        'Wind Infeed vs. Curtailed Energy (MW)',
    ),
)

fig2.add_trace(
    go.Bar(
        x=df['timestamp'],
        y=df['cost_static_eur'],
        name='Static Limit Cost (€)',
        marker_color='#ef4444',
        opacity=0.7,
    ),
    row=1,
    col=1,
)
fig2.add_trace(
    go.Bar(
        x=df['timestamp'],
        y=df['cost_dlr_eur'],
        name='DLR Optimized Cost (€)',
        marker_color='#10b981',
        opacity=0.9,
    ),
    row=1,
    col=1,
)

fig2.add_trace(
    go.Scatter(
        x=df['timestamp'],
        y=df['wind_infeed_mw'],
        name='Wind Infeed (MW)',
        line=dict(color='#38bdf8', width=1.8),
    ),
    row=2,
    col=1,
)
fig2.add_trace(
    go.Scatter(
        x=df['timestamp'],
        y=df['curtailment_static_mw'],
        name='Static Curtailment (MW)',
        line=dict(color='#f43f5e', width=1.6, dash='dot'),
    ),
    row=2,
    col=1,
)

fig2.update_layout(
    template='plotly_dark',
    plot_bgcolor='#060913',
    paper_bgcolor='#060913',
    height=500,
    margin=dict(l=20, r=20, t=60, b=20),
    legend=pure_blue_legend,
    hoverlabel=pure_blue_hover,
    hovermode='x unified',
)
fig2.update_xaxes(gridcolor='#1e293b')
fig2.update_yaxes(gridcolor='#1e293b')

st.plotly_chart(fig2, use_container_width=True)
