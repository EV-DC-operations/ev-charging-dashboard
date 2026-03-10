import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
from supabase import create_client
import time
import io

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="EV Charging Stations Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# TIMEZONE - เวลาไทย
# ==========================================
def get_thai_time():
    """Get current time in Thailand timezone (UTC+7)"""
    utc_now = datetime.now(timezone.utc)
    thai_time = utc_now + timedelta(hours=7)
    return thai_time.strftime('%Y-%m-%d %H:%M')

def get_thai_date():
    """Get current date in Thailand timezone"""
    utc_now = datetime.now(timezone.utc)
    thai_time = utc_now + timedelta(hours=7)
    return thai_time.date()

# ==========================================
# SUPABASE CONNECTION
# ==========================================
@st.cache_resource
def get_supabase_client():
    """Create Supabase client"""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Cannot connect to Supabase: {e}")
        return None

supabase = get_supabase_client()

# ==========================================
# DATA FUNCTIONS
# ==========================================
def load_stations():
    """Load stations from Supabase"""
    try:
        if supabase:
            response = supabase.table("stations").select("*").execute()
            if response.data:
                return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f"Error loading stations: {e}")
    return pd.DataFrame()

def load_pm_schedule():
    """Load PM schedule from Supabase"""
    try:
        if supabase:
            response = supabase.table("pm_schedule").select("*").execute()
            if response.data:
                return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f"Error loading PM schedule: {e}")
    return pd.DataFrame()

def load_incidents():
    """Load incidents from Supabase"""
    try:
        if supabase:
            response = supabase.table("incidents").select("*").execute()
            if response.data:
                return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f"Error loading incidents: {e}")
    return pd.DataFrame()

def load_spare_parts():
    """Load spare parts from Supabase"""
    try:
        if supabase:
            response = supabase.table("spare_parts").select("*").execute()
            if response.data:
                return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f"Error loading spare parts: {e}")
    return pd.DataFrame()

def load_flood_weather():
    """Load flood weather from Supabase"""
    try:
        if supabase:
            response = supabase.table("flood_weather").select("*").execute()
            if response.data:
                return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f"Error loading flood data: {e}")
    return pd.DataFrame()

def load_charger_units():
    """Load charger units from Supabase"""
    try:
        if supabase:
            response = supabase.table("charger_units").select("*").execute()
            if response.data:
                return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f"Error loading charger units: {e}")
    return pd.DataFrame()

# ==========================================
# WEATHER API - Open-Meteo (ฝนจริง + พยากรณ์)
# ==========================================
def get_historical_rain(lat, lon, days=3):
    """
    ดึงข้อมูลฝนจริงย้อนหลัง (Historical) จาก Open-Meteo
    - แม่นยำ 100% เพราะเป็นข้อมูลจริงที่ตกไปแล้ว
    """
    try:
        today = get_thai_date()
        start_date = (today - timedelta(days=days)).isoformat()
        end_date = (today - timedelta(days=1)).isoformat()  # เมื่อวาน
        
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&daily=precipitation_sum&timezone=Asia/Bangkok"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            rain_data = data.get('daily', {}).get('precipitation_sum', [])
            # กรอง None values
            rain_data = [r if r is not None else 0 for r in rain_data]
            return rain_data
    except Exception as e:
        pass
    return [0] * days

def get_forecast_rain(lat, lon, days=3):
    """
    ดึงข้อมูลพยากรณ์ฝน (Forecast) จาก Open-Meteo
    - ความแม่นยำ ~70-80%
    """
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum&timezone=Asia/Bangkok&forecast_days={days}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            rain_data = data.get('daily', {}).get('precipitation_sum', [])
            # กรอง None values
            rain_data = [r if r is not None else 0 for r in rain_data]
            return rain_data
    except:
        pass
    return [0] * days

