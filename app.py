#!/usr/bin/env python3
"""
Planet Viewer — Streamlit Edition
Converted from the original Tkinter desktop application to a responsive web application.
Preserves all core Skyfield calculations, Sidereal/Tropical modes, and custom aspect/glyph rendering.
"""

import math
import os
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from datetime import datetime, timedelta, timezone

# Use standard font system for rendering glyphs in matplotlib
plt.rcParams['font.family'] = 'sans-serif'

try:
    from zoneinfo import ZoneInfo
except Exception:
    st.error("This app requires Python 3.9+ for native timezone support via zoneinfo.")
    st.stop()

try:
    from skyfield.api import load
    from skyfield.framelib import ecliptic_frame
except ImportError:
    st.error("Missing required libraries. Please ensure 'skyfield' and 'jplephem' are listed in your requirements.txt file.")
    st.stop()

# ---------------------- Configuration & Constants ----------------------
ZODIAC_SIGNS = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]
PLANETS = [
    ("Sun", "sun"),
    ("Moon", "moon"),
    ("Mercury", "mercury"),
    ("Venus", "venus"),
    ("Mars", "mars"),
    ("Jupiter", "jupiter barycenter"),
    ("Saturn", "saturn barycenter"),
    ("Uranus", "uranus barycenter"),
    ("Neptune", "neptune barycenter"),
    ("Pluto", "pluto barycenter"),
]
BODY_ALIASES = {
    "sun": ["sun"], "moon": ["moon"], "mercury": ["mercury", "mercury barycenter"],
    "venus": ["venus", "venus barycenter"], "mars": ["mars", "mars barycenter"],
    "jupiter": ["jupiter", "jupiter barycenter"], "jupiter barycenter": ["jupiter barycenter", "jupiter"],
    "saturn": ["saturn", "saturn barycenter"], "saturn barycenter": ["saturn barycenter", "saturn"],
    "uranus": ["uranus", "uranus barycenter"], "uranus barycenter": ["uranus barycenter", "uranus"],
    "neptune": ["neptune", "neptune barycenter"], "neptune barycenter": ["neptune barycenter", "neptune"],
    "pluto": ["pluto", "pluto barycenter"], "pluto barycenter": ["pluto barycenter", "pluto"],
    "earth": ["earth"], "earth barycenter": ["earth barycenter"],
}
PLANET_GLYPHS = {
    "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
    "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅", "Neptune": "♆", "Pluto": "♇",
    "Asc": "Asc", "North Node": "☊", "South Node": "☋"
}
ASPECTS = [
    ("Sextile", 60.0, "#00BCD4"),
    ("Square", 90.0, "#FF5252"),
    ("Trine", 120.0, "#4CAF50"),
    ("Opposition", 180.0, "#FFB300"),
]
ASPECT_ORB_DEG = 3.0

AYANAMSA_CHOICES = {
    "Lahiri": {"t0": 2435553.5, "ayan_t0": 23.250182778 - 0.004658035},
    "Fagan/Bradley": {"t0": 2433282.42346, "ayan_t0": 24.042044444},
    "Krishnamurti": {"t0": 2415020.0, "ayan_t0": 360.0 - 337.636111},
    "Raman": {"t0": 2415020.0, "ayan_t0": 360.0 - 338.98556},
    "De Luce": {"t0": 1721057.5, "ayan_t0": 0.0},
}

# Streamlit App Styling Adjustments
st.set_page_config(page_title="Planet Viewer & Zodiac Chart", layout="wide")
st.markdown(
    """
    <style>
    .reportview-container { background: #000000; color: #ffffff; }
    .sidebar .sidebar-content { background: #111111; }
    div.stButton > button:first-child { background-color: #00C853; color: white; border-radius:5px; }
    </style>
    """, 
    unsafe_allow_html=True
)

# ---------------------- Ephemeris & Astronomical Helpers ----------------------
@st.cache_resource
def _load_ephemeris():
    ts = load.timescale()
    eph = load('de421.bsp')
    return ts, eph

def to_utc(dt_local: datetime) -> datetime:
    return dt_local.astimezone(timezone.utc)

def dt_to_julday_utc(dt_utc: datetime) -> float:
    y, m, d = dt_utc.year, dt_utc.month, dt_utc.day
    hour = dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600 + dt_utc.microsecond / 3_600_000_000
    a = (14 - m) // 12
    y2 = y + 4800 - a
    m2 = m + 12 * a - 3
    jdn = d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - y2 // 100 + y2 // 400 - 32045
    return jdn + (hour - 12.0) / 24.0

