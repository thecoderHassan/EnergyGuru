# ============================================================
#   ENERGYGURU – POWER CALCULUS
#   Streamlit Dashboard  |  dashboard.py
#   Run: streamlit run dashboard.py
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import serial
import serial.tools.list_ports
import time
import math
import random
from datetime import datetime, timedelta

# ── Page config (MUST be first Streamlit call) ───────────────
st.set_page_config(
    page_title="EnergyGuru – Power Calculus",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Barlow', sans-serif; background-color: #080c14; color: #ffffff; }
    #MainMenu, footer { visibility: hidden; }
    .eg-card { background: linear-gradient(145deg, #0d1422, #111827); border: 1px solid #1e3a52; border-radius: 10px; padding: 16px 14px 12px 14px; text-align: center; position: relative; overflow: hidden; }
    .eg-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: var(--accent); }
    .eg-value { font-family: 'Share Tech Mono', monospace; font-size: 1.55rem; font-weight: bold; color: var(--accent); letter-spacing: 1px; }
    .eg-label { font-size: 0.72rem; color: #6b7a90; margin-top: 3px; text-transform: uppercase; letter-spacing: 1.5px; }
    .eg-section { font-family: 'Share Tech Mono', monospace; color: #00c8ff; font-size: 0.78rem; letter-spacing: 3px; text-transform: uppercase; border-left: 3px solid #00c8ff; padding-left: 10px; margin: 18px 0 10px 0; }
    .status-live  { color: #00ff99; font-size: 0.75rem; }
    .status-demo  { color: #ffcc00; font-size: 0.75rem; }
    .status-off   { color: #ff4466; font-size: 0.75rem; }
    section[data-testid="stSidebar"] { background: #080c14; border-right: 1px solid #1a2840; }
    .eg-footer { margin-top: 18px; padding: 10px 0 2px 0; border-top: 1px solid #1a2840; text-align: center; }
    .eg-footer-title {
        font-family:'Share Tech Mono',monospace; font-size: 1.05rem; color: #00c8ff;
        letter-spacing: 2px; text-transform: uppercase;
        text-shadow: 0 0 6px rgba(0,200,255,0.75), 0 0 14px rgba(0,200,255,0.45);
        animation: egGlowTitle 1.8s ease-in-out infinite alternate;
    }
    .eg-footer-text {
        margin-top: 5px; font-family:'Share Tech Mono',monospace; font-size: 0.8rem;
        color: #9ec3df; letter-spacing: 1px; text-transform: uppercase;
        text-shadow: 0 0 6px rgba(120,200,255,0.65), 0 0 12px rgba(120,200,255,0.35);
        animation: egGlowText 2.2s ease-in-out infinite alternate;
    }
    @keyframes egGlowTitle {
        from { text-shadow: 0 0 4px rgba(0,200,255,0.55), 0 0 10px rgba(0,200,255,0.30); }
        to   { text-shadow: 0 0 9px rgba(0,200,255,0.95), 0 0 18px rgba(0,200,255,0.55); }
    }
    @keyframes egGlowText {
        from { text-shadow: 0 0 4px rgba(120,200,255,0.45), 0 0 9px rgba(120,200,255,0.20); }
        to   { text-shadow: 0 0 8px rgba(120,200,255,0.85), 0 0 16px rgba(120,200,255,0.40); }
    }
    @media (max-width: 768px) {
        .eg-value { font-size: 1.2rem; }
        .eg-label { font-size: 0.66rem; letter-spacing: 1px; }
        .eg-section { font-size: 0.7rem; letter-spacing: 2px; }
    }
    </style>
""", unsafe_allow_html=True)

# ── Constants ────────────────────────────────────────────────
CITY_LOCATIONS = {
    "Rawalpindi City Model": {"lat": 33.6007, "lon": 73.0679, "desc": "Punjab, Pakistan"},
    "Islamabad Lab":         {"lat": 33.7215, "lon": 73.0433, "desc": "Federal Capital, Pakistan"},
    "Lahore Smart Lab":      {"lat": 31.5204, "lon": 74.3587, "desc": "Punjab, Pakistan"},
    "Karachi IoT Hub":       {"lat": 24.8607, "lon": 67.0011, "desc": "Sindh, Pakistan"},
    "Custom Location":       {"lat": 33.6007, "lon": 73.0679, "desc": "User-defined"},
}

ACCENT_COLORS = {
    "voltage":  "#00c8ff",
    "current":  "#ff9500",
    "power":    "#ff4466",
    "energy":   "#00ff99",
    "bill":     "#ffd700",
    "carbon":   "#88ff00",
}

# ── Session State Init ───────────────────────────────────────
COLS = ['timestamp', 'voltage', 'current', 'power',
        'energy_kwh', 'bill_pkr', 'carbon_kg', 'runtime_hrs']

def _init_state():
    defaults = {
        'data_log':    pd.DataFrame(columns=COLS),
        'connected':   False,
        'serial_conn': None,
        'demo_mode':   True,
        'demo_v_base': 220.0,
        'demo_i_base': 1.8,
        'demo_energy': 0.0,
        'demo_tick':   0,
        'last_sample_ts': 0.0,
        'sample_interval_s': 1.0,
        'latest': {k: 0.0 for k in
                   ['voltage','current','power','energy_kwh','bill_pkr','carbon_kg','runtime_hrs']},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-family:'Share Tech Mono',monospace; color:#00c8ff;
                font-size:1.1rem; letter-spacing:3px; padding:10px 0 4px 0;">
        ⚡ ENERGYGURU
    </div>
    <div style="color:#4a6080; font-size:0.68rem; letter-spacing:2px; margin-bottom:16px;">
        POWER CALCULUS v1.0
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="eg-section">Connection</div>', unsafe_allow_html=True)
    demo_mode = st.toggle("🎮 Demo Mode (No Hardware)", value=st.session_state.demo_mode)
    st.session_state.demo_mode = demo_mode

    if not demo_mode:
        ports_list = serial.tools.list_ports.comports()

arduino_ports = []

for p in ports_list:
    desc = str(p.description).lower()

    if (
        "arduino" in desc
        or "ch340" in desc
        or "usb serial" in desc
        or "cp210" in desc
    ):
        arduino_ports.append(p.device)

selected_port = None

if arduino_ports:
    selected_port = st.selectbox(
        "Select Arduino Port",
        arduino_ports
    )
else:
    st.warning("Arduino not detected")

# optional debug
for p in ports_list:
    st.caption(f"{p.device} - {p.description}")
        c1, c2 = st.columns(2)
        with c1:
    if st.button("▶ Connect", use_container_width=True):

        if selected_port is None:
            st.error("Please select Arduino port first")

        else:
            try:
                # close old port if open
                if st.session_state.serial_conn:
                    try:
                        st.session_state.serial_conn.close()
                    except:
                        pass

                time.sleep(1)

                # open selected port
                ser = serial.Serial(
                    selected_port,
                    baud,
                    timeout=2
                )

                time.sleep(2)
                ser.reset_input_buffer()

                st.session_state.serial_conn = ser
                st.session_state.connected = True

                st.success(f"Connected to {selected_port}")

            except Exception as e:
                st.error(str(e))
        with c2:
            if st.button("■ Disconnect", use_container_width=True):
                if st.session_state.serial_conn:
                    try: st.session_state.serial_conn.close()
                    except: pass
                st.session_state.connected = False
                st.session_state.serial_conn = None

    # Status indicator
    if demo_mode:
        st.markdown('<p class="status-demo">◉ DEMO MODE ACTIVE</p>', unsafe_allow_html=True)
    elif st.session_state.connected:
        st.markdown('<p class="status-live">◉ ARDUINO CONNECTED</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-off">◉ DISCONNECTED</p>', unsafe_allow_html=True)

    if demo_mode:
        st.markdown('<div class="eg-section">Demo Controls</div>', unsafe_allow_html=True)
        st.session_state.demo_v_base = st.slider(
            "Demo Voltage (V)",
            min_value=180.0,
            max_value=260.0,
            value=float(st.session_state.demo_v_base),
            step=0.5,
        )
        st.session_state.demo_i_base = st.slider(
            "Demo Current (A)",
            min_value=0.1,
            max_value=5.0,
            value=float(st.session_state.demo_i_base),
            step=0.05,
        )
        if st.button("↺ Reset Demo Profile", use_container_width=True):
            # Revert to the original synthetic profile baseline.
            st.session_state.demo_v_base = 220.0
            st.session_state.demo_i_base = 1.8
            st.success("Demo profile reset to default dummy data behavior.")

    st.markdown('<div class="eg-section">Settings</div>', unsafe_allow_html=True)
    rate   = st.number_input("💰 Tariff (PKR / kWh)", 1.0, 500.0, 50.0, 1.0)
    carbon = st.number_input("🌱 Carbon Factor (kg CO₂ / kWh)", 0.1, 3.0, 0.82, 0.01)

    st.markdown('<div class="eg-section">Location</div>', unsafe_allow_html=True)
    city_choice = st.selectbox("City / Lab", list(CITY_LOCATIONS.keys()))
    if city_choice == "Custom Location":
        CITY_LOCATIONS["Custom Location"]["lat"] = st.number_input("Latitude",  value=33.6007)
        CITY_LOCATIONS["Custom Location"]["lon"] = st.number_input("Longitude", value=73.0679)
        CITY_LOCATIONS["Custom Location"]["desc"] = st.text_input("Description", "Custom Site")

    loc = CITY_LOCATIONS[city_choice]

    st.markdown('<div class="eg-section">Controls</div>', unsafe_allow_html=True)
    if st.button("🗑 Clear Data Log", use_container_width=True):
        st.session_state.data_log    = pd.DataFrame(columns=COLS)
        st.session_state.demo_energy = 0.0
        st.session_state.demo_tick   = 0
        st.session_state.last_sample_ts = 0.0
        st.success("Cleared!")

    # Buffer info
    n = len(st.session_state.data_log)
    st.markdown(f'<div style="color:#4a6080;font-size:0.72rem;margin-top:8px;">Buffer: {n}/500 readings</div>',
                unsafe_allow_html=True)

# ── Data Functions ───────────────────────────────────────────
def _demo_reading():
    """Simulate a realistic city-model reading."""
    t     = st.session_state.demo_tick
    st.session_state.demo_tick += 1

    v_base = float(st.session_state.demo_v_base)
    i_base = float(st.session_state.demo_i_base)

    # AC voltage ~220 V with ±6 V fluctuation
    v = v_base + 5 * math.sin(t * 0.07) + random.uniform(-2, 2)
    # Load current varies 0.8–2.8 A (city model lamps + motors)
    i = i_base + 0.6 * math.sin(t * 0.04) + 0.2 * math.sin(t * 0.13) + random.uniform(-0.05, 0.05)
    i = max(0.1, i)
    p = v * i

    dt_h = 1 / 3600
    st.session_state.demo_energy += (p / 1000) * dt_h

    e   = st.session_state.demo_energy
    b   = e * rate
    co2 = e * carbon
    rth = t / 3600

    return dict(voltage=round(v,2), current=round(i,3),
                power=round(p,2),  energy_kwh=round(e,6),
                bill_pkr=round(b,4), carbon_kg=round(co2,6),
                runtime_hrs=round(rth,5))

def _arduino_reading():
    """Read one CSV line from Arduino serial."""
    conn = st.session_state.serial_conn
    if not conn or not st.session_state.connected:
        return None
    try:
        raw = conn.readline().decode('utf-8', errors='ignore').strip()
        if ',' in raw:
            p = raw.split(',')
            if len(p) == 7:
                return dict(voltage=float(p[0]),    current=float(p[1]),
                            power=float(p[2]),       energy_kwh=float(p[3]),
                            bill_pkr=float(p[4]),    carbon_kg=float(p[5]),
                            runtime_hrs=float(p[6]))
    except Exception:
        pass
    return None

def _log(data):
    """Append to session log; keep last 500 rows."""
    row = pd.DataFrame([{"timestamp": datetime.now(), **data}])
    st.session_state.data_log = pd.concat(
        [st.session_state.data_log, row], ignore_index=True
    ).tail(500)
    st.session_state.latest = data

# ── Fetch current reading ────────────────────────────────────
now_ts = time.time()
can_sample = (now_ts - float(st.session_state.last_sample_ts)) >= float(st.session_state.sample_interval_s)

if can_sample:
    if st.session_state.demo_mode:
        _log(_demo_reading())
        st.session_state.last_sample_ts = now_ts
    elif st.session_state.connected:
        d = _arduino_reading()
        if d:
            _log(d)
            st.session_state.last_sample_ts = now_ts

latest = st.session_state.latest
df     = st.session_state.data_log.copy()

def render_footer():
    st.markdown(
        '<div class="eg-footer"><div class="eg-footer-title">ENERGYGURU</div>'
        '<div class="eg-footer-text">A PRODUCT OF 7PSOLUTIONS: 7PS CAAD LABS</div></div>',
        unsafe_allow_html=True
    )

def render_device_alerts(latest_row):
    if st.session_state.demo_mode:
        st.info("🧪 Demo mode is active. Values are simulated unless connected to Arduino.")
        return

    if not st.session_state.connected:
        st.error("🔴 Device status: Arduino is disconnected.")
        return

    v = float(latest_row.get("voltage", 0.0))
    i = float(latest_row.get("current", 0.0))
    p = float(latest_row.get("power", 0.0))

    if v < 195 or v > 255:
        st.error("🔴 Critical voltage detected. Check supply and wiring.")
    elif v < 210 or v > 240:
        st.warning("🟠 Voltage is borderline. Monitor stability.")
    else:
        st.success("🟢 Device status: connected and electrical values are stable.")

    if i > 4.2:
        st.warning("🟠 High current draw detected.")
    if p > 1000:
        st.warning("🟠 Power near upper expected limit.")

# ── Header ───────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; align-items:baseline; gap:12px; padding:6px 0 4px 0;">
    <span style="font-family:'Share Tech Mono',monospace; font-size:1.7rem; color:#00c8ff;">
        ⚡ ENERGYGURU
    </span>
    <span style="font-family:'Share Tech Mono',monospace; font-size:0.9rem; color:#3a5a80;">
        POWER CALCULUS — AI-Assisted City Energy Monitor
    </span>
</div>
<hr style="border-color:#1a2840; margin:6px 0 14px 0;">
""", unsafe_allow_html=True)

# ── Tabs ─────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "⚡  Live Dashboard",
    "🗺️  City Map",
    "📈  Analytics",
    "📄  Report",
])

# ════════════════════════════════════════════════════════════
# TAB 1 – LIVE DASHBOARD
# ════════════════════════════════════════════════════════════
with tab1:
    render_device_alerts(latest)

    # ── 6 metric cards ──────────────────────────────────────
    cards = [
        ("⚡ VOLTAGE",  f"{latest['voltage']:.1f} V",   "#00c8ff"),
        ("🔌 CURRENT",  f"{latest['current']:.3f} A",   "#ff9500"),
        ("💡 POWER",    f"{latest['power']:.1f} W",     "#ff4466"),
        ("🔋 ENERGY",   f"{latest['energy_kwh']:.5f} kWh", "#00ff99"),
        ("💰 BILL",     f"₨ {latest['bill_pkr']:.3f}", "#ffd700"),
        ("🌱 CO₂",      f"{latest['carbon_kg']:.5f} kg", "#88ff00"),
    ]
    cards_per_row = 6
    for i in range(0, len(cards), cards_per_row):
        row_cards = cards[i:i + cards_per_row]
        cols = st.columns(len(row_cards))
        for col, (lbl, val, clr) in zip(cols, row_cards):
            with col:
                st.markdown(f"""
                <div class="eg-card" style="--accent:{clr}">
                    <div class="eg-value" style="color:{clr}">{val}</div>
                    <div class="eg-label">{lbl}</div>
                </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 3 gauges ────────────────────────────────────────────
    def gauge(value, title, max_v, color, unit, threshold=0.85):
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            title={'text': title, 'font': {'color': '#8a9ab0', 'size': 12,
                                            'family': 'Share Tech Mono'}},
            number={'suffix': f' {unit}', 'font': {'color': color, 'size': 20,
                                                     'family': 'Share Tech Mono'}},
            gauge={
                'axis': {'range': [0, max_v], 'tickcolor': '#2a3a50',
                         'tickfont': {'size': 9, 'color': '#4a6080'}},
                'bar':  {'color': color, 'thickness': 0.25},
                'bgcolor': '#0d1422',
                'bordercolor': '#1a2840', 'borderwidth': 1,
                'steps': [
                    {'range': [0, max_v * 0.5],        'color': '#0d1422'},
                    {'range': [max_v * 0.5, max_v * threshold], 'color': '#111d2e'},
                    {'range': [max_v * threshold, max_v],       'color': '#1a1020'},
                ],
                'threshold': {'line': {'color': '#ff4466', 'width': 2},
                              'thickness': 0.75, 'value': max_v * threshold}
            }
        ))
        fig.update_layout(paper_bgcolor='#080c14', font_color='white',
                          height=200, margin=dict(l=15,r=15,t=40,b=5))
        return fig

    gauge_cols = st.columns(3)
    gauge_specs = [
        (latest['voltage'], "VOLTAGE (V)", 260, "#00c8ff", "V"),
        (latest['current'], "CURRENT (A)", 5, "#ff9500", "A"),
        (latest['power'], "POWER (W)", 1100, "#ff4466", "W"),
    ]
    for col, spec in zip(gauge_cols, gauge_specs):
        with col:
            st.plotly_chart(gauge(*spec), use_container_width=True)

    # ── Real-time charts ────────────────────────────────────
    if len(df) > 1:
        rc1, rc2 = st.columns(2)

        with rc1:
            st.markdown('<div class="eg-section">Voltage & Current — Live</div>', unsafe_allow_html=True)
            fig_vc = go.Figure()
            fig_vc.add_trace(go.Scatter(
                x=df['timestamp'], y=df['voltage'],
                name='Voltage (V)', line=dict(color='#00c8ff', width=1.8), yaxis='y1'
            ))
            fig_vc.add_trace(go.Scatter(
                x=df['timestamp'], y=df['current'],
                name='Current (A)', line=dict(color='#ff9500', width=1.8), yaxis='y2'
            ))
            fig_vc.update_layout(
                paper_bgcolor='#080c14', plot_bgcolor='#0d1422',
                font_color='white', height=260,
                yaxis=dict(title='V', color='#00c8ff', gridcolor='#0d1e2e'),
                yaxis2=dict(title='A', overlaying='y', side='right',
                            color='#ff9500', gridcolor='#0d1e2e'),
                legend=dict(bgcolor='#0d1422', font=dict(size=10)),
                margin=dict(l=8,r=8,t=8,b=8),
            )
            st.plotly_chart(fig_vc, use_container_width=True)

        with rc2:
            st.markdown('<div class="eg-section">Power — Live</div>', unsafe_allow_html=True)
            fig_pw = go.Figure()
            fig_pw.add_trace(go.Scatter(
                x=df['timestamp'], y=df['power'],
                fill='tozeroy', name='Power (W)',
                line=dict(color='#ff4466', width=1.8),
                fillcolor='rgba(255,68,102,0.15)'
            ))
            fig_pw.update_layout(
                paper_bgcolor='#080c14', plot_bgcolor='#0d1422',
                font_color='white', height=260,
                yaxis=dict(title='Watts', gridcolor='#0d1e2e'),
                margin=dict(l=8,r=8,t=8,b=8),
            )
            st.plotly_chart(fig_pw, use_container_width=True)
    else:
        st.info("📡 Collecting readings… Charts will appear after a few seconds.")


# ════════════════════════════════════════════════════════════
# TAB 2 – CITY MAP
# ════════════════════════════════════════════════════════════
with tab2:
    map_col, info_col = st.columns([3, 1])

    with map_col:
        st.markdown('<div class="eg-section">City Energy Monitor — Location</div>',
                    unsafe_allow_html=True)

        # Build coverage ring
        ring_lats = [loc['lat'] + 0.012 * math.cos(math.radians(i)) for i in range(361)]
        ring_lons = [loc['lon'] + 0.018 * math.sin(math.radians(i)) for i in range(361)]

        fig_map = go.Figure()

        # Coverage ring
        fig_map.add_trace(go.Scattermapbox(
            lat=ring_lats, lon=ring_lons,
            mode='lines',
            line=dict(color='rgba(0,200,255,0.4)', width=2),
            name='Monitor Zone', showlegend=False,
        ))

        # Main marker
        fig_map.add_trace(go.Scattermapbox(
            lat=[loc['lat']], lon=[loc['lon']],
            mode='markers+text',
            marker=dict(size=18, color='#00c8ff',
                        symbol='circle', opacity=0.9),
            text=[f"⚡  {city_choice}"],
            textposition='top right',
            textfont=dict(color='white', size=13, family='Share Tech Mono'),
            name=city_choice,
        ))

        fig_map.update_layout(
            mapbox=dict(
                style='open-street-map',
                center=dict(lat=loc['lat'], lon=loc['lon']),
                zoom=13,
            ),
            paper_bgcolor='#080c14',
            font_color='white',
            height=480,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig_map, use_container_width=True)

    with info_col:
        st.markdown('<div class="eg-section">Location</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="font-family:'Share Tech Mono',monospace; font-size:0.78rem;
                    color:#8a9ab0; line-height:1.9;">
            <div style="color:#00c8ff; font-size:0.95rem; margin-bottom:4px;">{city_choice}</div>
            {loc['desc']}<br>
            LAT: {loc['lat']:.4f}°<br>
            LON: {loc['lon']:.4f}°
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="eg-section">Live Readings</div>', unsafe_allow_html=True)
        st.metric("Voltage",  f"{latest['voltage']:.1f} V")
        st.metric("Current",  f"{latest['current']:.3f} A")
        st.metric("Power",    f"{latest['power']:.1f} W")

        st.markdown('<div class="eg-section">Totals</div>', unsafe_allow_html=True)
        st.metric("Energy",   f"{latest['energy_kwh']:.5f} kWh")
        st.metric("Bill",     f"₨ {latest['bill_pkr']:.3f}")
        st.metric("CO₂",      f"{latest['carbon_kg']:.5f} kg")

        # Voltage health check
        st.markdown('<div class="eg-section">Power Quality</div>', unsafe_allow_html=True)
        v = latest['voltage']
        if 210 <= v <= 240:
            st.success("✅ Voltage Normal")
        elif 195 <= v < 210 or 240 < v <= 255:
            st.warning("⚠️ Voltage Borderline")
        else:
            st.error("❌ Voltage Abnormal")


# ════════════════════════════════════════════════════════════
# TAB 3 – ANALYTICS
# ════════════════════════════════════════════════════════════
with tab3:
    if len(df) < 5:
        st.info("📡 Need at least 5 readings — collecting data…")
    else:
        # Summary row
        st.markdown('<div class="eg-section">Summary Statistics</div>', unsafe_allow_html=True)
        s1,s2,s3,s4,s5 = st.columns(5)
        s1.metric("Avg Voltage",  f"{df['voltage'].mean():.2f} V",  f"σ={df['voltage'].std():.2f}")
        s2.metric("Avg Current",  f"{df['current'].mean():.3f} A",  f"σ={df['current'].std():.3f}")
        s3.metric("Avg Power",    f"{df['power'].mean():.1f} W")
        s4.metric("Peak Power",   f"{df['power'].max():.1f} W")
        s5.metric("Total Energy", f"{df['energy_kwh'].iloc[-1]:.5f} kWh")

        st.markdown('<div class="eg-section">Energy & Bill Trends</div>', unsafe_allow_html=True)
        ac1, ac2 = st.columns(2)

        with ac1:
            fig_e = px.area(df, x='timestamp', y='energy_kwh',
                            color_discrete_sequence=['#00ff99'],
                            labels={'energy_kwh': 'kWh', 'timestamp': ''})
            fig_e.update_layout(paper_bgcolor='#080c14', plot_bgcolor='#0d1422',
                                 font_color='white', height=260,
                                 margin=dict(l=8,r=8,t=8,b=8))
            st.plotly_chart(fig_e, use_container_width=True)

        with ac2:
            fig_bc = go.Figure()
            fig_bc.add_trace(go.Scatter(x=df['timestamp'], y=df['bill_pkr'],
                                        name='Bill (PKR)', yaxis='y1',
                                        line=dict(color='#ffd700', width=1.8)))
            fig_bc.add_trace(go.Scatter(x=df['timestamp'], y=df['carbon_kg'],
                                        name='CO₂ (kg)', yaxis='y2',
                                        line=dict(color='#88ff00', width=1.8)))
            fig_bc.update_layout(
                paper_bgcolor='#080c14', plot_bgcolor='#0d1422', font_color='white',
                height=260,
                yaxis=dict(title='PKR', color='#ffd700', gridcolor='#0d1e2e'),
                yaxis2=dict(title='kg CO₂', overlaying='y', side='right',
                            color='#88ff00'),
                legend=dict(bgcolor='#0d1422', font=dict(size=10)),
                margin=dict(l=8,r=8,t=8,b=8),
            )
            st.plotly_chart(fig_bc, use_container_width=True)

        # Power histogram
        st.markdown('<div class="eg-section">Power Distribution</div>', unsafe_allow_html=True)
        fig_h = px.histogram(df, x='power', nbins=30,
                             color_discrete_sequence=['#ff4466'],
                             labels={'power': 'Power (W)', 'count': 'Frequency'})
        fig_h.update_layout(paper_bgcolor='#080c14', plot_bgcolor='#0d1422',
                             font_color='white', height=240,
                             margin=dict(l=8,r=8,t=8,b=8))
        st.plotly_chart(fig_h, use_container_width=True)

        # AI Prediction (linear regression on energy)
        reg_df = df.copy()
        reg_df['energy_kwh'] = pd.to_numeric(reg_df['energy_kwh'], errors='coerce')
        reg_df['timestamp'] = pd.to_datetime(reg_df['timestamp'], errors='coerce')
        reg_df = reg_df.dropna(subset=['energy_kwh', 'timestamp']).reset_index(drop=True)

        if len(reg_df) >= 15:
            st.markdown('<div class="eg-section">AI Energy Prediction (Linear Regression)</div>',
                        unsafe_allow_html=True)
            x = np.arange(len(reg_df), dtype=float)
            y = reg_df['energy_kwh'].to_numpy(dtype=float)
            coeffs = np.polyfit(x, y, 1)

            n_future = 60
            fx = np.arange(len(reg_df), len(reg_df) + n_future, dtype=float)
            fy = np.polyval(coeffs, fx)
            ft = [reg_df['timestamp'].iloc[-1] + timedelta(seconds=i) for i in range(1, n_future+1)]

            fig_pr = go.Figure()
            fig_pr.add_trace(go.Scatter(x=reg_df['timestamp'], y=reg_df['energy_kwh'],
                                        name='Actual', line=dict(color='#00ff99', width=2)))
            fig_pr.add_trace(go.Scatter(x=ft, y=fy,
                                        name='Predicted (60 s)', yaxis='y1',
                                        line=dict(color='#ffd700', width=1.8, dash='dot')))
            fig_pr.update_layout(paper_bgcolor='#080c14', plot_bgcolor='#0d1422',
                                  font_color='white', height=260,
                                  yaxis=dict(title='kWh', gridcolor='#0d1e2e'),
                                  legend=dict(bgcolor='#0d1422'),
                                  margin=dict(l=8,r=8,t=8,b=8))
            st.plotly_chart(fig_pr, use_container_width=True)

            # Extrapolate
            rate_kwh_per_s = coeffs[0]
            daily   = rate_kwh_per_s * 86400
            monthly = daily * 30

            p1,p2,p3,p4 = st.columns(4)
            p1.metric("⏱ Rate",         f"{rate_kwh_per_s*3600:.4f} kWh/hr")
            p2.metric("📅 Daily Est.",   f"{daily:.4f} kWh",   f"₨ {daily*rate:.2f}")
            p3.metric("📅 Monthly Est.", f"{monthly:.3f} kWh", f"₨ {monthly*rate:.2f}")
            p4.metric("🌱 Monthly CO₂",  f"{monthly*carbon:.3f} kg")

        # Data table
        st.markdown('<div class="eg-section">Data Log (last 50 readings)</div>',
                    unsafe_allow_html=True)
        disp = df.tail(50).copy()
        disp['timestamp'] = pd.to_datetime(disp['timestamp'], errors='coerce')
        disp['timestamp'] = disp['timestamp'].dt.strftime('%H:%M:%S').fillna('--:--:--')
        st.dataframe(disp, use_container_width=True, height=260)

        csv_bytes = df.to_csv(index=False).encode()
        st.download_button("⬇️  Download CSV", csv_bytes,
                           f"energyguru_{datetime.now():%Y%m%d_%H%M%S}.csv",
                           "text/csv", use_container_width=True)


# ════════════════════════════════════════════════════════════
# TAB 4 – REPORT GENERATOR
# ════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="eg-section">Report Configuration</div>', unsafe_allow_html=True)

    if "report_pdf_bytes" not in st.session_state:
        st.session_state.report_pdf_bytes = None
    if "report_pdf_filename" not in st.session_state:
        st.session_state.report_pdf_filename = None

    rc1, rc2 = st.columns(2)
    with rc1:
        rpt_title   = st.text_input("Report Title",    "EnergyGuru – Power Calculus Report")
        institution = st.text_input("Institution",     "Smart Energy Lab")
        operator    = st.text_input("Operator",        "")
        project_id  = st.text_input("Project ID",      "ENERGYGURU-2025-001")
    with rc2:
        notes = st.text_area("Notes / Remarks",
                             "Generated by EnergyGuru Power Calculus System.\n"
                             "Arduino-based IoT Energy Monitoring | City Model.")

    generate_btn = st.button("📊  Generate PDF Report", type="primary",
                             use_container_width=True)

    if generate_btn:
        if len(df) < 2:
            st.error("⚠️ Not enough data — collect at least 2 readings first.")
        else:
            try:
                from fpdf import FPDF  # pip install fpdf2

                # ── Compute summary stats ───────────────────
                avg_v   = df['voltage'].mean()
                avg_i   = df['current'].mean()
                avg_p   = df['power'].mean()
                max_p   = df['power'].max()
                min_p   = df['power'].min()
                tot_e   = df['energy_kwh'].iloc[-1]
                tot_b   = df['bill_pkr'].iloc[-1]
                tot_co2 = df['carbon_kg'].iloc[-1]
                n_reads = len(df)
                dur_s   = n_reads   # 1 reading per second
                # Monthly projections from average power trend.
                monthly_energy_est = (avg_p / 1000.0) * 24 * 30
                monthly_cost_est   = monthly_energy_est * rate
                monthly_co2_est    = monthly_energy_est * carbon

                # ── AI Recommendations ──────────────────────
                recs = []
                if avg_p > 500:
                    recs.append("HIGH load detected - consider switching off idle appliances.")
                if avg_v < 210 or avg_v > 235:
                    recs.append("Voltage outside safe range (210-235 V) - check power supply.")
                if df['voltage'].std() > 8:
                    recs.append("High voltage fluctuation - consider a voltage stabiliser.")
                recs.append("Use LED lighting to reduce city model consumption by ~70%.")
                recs.append("Schedule high-load demos during off-peak hours (22:00-06:00).")
                recs.append("Install capacitor banks to improve power factor.")
                recs.append("Regular maintenance reduces standby losses significantly.")

                def pdf_safe(text):
                    if text is None:
                        return ""
                    normalized = str(text).translate(str.maketrans({
                        "–": "-",
                        "—": "-",
                        "•": "|",
                        "°": " deg",
                        "₂": "2",
                        "₨": "Rs",
                        "✓": "[+]",
                        "⚠": "[!]",
                    }))
                    return normalized.encode("latin-1", "replace").decode("latin-1")

                # ── Build PDF ───────────────────────────────
                class EnergyPDF(FPDF):
                    def header(self):
                        # Dark top bar
                        self.set_fill_color(8, 12, 20)
                        self.rect(0, 0, 210, 297, 'F')

                        self.set_fill_color(0, 40, 60)
                        self.rect(0, 0, 210, 22, 'F')

                        self.set_fill_color(0, 200, 255)
                        self.rect(0, 0, 4, 22, 'F')

                        self.set_font('Helvetica', 'B', 14)
                        self.set_text_color(0, 200, 255)
                        self.set_xy(8, 4)
                        self.cell(100, 7, pdf_safe('ENERGYGURU - POWER CALCULUS'), ln=False)

                        self.set_font('Helvetica', '', 7)
                        self.set_text_color(80, 120, 160)
                        self.set_xy(8, 13)
                        self.cell(0, 5, pdf_safe(
                                  f'AI-Assisted Energy Usage Analyzer  |  '
                                  f'Generated: {datetime.now():%Y-%m-%d %H:%M:%S}'))
                        self.ln(14)

                    def footer(self):
                        self.set_y(-14)
                        self.set_font('Helvetica', 'I', 7)
                        self.set_text_color(50, 70, 100)
                        self.cell(0, 8,
                                  pdf_safe(f'EnergyGuru Power Calculus  |  {institution}  |  Page {self.page_no()}'),
                                  align='C')

                    def section_title(self, txt):
                        self.set_fill_color(0, 30, 50)
                        self.set_draw_color(0, 200, 255)
                        self.set_line_width(0.3)
                        self.rect(self.get_x(), self.get_y(), 185, 8, 'DF')
                        self.set_font('Helvetica', 'B', 9)
                        self.set_text_color(0, 200, 255)
                        self.cell(0, 8, pdf_safe(f'  {txt}'), ln=True)
                        self.ln(2)

                    def kv_row(self, label, value, fill_idx):
                        if fill_idx % 2 == 0:
                            self.set_fill_color(13, 20, 34)
                        else:
                            self.set_fill_color(10, 16, 28)
                        self.set_text_color(100, 140, 180)
                        self.set_font('Helvetica', '', 9)
                        self.cell(90, 7, pdf_safe(f'  {label}'), fill=True)
                        self.set_text_color(220, 230, 240)
                        self.set_font('Helvetica', 'B', 9)
                        self.cell(95, 7, pdf_safe(f'  {value}'), fill=True, ln=True)

                pdf = EnergyPDF()
                pdf.set_auto_page_break(auto=True, margin=18)
                pdf.add_page()

                # Title block
                pdf.set_font('Helvetica', 'B', 17)
                pdf.set_text_color(0, 200, 255)
                pdf.cell(0, 10, pdf_safe(rpt_title), ln=True, align='C')
                pdf.ln(1)

                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(80, 120, 160)
                pdf.cell(0, 6, pdf_safe(f'Institution: {institution}    |    Project: {project_id}'), ln=True, align='C')
                pdf.cell(0, 6, pdf_safe(f'Location: {city_choice}   |   Lat {loc["lat"]:.4f} deg  Lon {loc["lon"]:.4f} deg'), ln=True, align='C')
                if operator:
                    pdf.cell(0, 6, pdf_safe(f'Operator: {operator}'), ln=True, align='C')
                pdf.cell(0, 6, pdf_safe(f'Date: {datetime.now():%B %d, %Y}    Time: {datetime.now():%H:%M:%S}'), ln=True, align='C')
                pdf.ln(4)

                # Divider
                pdf.set_draw_color(0, 60, 90)
                pdf.set_line_width(0.4)
                pdf.line(15, pdf.get_y(), 195, pdf.get_y())
                pdf.ln(5)

                # ── Section 1: Measurements ──────────────────
                pdf.section_title('1.  MEASUREMENT SUMMARY')
                rows = [
                    ("Average Voltage",        f"{avg_v:.2f} V"),
                    ("Average Current",         f"{avg_i:.3f} A"),
                    ("Average Power",           f"{avg_p:.2f} W"),
                    ("Peak Power",              f"{max_p:.2f} W"),
                    ("Minimum Power",           f"{min_p:.2f} W"),
                    ("Total Energy Consumed",   f"{tot_e:.6f} kWh"),
                    ("Electricity Bill",        f"PKR {tot_b:.4f}"),
                    ("Carbon Footprint",        f"{tot_co2:.6f} kg CO2"),
                    ("Monthly Energy (Est.)",   f"{monthly_energy_est:.3f} kWh"),
                    ("Monthly Cost (Est.)",     f"PKR {monthly_cost_est:.2f}"),
                    ("Monthly CO2 (Est.)",      f"{monthly_co2_est:.3f} kg"),
                    ("Tariff Rate",             f"PKR {rate:.2f} / kWh"),
                    ("Carbon Factor",           f"{carbon:.2f} kg CO₂ / kWh"),
                    ("Total Readings",          f"{n_reads}"),
                    ("Monitoring Duration",     f"{dur_s} seconds  ({dur_s/60:.1f} min)"),
                ]
                for idx, (lbl, val) in enumerate(rows):
                    pdf.kv_row(lbl, val, idx)
                pdf.ln(5)

                # ── Section 2: Arduino Calculations ─────────
                pdf.section_title('2.  ARDUINO CALCULATIONS')
                pdf.set_fill_color(8, 16, 26)
                pdf.set_font('Courier', '', 8)
                pdf.set_text_color(0, 220, 120)
                calc_lines = [
                    '',
                    f'  // Instantaneous Power',
                    f'  power_W = voltage_V * current_A',
                    f'         = {avg_v:.2f} V  *  {avg_i:.3f} A  =  {avg_p:.2f} W',
                    '',
                    f'  // Energy accumulation (per interval)',
                    f'  energy_kWh += (power_W / 1000.0) * dt_hours',
                    f'  total_energy = {tot_e:.6f} kWh',
                    '',
                    f'  // Electricity Bill',
                    f'  bill_PKR = energy_kWh * tariff',
                    f'          = {tot_e:.6f}  *  {rate:.2f}  =  PKR {tot_b:.4f}',
                    '',
                    f'  // Carbon Footprint',
                    f'  carbon_kg = energy_kWh * carbon_factor',
                    f'           = {tot_e:.6f}  *  {carbon:.2f}  =  {tot_co2:.6f} kg CO2',
                    '',
                    f'  // Apparent Power',
                    f'  S (VA) = {avg_v:.2f} V  *  {avg_i:.3f} A  =  {avg_v*avg_i:.2f} VA',
                    '',
                ]
                for ln_text in calc_lines:
                    pdf.cell(0, 6, ln_text, fill=True, ln=True)
                pdf.ln(4)

                # ── Section 3: Last 20 readings ──────────────
                pdf.section_title('3.  RECENT READINGS  (last 20)')
                hdrs   = ['Time',    'V (V)',  'I (A)',  'P (W)',
                          'kWh',     'Bill Rs', 'CO2 kg']
                c_widths = [26, 22, 22, 25, 32, 30, 28]

                # Table header
                pdf.set_fill_color(0, 40, 60)
                pdf.set_text_color(0, 200, 255)
                pdf.set_font('Helvetica', 'B', 8)
                for h, w in zip(hdrs, c_widths):
                    pdf.cell(w, 7, pdf_safe(h), fill=True, align='C')
                pdf.ln()

                pdf.set_font('Helvetica', '', 8)
                recent = df.tail(20)
                for idx, (_, row) in enumerate(recent.iterrows()):
                    bg = (13, 20, 34) if idx % 2 == 0 else (10, 16, 28)
                    pdf.set_fill_color(*bg)
                    pdf.set_text_color(180, 200, 220)
                    ts = row['timestamp'].strftime('%H:%M:%S') if hasattr(row['timestamp'], 'strftime') else str(row['timestamp'])[:8]
                    vals = [ts,
                            f"{row['voltage']:.1f}",
                            f"{row['current']:.3f}",
                            f"{row['power']:.1f}",
                            f"{row['energy_kwh']:.6f}",
                            f"{row['bill_pkr']:.4f}",
                            f"{row['carbon_kg']:.6f}"]
                    for v, w in zip(vals, c_widths):
                        pdf.cell(w, 6, pdf_safe(v), fill=True, align='C')
                    pdf.ln()
                pdf.ln(4)

                # ── Section 4: AI Recommendations ───────────
                pdf.section_title('4.  AI ENERGY RECOMMENDATIONS')
                pdf.set_font('Helvetica', '', 9)
                for i, rec in enumerate(recs):
                    icon = '[!]' if rec.startswith('HIGH') or rec.startswith('Voltage') or rec.startswith('High') else '[+]'
                    clr = (255, 180, 60) if icon == '[!]' else (100, 220, 130)
                    pdf.set_text_color(*clr)
                    pdf.cell(0, 8, pdf_safe(f'  {icon}  {rec}'), ln=True)
                pdf.ln(3)

                # ── Notes ────────────────────────────────────
                if notes.strip():
                    pdf.set_draw_color(0, 60, 90)
                    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
                    pdf.ln(3)
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_text_color(60, 100, 140)
                    pdf.cell(0, 7, 'NOTES:', ln=True)
                    pdf.set_font('Helvetica', '', 8)
                    pdf.set_text_color(140, 160, 180)
                    for ln_text in notes.split('\n'):
                        pdf.cell(0, 6, pdf_safe(ln_text), ln=True)

                # ── Output ───────────────────────────────────
                pdf_bytes = bytes(pdf.output())
                st.success("✅ Report generated successfully!")
                filename = f"EnergyGuru_Report_{datetime.now():%Y%m%d_%H%M%S}.pdf"
                st.session_state.report_pdf_bytes = pdf_bytes
                st.session_state.report_pdf_filename = filename

                # Quick preview
                st.markdown('<div class="eg-section">Report Preview</div>',
                            unsafe_allow_html=True)
                pc = st.columns(4)
                pc[0].metric("Total Energy",  f"{tot_e:.6f} kWh")
                pc[1].metric("Total Bill",    f"₨ {tot_b:.4f}")
                pc[2].metric("CO₂",           f"{tot_co2:.6f} kg")
                pc[3].metric("Peak Power",    f"{max_p:.1f} W")
                pm = st.columns(3)
                pm[0].metric("Monthly Energy (Est.)", f"{monthly_energy_est:.3f} kWh")
                pm[1].metric("Monthly Cost (Est.)",   f"₨ {monthly_cost_est:.2f}")
                pm[2].metric("Monthly CO₂ (Est.)",    f"{monthly_co2_est:.3f} kg")

            except ImportError:
                st.error("⚠️ `fpdf2` is not installed.  Run:  **pip install fpdf2**")
            except Exception as ex:
                st.error(f"Error: {ex}")
                st.exception(ex)

    if st.session_state.report_pdf_bytes:
        st.download_button(
            "⬇️  Download PDF Report",
            data=st.session_state.report_pdf_bytes,
            file_name=st.session_state.report_pdf_filename,
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

render_footer()

# ── Auto refresh (live updates) ──────────────────────────────
if st.session_state.demo_mode or st.session_state.connected:
    time.sleep(1)
    st.rerun()
