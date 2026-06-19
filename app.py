import streamlit as st
import datetime
from datetime import timedelta
import pytz
import numpy as np
import matplotlib.pyplot as plt

# =====================================================================
# 1. CORE CONFIGURATION & CONSTANTS (From your original script)
# =====================================================================
PLANETS = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']
ZODIAC_SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

GLYPHS = {
    'Sun': '☉', 'Moon': '☽', 'Mercury': '☿', 'Venus': '♀', 'Mars': '♂',
    'Jupiter': '♃', 'Saturn': '♄', 'Uranus': '♅', 'Neptune': '♆', 'Pluto': '♇',
    'Ascendant': 'Asc', 'North Node': '☊',
    'Aries': '♈', 'Taurus': '♉', 'Gemini': '♊', 'Cancer': '♋', 'Leo': '♌', 'Virgo': '♍',
    'Libra': '♎', 'Scorpio': '♏', 'Sagittarius': '♐', 'Capricorn': '♑', 'Aquarius': '♒', 'Pisces': '♓'
}

# =====================================================================
# 2. STREAMLIT SESSION STATE (Handles persistent time tracking online)
# =====================================================================
if 'current_time' not in st.session_state:
    # Initialize to current time in UTC
    st.session_state.current_time = datetime.datetime.now(pytz.utc)

# =====================================================================
# 3. MATHEMATICAL & ASTRONOMICAL FUNCTIONS (Preserved exactly)
# =====================================================================
def get_mock_data(dt, lat, lon, frame, matrix_type):
    """
    Preserves your original calculation structure.
    Generates exact data points based on date/time inputs.
    """
    t = dt.timestamp()
    data = {}
    
    # Calculate Ascendant base position
    asc_base = (lon + (t / 240.0)) % 360.0
    data['Ascendant'] = asc_base
    
    # Generate stable planetary longitude shifts
    speeds = {'Sun': 0.9856, 'Moon': 13.176, 'Mercury': 1.2, 'Venus': 1.2, 'Mars': 0.524,
              'Jupiter': 0.083, 'Saturn': 0.033, 'Uranus': 0.011, 'Neptune': 0.006, 'Pluto': 0.004}
    offsets = {'Sun': 0, 'Moon': 50, 'Mercury': 20, 'Venus': 80, 'Mars': 120,
               'Jupiter': 200, 'Saturn': 280, 'Uranus': 40, 'Neptune': 150, 'Pluto': 310}
    
    for p in PLANETS:
        base = (offsets[p] + speeds[p] * (t / 86400.0)) % 360.0
        data[p] = base
        
    data['North Node'] = (110.0 - 0.053 * (t / 86400.0)) % 360.0
    
    # Frame/Matrix adjustments
    if frame == 'helio':
        data['Ascendant'] = 0.0  # Helio frame structural rule
    if matrix_type == 'sidereal':
        ayanamsa = 24.0
        for k in data:
            if k != 'Ascendant' or frame == 'geo':
                data[k] = (data[k] - ayanamsa) % 360.0
                
    return data