def wrap360(angle: float) -> float:
    return angle % 360.0

def format_lon_deg(angle: float) -> str:
    angle %= 360.0
    sign = int(angle // 30)
    in_sign = angle % 30.0
    deg = int(in_sign)
    minutes_full = (in_sign - deg) * 60
    minu = int(minutes_full)
    sec = int(round((minutes_full - minu) * 60))
    if sec == 60: sec = 0; minu += 1
    if minu == 60: minu = 0; deg += 1
    if deg == 30: deg = 0; sign = (sign + 1) % 12
    return f"{ZODIAC_SIGNS[sign]} {deg:02d}°{minu:02d}′{sec:02d}″ ({angle:07.4f}°)"

def format_signed_deg(angle: float, suffix_pos: str = "", suffix_neg: str = "") -> str:
    a = abs(angle)
    deg = int(a)
    minutes_full = (a - deg) * 60
    minu = int(minutes_full)
    sec = int(round((minutes_full - minu) * 60))
    if sec == 60: sec = 0; minu += 1
    if minu == 60: minu = 0; deg += 1
    suf = f" {suffix_pos if angle >= 0 else suffix_neg}" if (suffix_pos and suffix_neg) else ""
    return f"{'+' if angle >= 0 else '-'}{deg:02d}°{minu:02d}′{sec:02d}″ ({angle:+.4f}°){suf}"

def format_hours_hms(hours: float) -> str:
    hours %= 24.0
    h = int(hours)
    minutes_full = (hours - h) * 60
    m = int(minutes_full)
    s = int(round((minutes_full - m) * 60))
    if s == 60: s = 0; m += 1
    if m == 60: m = 0; h = (h + 1) % 24
    return f"{h:02d}h {m:02d}m {s:02d}s ({hours:06.3f}h)"

def mean_obliquity_deg(jd_ut: float) -> float:
    T = (jd_ut - 2451545.0) / 36525.0
    seconds = 84381.448 - 46.8150 * T - 0.00059 * (T ** 2) + 0.001813 * (T ** 3)
    return seconds / 3600.0

def precession_arcsec_from_j2000(jd_ut: float) -> float:
    T = (jd_ut - 2451545.0) / 36525.0
    return 5029.0966 * T + 1.11113 * (T ** 2) - 0.000006 * (T ** 3)

def ayanamsa_deg(name: str, jd_ut: float) -> float:
    item = AYANAMSA_CHOICES.get(name, AYANAMSA_CHOICES["Lahiri"])
    delta_arcsec = precession_arcsec_from_j2000(jd_ut) - precession_arcsec_from_j2000(item["t0"])
    return wrap360(item["ayan_t0"] + delta_arcsec / 3600.0)

def calc_ascendant_tropical(jd_ut: float, lat_deg: float, lon_deg_east: float, t) -> float:
    phi = math.radians(lat_deg)
    eps = math.radians(mean_obliquity_deg(jd_ut))
    theta_local_deg = (float(t.gmst) * 15.0 + lon_deg_east) % 360.0
    theta = math.radians(theta_local_deg)
    y = -math.cos(theta)
    x = math.sin(theta) * math.cos(eps) + math.tan(phi) * math.sin(eps)
    lam = math.degrees(math.atan2(y, x)) % 360.0
    if lam < 180.0: lam += 180.0
    else: lam -= 180.0
    return lam % 360.0

def _resolve_body(eph, body_key: str):
    for key in BODY_ALIASES.get(body_key, [body_key]):
        try: return eph[key]
        except Exception: continue
    raise KeyError(f"Body not found in ephemeris: {body_key}")

def _position_xyz_au(t, body_key: str, eph):
    if body_key == "moon":
        earth_xyz = _resolve_body(eph, "earth").at(t).position.au
        moon_geo_xyz = _resolve_body(eph, "moon").at(t).position.au
        return tuple(float(earth_xyz[i]) + float(moon_geo_xyz[i]) for i in range(3))
    xyz = _resolve_body(eph, body_key).at(t).position.au
    return tuple(float(xyz[i]) for i in range(3))

def _heliocentric_xyz_au(t, body_key: str, eph):
    if body_key == "sun": return (0.0, 0.0, 0.0)
    body_xyz = _position_xyz_au(t, body_key, eph)
    sun_xyz = _position_xyz_au(t, "sun", eph)
    return tuple(body_xyz[i] - sun_xyz[i] for i in range(3))

def _equatorial_from_xyz(x: float, y: float, z: float):
    dist = math.sqrt(x * x + y * y + z * z)
    ra_deg = wrap360(math.degrees(math.atan2(y, x))) if dist else 0.0
    dec_deg = math.degrees(math.atan2(z, math.sqrt(x * x + y * y))) if dist else 0.0
    return ra_deg, dec_deg, dist

def _ecliptic_from_xyz(x: float, y: float, z: float, jd_ut: float):
    eps = math.radians(mean_obliquity_deg(jd_ut))
    x_ecl = x
    y_ecl = y * math.cos(eps) + z * math.sin(eps)
    z_ecl = -y * math.sin(eps) + z * math.cos(eps)
    dist = math.sqrt(x_ecl * x_ecl + y_ecl * y_ecl + z_ecl * z_ecl)
    lon = wrap360(math.degrees(math.atan2(y_ecl, x_ecl))) if dist else 0.0
    lat = math.degrees(math.atan2(z_ecl, math.sqrt(x_ecl * x_ecl + y_ecl * y_ecl))) if dist else 0.0
    return lon, lat, dist

def calc_ecliptic_sf(t, jd_ut, eph, body_key: str, center_mode: str, zodiac_mode: str, ayanamsa_name: str):
    if center_mode == "helio":
        x, y, z = _heliocentric_xyz_au(t, body_key, eph)
        lon, lat, dist = _ecliptic_from_xyz(x, y, z, jd_ut)
    else:
        earth = _resolve_body(eph, "earth")
        vec = earth.at(t).observe(_resolve_body(eph, body_key)).apparent()
        lat_a, lon_a, dist_a = vec.frame_latlon(ecliptic_frame)
        lon = wrap360(float(lon_a.degrees))
        lat = float(lat_a.degrees)
        dist = float(getattr(dist_a, "au", 0.0))
    if zodiac_mode == "sidereal":
        lon = wrap360(lon - ayanamsa_deg(ayanamsa_name, jd_ut))
    return lon, lat, dist

def calc_equatorial_sf(t, eph, body_key: str, center_mode: str):
    if center_mode == "helio":
        x, y, z = _heliocentric_xyz_au(t, body_key, eph)
        ra_deg, dec_deg, dist = _equatorial_from_xyz(x, y, z)
        return ra_deg, dec_deg, dist
    earth = _resolve_body(eph, "earth")
    vec = earth.at(t).observe(_resolve_body(eph, body_key)).apparent()
    ra_a, dec_a, dist_a = vec.radec()
    ra_deg = wrap360(float(ra_a.hours) * 15.0)
    dec_deg = float(dec_a.degrees)
    dist = float(getattr(dist_a, "au", 0.0))
    return ra_deg, dec_deg, dist

def calc_north_node_lon(t, jd_ut, eph, zodiac_mode: str, ayanamsa_name: str) -> float:
    moon_vec = eph["earth"].at(t).observe(eph["moon"]).apparent()
    pos = moon_vec.frame_xyz(ecliptic_frame)
    r = pos.au
    t_epsilon = t.ts.from_datetime(t.utc_datetime() + timedelta(minutes=10))
    moon_vec2 = eph["earth"].at(t_epsilon).observe(eph["moon"]).apparent()
    pos2 = moon_vec2.frame_xyz(ecliptic_frame)
    r2 = pos2.au
    v = [(r2[i] - r[i]) / (10.0 / (24.0 * 60.0)) for i in range(3)]
    hx = r[1] * v[2] - r[2] * v[1]
    hy = r[2] * v[0] - r[0] * v[2]
    nx, ny = -hy, hx
    lon = math.degrees(math.atan2(ny, nx)) % 360.0
    if zodiac_mode == "sidereal":
        lon = wrap360(lon - ayanamsa_deg(ayanamsa_name, jd_ut))
    return lon

# ---------------------- Glyph Layout & Separation Engine ----------------------
def layout_glyphs_on_ring(plot_positions, label_r, pad_deg=6.0):
    if not plot_positions: return []
    items = []
    for name, lon in plot_positions:
        items.append({"name": name, "lon": lon % 360.0, "text": PLANET_GLYPHS.get(name, name[:2]), "disp_lon": lon % 360.0})
    
    if len(items) <= 1: return items
    items.sort(key=lambda d: d["lon"])
    n = len(items)
    
    for _ in range(5):
        for i in range(n):
            j = (i + 1) % n
            diff = (items[j]["disp_lon"] - items[i]["disp_lon"]) % 360.0
            if diff < pad_deg:
                overlap = pad_deg - diff
                items[i]["disp_lon"] = (items[i]["disp_lon"] - overlap / 2.0) % 360.0
                items[j]["disp_lon"] = (items[j]["disp_lon"] + overlap / 2.0) % 360.0
    return items

def get_aspect_pairs(positions):
    # CHANGED: Removed "North Node" and "South Node" from the exclusions below
    clean = [(name, lon % 360.0) for name, lon in positions if name not in ["Asc"]]
    pairs = []
    for i in range(len(clean)):
        name1, lon1 = clean[i]
        for j in range(i + 1, len(clean)):
            name2, lon2 = clean[j]
            sep = abs((lon2 - lon1 + 180.0) % 360.0 - 180.0)
            for aspect_name, aspect_deg, color in ASPECTS:
                if abs(sep - aspect_deg) <= ASPECT_ORB_DEG:
                    pairs.append((lon1, lon2, color))
                    break
    return pairs

# ---------------------- Streamlit Sidebar UI Inputs ----------------------
st.sidebar.header("⚙️ Calculation Settings")

# Time Management State System
if 'base_date' not in st.session_state:
    st.session_state.base_date = datetime.now()

col1, col2 = st.sidebar.columns(2)

if col1.button("⟨ Step Back"):
    st.session_state.base_date -= timedelta(days=1)
if col2.button("Step Forward ⟩"):
    st.session_state.base_date += timedelta(days=1)
if st.sidebar.button("🎯 Reset to Now"):
    st.session_state.base_date = datetime.now()

tz_choice = st.sidebar.selectbox("Timezone Target", ["UTC", "America/Chicago", "America/New_York", "America/Denver", "America/Los_Angeles", "Europe/London"])
zodiac_mode = st.sidebar.radio("Zodiac Matrix", ["tropical", "sidereal"], horizontal=True)

ayanamsa_name = "Lahiri"
if zodiac_mode == "sidereal":
    ayanamsa_name = st.sidebar.selectbox("Ayanamsa Standard", list(AYANAMSA_CHOICES.keys()))

center_mode = st.sidebar.radio("Reference Origin Frame", ["geo", "helio"], horizontal=True)
quantity_mode = st.sidebar.selectbox("Displayed Value Matrix", ["lon", "lat", "dec", "ra"])

st.sidebar.markdown("---")
st.sidebar.header("📍 Observer Location (Geocentric Only)")
lat_val = st.sidebar.number_input("Latitude (Decimal °)", value=39.7392, step=0.01)
lon_val = st.sidebar.number_input("Longitude East (Negative for West °)", value=-104.9903, step=0.01)

# Processing Selected Target Time
target_tz = ZoneInfo(tz_choice)
localized_time = st.session_state.base_date.astimezone(target_tz)

# ---------------------- Data Computation Pipeline ----------------------
ts, eph = _load_ephemeris()
dt_utc = to_utc(localized_time)
jd_ut = dt_to_julday_utc(dt_utc)
t = ts.from_datetime(dt_utc)

asc_disp = None
if center_mode == "geo":
    asc_trop = calc_ascendant_tropical(jd_ut, lat_val, lon_val, t)
    asc_disp = wrap360(asc_trop - ayanamsa_deg(ayanamsa_name, jd_ut)) if zodiac_mode == "sidereal" else asc_trop

wheel_positions = []
text_report = []

if center_mode == "geo" and asc_disp is not None:
    text_report.append(f"{'Ascendant':<12} : {format_lon_deg(asc_disp)}")

if center_mode == "geo":
    n_node = calc_north_node_lon(t, jd_ut, eph, zodiac_mode, ayanamsa_name)
    s_node = wrap360(n_node + 180.0)
    
    wheel_positions.append(("North Node", n_node))
    wheel_positions.append(("South Node", s_node))
    
    text_report.append(f"{'North Node':<12} : {format_lon_deg(n_node)}")
    text_report.append(f"{'South Node':<12} : {format_lon_deg(s_node)}")

for name, body_key in PLANETS:
    try:
        if quantity_mode == "dec":
            _, dec, _ = calc_equatorial_sf(t, eph, body_key, center_mode)
            disp_str = format_signed_deg(dec, "N", "S")
        elif quantity_mode == "ra":
            ra, _, _ = calc_equatorial_sf(t, eph, body_key, center_mode)
            disp_str = format_hours_hms(ra / 15.0)
        else:
            lon, lat, _ = calc_ecliptic_sf(t, jd_ut, eph, body_key, center_mode, zodiac_mode, ayanamsa_name)
            disp_str = format_lon_deg(lon) if quantity_mode == "lon" else format_signed_deg(lat)
        
        w_lon, _, _ = calc_ecliptic_sf(t, jd_ut, eph, body_key, center_mode, zodiac_mode, ayanamsa_name)
        wheel_positions.append((name, w_lon))
        text_report.append(f"{name:<12} : {disp_str}")
    except Exception as e:
        text_report.append(f"{name:<12} : Execution Error ({str(e)})")

if center_mode == "geo" and asc_disp is not None:
    wheel_positions.append(("Asc", asc_disp))

# ---------------------- Visual Output Grid Construction ----------------------
st.title("🌌 Astro-Geometric Cycle Engine")
st.subheader(f"Data Matrix Target Time: {localized_time.strftime('%A, %B %d, %Y - %I:%M:%S %p')} ({tz_choice})")

view_col, report_col = st.columns([3, 2])

with view_col:
    fig, ax = plt.subplots(figsize=(8, 8), facecolor='black')
    ax.set_facecolor('black')
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.axis('off')

    outer_circle = plt.Circle((0, 0), 1.0, color='#333333', fill=False, linewidth=2)
    inner_circle = plt.Circle((0, 0), 0.8, color='#333333', fill=False, linewidth=1.5)
    hub_circle = plt.Circle((0, 0), 0.25, color='#222222', fill=False, linewidth=1)
    ax.add_artist(outer_circle)
    ax.add_artist(inner_circle)
    ax.add_artist(hub_circle)

    for deg in range(0, 360, 30):
        rad = math.radians(180.0 + deg)
        ax.plot([0.8 * math.cos(rad), 1.0 * math.cos(rad)], [0.8 * math.sin(rad), 1.0 * math.sin(rad)], color='#333333', linewidth=1.5)

    for i, sign in enumerate(ZODIAC_SIGNS):
        mid_deg = i * 30.0 + 15.0
        rad = math.radians(180.0 + mid_deg)
        ax.text(0.9 * math.cos(rad), 0.9 * math.sin(rad), sign, color='#ffffff', fontsize=16, ha='center', va='center')

    aspect_lines = get_aspect_pairs(wheel_positions)
    for lon1, lon2, color in aspect_lines:
        r1, r2 = math.radians(180.0 + lon1), math.radians(180.0 + lon2)
        ax.plot([0.75 * math.cos(r1), 0.75 * math.cos(r2)], [0.75 * math.sin(r1), 0.75 * math.sin(r2)], color=color, linewidth=1.5, alpha=0.8)

    separated_glyphs = layout_glyphs_on_ring(wheel_positions, label_r=0.6)
    for glyph in separated_glyphs:
        t_rad = math.radians(180.0 + glyph["lon"])
        d_rad = math.radians(180.0 + glyph["disp_lon"])
        
        if glyph["name"] == "Asc":
            p_color = '#00C853'
        elif glyph["name"] in ["North Node", "South Node"]:
            p_color = '#FFB300'
        else:
            p_color = '#ffffff'
            
        ax.plot(0.79 * math.cos(t_rad), 0.79 * math.sin(t_rad), marker='o', color=p_color, markersize=4)
        ax.plot([0.78 * math.cos(t_rad), 0.62 * math.cos(d_rad)], [0.78 * math.sin(t_rad), 0.62 * math.sin(d_rad)], color='#444444', linewidth=0.5)
        ax.text(0.58 * math.cos(d_rad), 0.58 * math.sin(d_rad), glyph["text"], color=p_color, fontsize=14, ha='center', va='center')

    ax.text(0, -0.05, f"{zodiac_mode.upper()}", color='#666666', fontsize=9, ha='center', va='center', fontweight='bold')
    st.pyplot(fig)

with report_col:
    st.markdown("### 📊 Metrics Output Summary")
    st.code("\n".join(text_report), language="text")
    
    st.markdown("---")
    st.markdown("### 🟢 Aspect Color Legend")
    for name, deg, color in ASPECTS:
        st.markdown(f"<span style='color:{color}; font-size:20px;'>■</span> **{name}** ({int(deg)}° System / Orb ±3°)", unsafe_allow_html=True)
    
    st.markdown("---")
    st.info(f"**Julian Day:** `{jd_ut:.5f}`  \n**UTC System Clock Time:** `{dt_utc.strftime('%Y-%m-%d %H:%M:%S')}`")