def get_combined_rain_data(lat, lon):
    """
    รวมข้อมูลฝนจริง 3 วัน + พยากรณ์ 4 วัน
    Returns: (past_3d, forecast_3d, all_7_days)
    """
    # ฝนจริงย้อนหลัง 3 วัน
    past_rain = get_historical_rain(lat, lon, days=3)
    
    # พยากรณ์ 4 วัน (วันนี้ + อีก 3 วัน)
    forecast_rain = get_forecast_rain(lat, lon, days=4)
    
    # รวม 7 วัน: [past_3, past_2, past_1, today, future_1, future_2, future_3]
    all_7_days = past_rain + forecast_rain[:4] if len(forecast_rain) >= 4 else past_rain + forecast_rain
    
    # Ensure 7 days
    while len(all_7_days) < 7:
        all_7_days.append(0)
    
    past_3d_total = sum(past_rain[:3]) if past_rain else 0
    forecast_3d_total = sum(forecast_rain[:3]) if forecast_rain else 0
    
    return past_3d_total, forecast_3d_total, all_7_days[:7]

# ==========================================
# NEW FORMULA v3.3 - ผสมฝนจริง + พยากรณ์
# ==========================================
def calculate_rain_score_v33(past_3d, forecast_3d):
    """
    สูตร v3.3: ผสมฝนจริง (60%) + พยากรณ์ (40%)
    
    - ฝนจริง = เชื่อถือได้ 100% → น้ำหนักมาก
    - พยากรณ์ = อาจผิดพลาด → น้ำหนักน้อย
    
    Combined Rain = (Past × 0.6) + (Forecast × 0.4)
    
    จากนั้นแปลงเป็นคะแนน:
    - 0-10mm = 0-15 คะแนน
    - 10-30mm = 15-35 คะแนน
    - 30-60mm = 35-55 คะแนน
    - 60-100mm = 55-75 คะแนน
    - 100mm+ = 75-90 คะแนน
    """
    # คำนวณ Combined Rain
    combined_rain = (past_3d * 0.6) + (forecast_3d * 0.4)
    
    # แปลงเป็นคะแนน
    if combined_rain <= 0:
        return 0
    elif combined_rain <= 10:
        return combined_rain * 1.5  # 0-15
    elif combined_rain <= 30:
        return 15 + (combined_rain - 10) * 1.0  # 15-35
    elif combined_rain <= 60:
        return 35 + (combined_rain - 30) * 0.67  # 35-55
    elif combined_rain <= 100:
        return 55 + (combined_rain - 60) * 0.5  # 55-75
    else:
        return min(75 + (combined_rain - 100) * 0.15, 90)  # 75-90 (max 90)

def calculate_location_factor(flood_history, drainage_quality, nearby_water):
    """
    คำนวณตัวคูณจากปัจจัยพื้นที่
    - flood_history: 1=ไม่เคย(×1.0), 2=เคย 1-2 ครั้ง(×1.15), 3=ท่วมบ่อย(×1.3)
    - drainage_quality: 1=แย่มาก(×1.2), 2=พอใช้(×1.1), 3=ดี(×1.0), 4=ดีมาก(×0.9)
    - nearby_water: 0=ไม่ใกล้(×1.0), 1=ใกล้(×1.15)
    """
    # Flood history factor
    if flood_history >= 3:
        flood_factor = 1.3
    elif flood_history == 2:
        flood_factor = 1.15
    else:
        flood_factor = 1.0
    
    # Drainage factor
    if drainage_quality <= 1:
        drain_factor = 1.2
    elif drainage_quality == 2:
        drain_factor = 1.1
    elif drainage_quality == 3:
        drain_factor = 1.0
    else:
        drain_factor = 0.9
    
    # Nearby water factor
    water_factor = 1.15 if nearby_water >= 1 else 1.0
    
    return flood_factor * drain_factor * water_factor

def calculate_risk_score_v33(past_3d, forecast_3d, flood_history, drainage_quality, nearby_water):
    """
    สูตร v3.3: Risk = Rain_Score × Location_Factor
    
    Rain_Score = จากฝนผสม (60% จริง + 40% พยากรณ์)
    Location_Factor = ตัวคูณจากประวัติ/ระบายน้ำ/ใกล้แหล่งน้ำ
    """
    rain_score = calculate_rain_score_v33(past_3d, forecast_3d)
    location_factor = calculate_location_factor(flood_history, drainage_quality, nearby_water)
    
    total = rain_score * location_factor
    return min(total, 100)  # Cap at 100