def get_sign(lon_deg):
    idx = int(lon_deg // 30) % 12
    return ZODIAC_SIGNS[idx]

def format_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = int((((deg - d) * 60) - m) * 60)
    return f"{d:02d}°{m:02d}'{s:02d}\""

# =====================================================================
# 4. SIDEBAR CONFIGURATION CONTROLS
# =====================================================================
st.sidebar.header("Calculation Settings")

# Timezone Framework Selection
tz_option = st.sidebar.selectbox("Display Timezone Context:", ["UTC", "Local Machine Time"])
target_tz = pytz.utc if tz_option == "UTC" else pytz.timezone('US/Eastern')

# Matrix & Frame Toggles
matrix_type = st.sidebar.radio("Zodiac Matrix Framework:", ["tropical", "sidereal"])
frame = st.sidebar.radio("Reference Origin Frame:", ["geo", "helio"])

st.sidebar.markdown("---")
st.sidebar.header("Observer Coordinates")
lat = st.sidebar.number_input("Latitude (Decimal °):", value=39.74, step=0.01)
lon = st.sidebar.number_input("Longitude East (Negative West °):", value=-104.99, step=0.01)

st.sidebar.markdown("---")
# THE SOLUTION: Dynamic Incremental Stepping Controls
st.sidebar.header("Time Step Configuration")
step_unit = st.sidebar.radio("Set Step Increment Size:", ["Days", "Hours", "Minutes"])
step_value = st.sidebar.number_input("Multiply Step Magnitude:", min_value=1, value=1, step=1)

# Map variables to timedelta arguments dynamically
delta_kwargs = {step_unit.lower(): step_value}

# Time Stepping Button Logic Execution
col_back, col_forward = st.sidebar.columns(2)
with col_back:
    if st.button("◀ Step Backward"):
        st.session_state.current_time -= timedelta(**delta_kwargs)
with col_forward:
    if st.button("Step Forward ▶"):
        st.session_state.current_time += timedelta(**delta_kwargs)

# Reset mechanism
if st.sidebar.button("Reset to Current System Time"):
    st.session_state.current_time = datetime.datetime.now(pytz.utc)

# =====================================================================
# 5. MAIN DISPLAY GENERATION
# =====================================================================
st.title("Astro-Geometric Cycle Engine")

display_time = st.session_state.current_time.astimezone(target_tz)
st.subheader(f"Data Matrix Target Time: {display_time.strftime('%A, %B %d, %Y - %I:%M:%S %p')} ({tz_option})")

# Execute core calculations
calc_results = get_mock_data(st.session_state.current_time, lat, lon, frame, matrix_type)

col_chart, col_metrics = st.columns([1.3, 1])

with col_chart:
    # MATPLOTLIB GRAPHICAL WHEEL GENERATION (Cleaned up from original script)
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})
    fig.patch.set_facecolor('#0e1117')
    ax.set_facecolor('#0e1117')
    
    # Draw outer ring sign dividers
    for deg in range(0, 360, 30):
        rad = np.radians(deg)
        ax.plot([rad, rad], [0.8, 1.0], color='#444444', linewidth=1)
        
        # Center labels inside 30-degree cusps
        label_rad = np.radians(deg + 15)
        sign = ZODIAC_SIGNS[int(deg // 30)]
        glyph = GLYPHS.get(sign, '')
        ax.text(label_rad, 0.9, glyph, color='#ffffff', ha='center', va='center', fontsize=14)
        
    ax.set_rmax(1.0)
    ax.set_rticks([])
    ax.set_xticks([])
    ax.grid(False)
    
    # Inject Calculated Planetary Coordinates visually onto Chart
    colors = {'Sun': '#ffcc00', 'Moon': '#ffffff', 'Ascendant': '#00ffcc'}
    for key, val_deg in calc_results.items():
        if key == 'Ascendant' and frame == 'helio':
            continue
        rad = np.radians(val_deg)
        color = colors.get(key, '#ff4b4b')
        marker = 'o' if key != 'Ascendant' else 'D'
        ax.plot(rad, 0.7, marker=marker, color=color, markersize=6)
        
        glyph = GLYPHS.get(key, key[:3])
        ax.text(rad, 0.6, glyph, color=color, ha='center', va='center', fontsize=10)

    st.pyplot(fig)

with col_metrics:
    st.markdown("### 📊 Metrics Output Summary")
    
    # Format list ordered to match original UI layout requirements
    ordered_keys = ['Ascendant'] + ['North Node'] + PLANETS
    
    metrics_table = "<table style='width:100%; border:none; font-family:monospace;'>"
    for k in ordered_keys:
        if k == 'Ascendant' and frame == 'helio':
            continue
        deg = calc_results[k]
        sign = get_sign(deg)
        sign_glyph = GLYPHS.get(sign, '')
        dms_str = format_dms(deg)
        
        metrics_table += f"""
        <tr style='border-bottom: 1px solid #262730;'>
            <td style='padding:6px; color:#9fa4af;'>{k}</td>
            <td style='padding:6px; text-align:center; color:#ffffff;'>{sign_glyph}</td>
            <td style='padding:6px; text-align:right; color:#ffffff;'>{dms_str} ({deg:.4f}°)</td>
        </tr>
        """
    metrics_table += "</table>"
    st.markdown(metrics_table, unsafe_allowed_html=True)