def get_risk_level_v33(score):
    """
    เกณฑ์ระดับความเสี่ยง v3.3
    - 70-100: รุนแรง
    - 50-69: สูง
    - 30-49: ปานกลาง
    - 0-29: ต่ำ
    """
    if score >= 70:
        return 'รุนแรง'
    elif score >= 50:
        return 'สูง'
    elif score >= 30:
        return 'ปานกลาง'
    else:
        return 'ต่ำ'

def update_rain_data():
    """Update rain data for all stations with v3.3 formula (Past + Forecast)"""
    if not supabase:
        return False, "ไม่สามารถเชื่อมต่อ Database"
    
    try:
        # Load stations
        stations_response = supabase.table("stations").select("station_id, latitude, longitude, flood_history, drainage_quality, nearby_water").execute()
        stations = stations_response.data
        
        updated = 0
        total = len(stations)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, station in enumerate(stations):
            station_id = station['station_id']
            lat = station.get('latitude', 13.7)
            lon = station.get('longitude', 100.5)
            
            # Get combined rain data (past + forecast)
            past_3d, forecast_3d, all_7_days = get_combined_rain_data(lat, lon)
            
            # Calculate risk with v3.3 formula
            risk_score = calculate_risk_score_v33(
                past_3d,
                forecast_3d,
                station.get('flood_history', 1),
                station.get('drainage_quality', 3),
                station.get('nearby_water', 0)
            )
            risk_level = get_risk_level_v33(risk_score)
            
            # Combined for display
            rain_3d_combined = (past_3d * 0.6) + (forecast_3d * 0.4)
            rain_7d_total = sum(all_7_days)
            
            # Update flood_weather table
            supabase.table("flood_weather").upsert({
                'station_id': station_id,
                'rain_day1': round(all_7_days[0], 1),  # past 3 days
                'rain_day2': round(all_7_days[1], 1),
                'rain_day3': round(all_7_days[2], 1),
                'rain_day4': round(all_7_days[3], 1),  # today + forecast
                'rain_day5': round(all_7_days[4], 1),
                'rain_day6': round(all_7_days[5], 1),
                'rain_day7': round(all_7_days[6], 1),
                'rain_3d_total': round(rain_3d_combined, 1),  # Combined score
                'rain_7d_total': round(rain_7d_total, 1),
                'past_3d_actual': round(past_3d, 1),  # ฝนจริง 3 วัน
                'forecast_3d': round(forecast_3d, 1),  # พยากรณ์ 3 วัน
                'risk_score': round(risk_score, 1),
                'risk_level': risk_level,
                'updated_at': datetime.utcnow().isoformat()
            }, on_conflict='station_id').execute()
            
            updated += 1
            progress_bar.progress((i + 1) / total)
            status_text.text(f"กำลังอัปเดต: {station_id} ({i+1}/{total}) | ฝนจริง: {past_3d:.1f}mm | พยากรณ์: {forecast_3d:.1f}mm")
            
            # Small delay to avoid API rate limit
            time.sleep(0.15)
        
        progress_bar.empty()
        status_text.empty()
        return True, f"อัปเดตสำเร็จ {updated} สถานี (ใช้ข้อมูลผสม: ฝนจริง 60% + พยากรณ์ 40%)"
    
    except Exception as e:
        return False, f"Error: {str(e)}"

# ==========================================
# EXPORT FUNCTIONS
# ==========================================
def export_to_excel(dataframes_dict):
    """Export multiple dataframes to Excel"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dataframes_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("## 🚗 EV Stations")
    st.markdown("---")
    
    page = st.radio(
        "เมนู",
        ["📊 แดชบอร์ด", "🌧️ ความเสี่ยงน้ำท่วม", "🔧 ตาราง PM", "⚠️ บันทึกเคสเสีย", "📦 สต๊อกอะไหล่", "🗺️ แผนที่สถานี"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### ⚙️ ตั้งค่า")
    auto_refresh = st.checkbox("Auto Refresh (5 นาที)", value=False)
    
    st.markdown("---")
    
    # Database status
    if supabase:
        st.success("✅ เชื่อมต่อ Database แล้ว")
    else:
        st.warning("⚠️ ไม่สามารถเชื่อมต่อ Database")
    
    st.markdown("##### 📱 Version 3.3")
    st.markdown("##### 🧮 สูตรผสม: ฝนจริง 60% + พยากรณ์ 40%")
    st.markdown("##### Made with Streamlit + Supabase")

# ==========================================
# LOAD DATA
# ==========================================
df_stations = load_stations()
df_pm = load_pm_schedule()
df_incidents = load_incidents()
df_parts = load_spare_parts()
df_flood = load_flood_weather()
df_chargers = load_charger_units()

# Calculate KPIs
flood_counts = df_flood['risk_level'].value_counts() if 'risk_level' in df_flood.columns else pd.Series()
pm_counts = df_pm['pm_status'].value_counts() if 'pm_status' in df_pm.columns else pd.Series()
inc_counts = df_incidents['status'].value_counts() if 'status' in df_incidents.columns else pd.Series()
parts_counts = df_parts['stock_status'].value_counts() if 'stock_status' in df_parts.columns else pd.Series()

# ==========================================
# MAIN CONTENT
# ==========================================
if page == "📊 แดชบอร์ด":
    # Header
    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.markdown("## 🚗 แดชบอร์ดสถานีชาร์จ EV")
        st.caption(f"อัปเดตล่าสุด: {get_thai_time()}")
    
    with col_btn:
        if st.button("🌧️ อัปเดตข้อมูลฝน", type="primary", use_container_width=True):
            success, message = update_rain_data()
            if success:
                st.success(f'✅ {message}')
                time.sleep(1)
                st.rerun()
            else:
                st.error(f'❌ {message}')
    
    # KPI Cards
    st.markdown("### 📈 สรุปภาพรวม")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("#### 🌧️ ความเสี่ยงน้ำท่วม")
        st.metric("รุนแรง", flood_counts.get('รุนแรง', 0))
        st.metric("สูง", flood_counts.get('สูง', 0))
        st.metric("ปานกลาง", flood_counts.get('ปานกลาง', 0))
        st.metric("ต่ำ", flood_counts.get('ต่ำ', 0))
    
    with col2:
        st.markdown("#### 🔧 สถานะ PM")
        st.metric("เกินกำหนด", pm_counts.get('เกินกำหนด', 0))
        st.metric("ใกล้ถึง", pm_counts.get('ใกล้ถึง', 0))
        st.metric("ปกติ", pm_counts.get('ปกติ', 0))
    
    with col3:
        st.markdown("#### 📦 สถานะอะไหล่")
        st.metric("หมด", parts_counts.get('หมด', 0))
        st.metric("ใกล้หมด", parts_counts.get('ใกล้หมด', 0))
        st.metric("ปกติ", parts_counts.get('ปกติ', 0))
    
    with col4:
        st.markdown("#### ⚠️ เคสเสีย")
        st.metric("รอดำเนินการ", inc_counts.get('รอดำเนินการ', 0))
        st.metric("กำลังดำเนินการ", inc_counts.get('กำลังดำเนินการ', 0))
        st.metric("เสร็จสิ้น", inc_counts.get('เสร็จสิ้น', 0))
    
    # Action Items
    st.markdown("### 🚨 รายการที่ต้องดำเนินการ")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        risk_count = flood_counts.get('ปานกลาง', 0) + flood_counts.get('สูง', 0) + flood_counts.get('รุนแรง', 0)
        st.info(f"🌧️ **สถานีเสี่ยงน้ำท่วม:** {risk_count} สถานี")
        st.warning(f"🔧 **เครื่อง PM เกินกำหนด:** {pm_counts.get('เกินกำหนด', 0)} เครื่อง")
    
    with col_b:
        parts_alert = parts_counts.get('หมด', 0) + parts_counts.get('ใกล้หมด', 0)
        st.error(f"📦 **อะไหล่หมด/ใกล้หมด:** {parts_alert} รายการ")
        st.warning(f"⚠️ **เคสเสียรอดำเนินการ:** {inc_counts.get('รอดำเนินการ', 0)} เคส")
    
    # Formula Info
    with st.expander("📊 สูตรคำนวณความเสี่ยงน้ำท่วม v3.3 (ผสมฝนจริง + พยากรณ์)"):
        st.markdown("""
        ### หลักการ v3.3
        > **ใช้ข้อมูลฝนจริง (60%) + พยากรณ์ (40%)**
        
        ```
        Combined Rain = (ฝนจริง 3 วัน × 0.6) + (พยากรณ์ 3 วัน × 0.4)
        Risk Score = Rain_Score × Location_Factor
        ```
        
        ### ทำไมต้องผสม?
        | ข้อมูล | ความแม่น | น้ำหนัก |
        |--------|----------|---------|
        | 🔵 ฝนจริงย้อนหลัง | 100% | 60% |
        | 🟡 พยากรณ์ | 70-80% | 40% |
        
        ### ตัวอย่าง
        - ฝนจริง 0mm + พยากรณ์ 50mm = (0×0.6) + (50×0.4) = **20mm** → คะแนนต่ำ 🟢
        - ฝนจริง 50mm + พยากรณ์ 50mm = (50×0.6) + (50×0.4) = **50mm** → คะแนนสูง 🟠
        
        ### ระดับความเสี่ยง
        - 🔴 รุนแรง: 70-100
        - 🟠 สูง: 50-69
        - 🟡 ปานกลาง: 30-49
        - 🟢 ต่ำ: 0-29
        """)
    
    # Export Button
    st.markdown("---")
    st.markdown("### 📥 Export ข้อมูล")
    
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    
    with col_exp1:
        if st.button("📊 Export รายงานทั้งหมด", use_container_width=True):
            excel_data = export_to_excel({
                'สถานี': df_stations,
                'ความเสี่ยงน้ำท่วม': df_flood,
                'ตารางPM': df_pm,
                'เคสเสีย': df_incidents,
                'อะไหล่': df_parts
            })
            st.download_button(
                label="⬇️ ดาวน์โหลด Excel",
                data=excel_data,
                file_name=f"EV_Report_{get_thai_time().replace(':', '-').replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

elif page == "🌧️ ความเสี่ยงน้ำท่วม":
    st.markdown("## 🌧️ ความเสี่ยงน้ำท่วม")
    st.caption(f"อัปเดตล่าสุด: {get_thai_time()} | 🧮 สูตร v3.3: ฝนจริง 60% + พยากรณ์ 40%")
    
    # Update button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 อัปเดตข้อมูลฝน", type="primary", use_container_width=True):
            success, message = update_rain_data()
            if success:
                st.success(f'✅ {message}')
                time.sleep(1)
                st.rerun()
            else:
                st.error(f'❌ {message}')
    
    # Info box
    st.info("📊 **ข้อมูลใหม่:** rain_day1-3 = ฝนจริงย้อนหลัง | rain_day4-7 = วันนี้+พยากรณ์ | past_3d_actual = ฝนจริงรวม | forecast_3d = พยากรณ์รวม")
    
    # Filters
    risk_filter = st.multiselect(
        "กรองตามระดับเสี่ยง", 
        ['รุนแรง', 'สูง', 'ปานกลาง', 'ต่ำ'], 
        default=['รุนแรง', 'สูง', 'ปานกลาง']
    )
    
    if not df_flood.empty and 'risk_level' in df_flood.columns:
        # Merge with stations to get station_name
        if not df_stations.empty:
            df_flood_display = df_flood.merge(
                df_stations[['station_id', 'station_name', 'province']], 
                on='station_id', 
                how='left'
            )
            # Reorder columns - important columns first
            cols = ['station_id', 'station_name', 'province', 'risk_level', 'risk_score', 
                    'past_3d_actual', 'forecast_3d', 'rain_3d_total',
                    'rain_day1', 'rain_day2', 'rain_day3', 
                    'rain_day4', 'rain_day5', 'rain_day6', 'rain_day7', 'updated_at']
            cols = [c for c in cols if c in df_flood_display.columns]
            df_flood_display = df_flood_display[cols]
        else:
            df_flood_display = df_flood
        
        df_filtered = df_flood_display[df_flood_display['risk_level'].isin(risk_filter)]
        
        # Summary
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("รุนแรง 🔴", len(df_filtered[df_filtered['risk_level'] == 'รุนแรง']))
        col2.metric("สูง 🟠", len(df_filtered[df_filtered['risk_level'] == 'สูง']))
        col3.metric("ปานกลาง 🟡", len(df_filtered[df_filtered['risk_level'] == 'ปานกลาง']))
        col4.metric("ต่ำ 🟢", len(df_filtered[df_filtered['risk_level'] == 'ต่ำ']))
        
        # Table
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        
        # Download
        st.download_button(
            label="📥 ดาวน์โหลด CSV",
            data=df_filtered.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"flood_risk_{get_thai_time().replace(':', '-').replace(' ', '_')}.csv",
            mime="text/csv"
        )
    else:
        st.info("ยังไม่มีข้อมูลความเสี่ยงน้ำท่วม")

elif page == "🔧 ตาราง PM":
    st.markdown("## 🔧 ตาราง PM")
    st.caption(f"อัปเดตล่าสุด: {get_thai_time()}")
    
    # Add PM record form
    with st.expander("➕ บันทึกงาน PM"):
        col1, col2 = st.columns(2)
        with col1:
            pm_unit = st.selectbox(
                "รหัสเครื่อง", 
                df_pm['unit_id'].unique() if not df_pm.empty else []
            )
            pm_date = st.date_input("วันที่ทำ PM", datetime.now())
        with col2:
            pm_technician = st.text_input("ช่างผู้ทำ")
            pm_notes = st.text_area("หมายเหตุ")
        
        if st.button("💾 บันทึก PM", type="primary"):
            if pm_unit and pm_technician and supabase:
                try:
                    # Update PM record
                    next_pm = pm_date + timedelta(days=90)
                    supabase.table("pm_schedule").update({
                        "last_pm_date": pm_date.isoformat(),
                        "next_pm_date": next_pm.isoformat(),
                        "days_until_pm": 90,
                        "pm_status": "ปกติ",
                        "technician": pm_technician,
                        "notes": pm_notes,
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("unit_id", pm_unit).execute()
                    st.success(f"✅ บันทึก PM สำเร็จ: {pm_unit}")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("กรุณากรอกข้อมูลให้ครบ")
    
    # Filters
    status_filter = st.multiselect(
        "กรองตามสถานะ", 
        ['เกินกำหนด', 'ใกล้ถึง', 'ปกติ'], 
        default=['เกินกำหนด', 'ใกล้ถึง']
    )
    
    if not df_pm.empty and 'pm_status' in df_pm.columns:
        # Merge with stations to get station_name
        if not df_stations.empty:
            df_pm_display = df_pm.merge(
                df_stations[['station_id', 'station_name', 'province']], 
                on='station_id', 
                how='left'
            )
            # Reorder columns
            cols = ['unit_id', 'station_id', 'station_name', 'pm_status', 'days_until_pm',
                    'last_pm_date', 'next_pm_date', 'technician', 'notes']
            cols = [c for c in cols if c in df_pm_display.columns]
            df_pm_display = df_pm_display[cols]
        else:
            df_pm_display = df_pm
        
        df_pm_filtered = df_pm_display[df_pm_display['pm_status'].isin(status_filter)]
        
        # Summary
        col1, col2, col3 = st.columns(3)
        col1.metric("เกินกำหนด 🔴", len(df_pm[df_pm['pm_status'] == 'เกินกำหนด']))
        col2.metric("ใกล้ถึง 🟡", len(df_pm[df_pm['pm_status'] == 'ใกล้ถึง']))
        col3.metric("ปกติ 🟢", len(df_pm[df_pm['pm_status'] == 'ปกติ']))
        
        st.dataframe(df_pm_filtered, use_container_width=True, hide_index=True)
        
        # Download
        st.download_button(
            label="📥 ดาวน์โหลด CSV",
            data=df_pm_filtered.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"pm_schedule_{get_thai_time().replace(':', '-').replace(' ', '_')}.csv",
            mime="text/csv"
        )
    else:
        st.info("ยังไม่มีข้อมูล PM")

elif page == "⚠️ บันทึกเคสเสีย":
    st.markdown("## ⚠️ บันทึกเคสเสีย")
    st.caption(f"อัปเดตล่าสุด: {get_thai_time()}")
    
    # Add new incident form
    with st.expander("➕ เพิ่มเคสใหม่"):
        col1, col2 = st.columns(2)
        with col1:
            new_station = st.selectbox(
                "รหัสสถานี",
                df_stations['station_id'].unique() if not df_stations.empty else []
            )
            new_issue = st.selectbox(
                "ประเภทปัญหา", 
                ['หัวชาร์จเสีย', 'หน้าจอไม่ทำงาน', 'จ่ายไฟไม่ได้', 'ระบบชำระเงินขัดข้อง', 'อื่นๆ']
            )
        with col2:
            new_severity = st.selectbox("ความรุนแรง", ['วิกฤต', 'สูง', 'ปานกลาง', 'ต่ำ'])
            new_desc = st.text_area("รายละเอียด")
        
        if st.button("💾 บันทึกเคส", type="primary"):
            if new_station and supabase:
                try:
                    case_id = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    supabase.table("incidents").insert({
                        "case_id": case_id,
                        "station_id": new_station,
                        "issue_type": new_issue,
                        "severity": new_severity,
                        "description": new_desc,
                        "status": "รอดำเนินการ",
                        "report_date": datetime.now().date().isoformat()
                    }).execute()
                    st.success(f"✅ บันทึกเคส {case_id} เรียบร้อย!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("กรุณาเลือกสถานี")
    
    # Update incident status
    with st.expander("✏️ อัปเดตสถานะเคส"):
        col1, col2 = st.columns(2)
        with col1:
            update_case = st.selectbox(
                "เลือกเคส",
                df_incidents['case_id'].unique() if not df_incidents.empty else []
            )
            update_status = st.selectbox("สถานะใหม่", ['รอดำเนินการ', 'กำลังดำเนินการ', 'เสร็จสิ้น'])
        with col2:
            update_tech = st.text_input("ผู้ซ่อม")
            update_cause = st.text_area("สาเหตุ")
        
        if st.button("💾 อัปเดตเคส", type="primary", key="update_inc"):
            if update_case and supabase:
                try:
                    update_data = {
                        "status": update_status,
                        "technician": update_tech,
                        "root_cause": update_cause
                    }
                    if update_status == 'เสร็จสิ้น':
                        update_data["resolved_date"] = datetime.now().date().isoformat()
                    
                    supabase.table("incidents").update(update_data).eq("case_id", update_case).execute()
                    st.success(f"✅ อัปเดตเคส {update_case} เรียบร้อย!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    # Display incidents
    status_filter = st.multiselect(
        "กรองตามสถานะ", 
        ['รอดำเนินการ', 'กำลังดำเนินการ', 'เสร็จสิ้น'], 
        default=['รอดำเนินการ', 'กำลังดำเนินการ']
    )
    
    if not df_incidents.empty and 'status' in df_incidents.columns:
        # Merge with stations to get station_name
        if not df_stations.empty:
            df_inc_display = df_incidents.merge(
                df_stations[['station_id', 'station_name', 'province']], 
                on='station_id', 
                how='left'
            )
            # Reorder columns
            cols = ['case_id', 'report_date', 'station_id', 'station_name', 'issue_type', 
                    'severity', 'status', 'technician', 'description', 'root_cause', 'resolved_date']
            cols = [c for c in cols if c in df_inc_display.columns]
            df_inc_display = df_inc_display[cols]
        else:
            df_inc_display = df_incidents
        
        df_inc_filtered = df_inc_display[df_inc_display['status'].isin(status_filter)]
        st.dataframe(df_inc_filtered, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูลเคสเสีย")

elif page == "📦 สต๊อกอะไหล่":
    st.markdown("## 📦 สต๊อกอะไหล่")
    st.caption(f"อัปเดตล่าสุด: {get_thai_time()}")
    
    # Update stock form
    with st.expander("✏️ อัปเดตสต๊อก"):
        col1, col2 = st.columns(2)
        with col1:
            update_part = st.selectbox(
                "เลือกอะไหล่",
                df_parts['part_id'].unique() if not df_parts.empty else []
            )
            action = st.radio("การดำเนินการ", ['เบิก', 'รับเข้า'])
        with col2:
            qty_change = st.number_input("จำนวน", min_value=1, value=1)
        
        if st.button("💾 อัปเดตสต๊อก", type="primary"):
            if update_part and supabase:
                try:
                    # Get current quantity
                    current = supabase.table("spare_parts").select("quantity, min_stock").eq("part_id", update_part).execute()
                    if current.data:
                        current_qty = current.data[0]['quantity']
                        min_stock = current.data[0]['min_stock']
                        
                        if action == 'เบิก':
                            new_qty = max(0, current_qty - qty_change)
                        else:
                            new_qty = current_qty + qty_change
                        
                        # Determine status
                        if new_qty == 0:
                            new_status = 'หมด'
                        elif new_qty < min_stock:
                            new_status = 'ใกล้หมด'
                        else:
                            new_status = 'ปกติ'
                        
                        supabase.table("spare_parts").update({
                            "quantity": new_qty,
                            "stock_status": new_status,
                            "updated_at": datetime.utcnow().isoformat()
                        }).eq("part_id", update_part).execute()
                        
                        st.success(f"✅ อัปเดตสต๊อก {update_part}: {current_qty} → {new_qty}")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    # Summary
    if not df_parts.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("หมด 🔴", parts_counts.get('หมด', 0))
        col2.metric("ใกล้หมด 🟡", parts_counts.get('ใกล้หมด', 0))
        col3.metric("ปกติ 🟢", parts_counts.get('ปกติ', 0))
        
        # Table
        st.markdown("### รายการอะไหล่")
        
        # Reorder columns
        cols = ['part_id', 'part_name', 'category', 'quantity', 'min_stock', 
                'stock_status', 'unit_price', 'supplier']
        cols = [c for c in cols if c in df_parts.columns]
        df_parts_display = df_parts[cols]
        
        st.dataframe(df_parts_display, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูลอะไหล่")

elif page == "🗺️ แผนที่สถานี":
    st.markdown("## 🗺️ แผนที่สถานี")
    st.caption(f"แสดงตำแหน่งสถานีทั้งหมด {len(df_stations)} สถานี")
    
    if not df_stations.empty and 'latitude' in df_stations.columns and 'longitude' in df_stations.columns:
        # Filter by province
        provinces = ['ทั้งหมด'] + sorted(df_stations['province'].dropna().unique().tolist())
        selected_province = st.selectbox("กรองตามจังหวัด", provinces)
        
        if selected_province != 'ทั้งหมด':
            df_map = df_stations[df_stations['province'] == selected_province]
        else:
            df_map = df_stations
        
        # Prepare map data
        map_data = df_map[['latitude', 'longitude']].dropna()
        map_data.columns = ['lat', 'lon']
        
        st.map(map_data)
        
        st.markdown(f"### 📍 แสดง {len(map_data)} สถานี")
        
        # Display columns
        cols = ['station_id', 'station_name', 'province', 'latitude', 'longitude']
        cols = [c for c in cols if c in df_map.columns]
        
        st.dataframe(df_map[cols], use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูลตำแหน่งสถานี")

# Auto refresh
if auto_refresh:
    time.sleep(300)
    st.rerun()
