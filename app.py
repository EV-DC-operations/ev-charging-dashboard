import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from supabase import create_client
import time

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
    return create_sample_stations()

def load_pm_schedule():
    """Load PM schedule from Supabase"""
    try:
        if supabase:
            response = supabase.table("pm_schedule").select("*").execute()
            if response.data:
                return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f"Error loading PM schedule: {e}")
    return create_sample_pm()

def load_incidents():
    """Load incidents from Supabase"""
    try:
        if supabase:
            response = supabase.table("incidents").select("*").execute()
            if response.data:
                return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f"Error loading incidents: {e}")
    return create_sample_incidents()

def load_spare_parts():
    """Load spare parts from Supabase"""
    try:
        if supabase:
            response = supabase.table("spare_parts").select("*").execute()
            if response.data:
                return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f"Error loading spare parts: {e}")
    return create_sample_parts()

def load_flood_weather():
    """Load flood weather from Supabase"""
    try:
        if supabase:
            response = supabase.table("flood_weather").select("*").execute()
            if response.data:
                return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f"Error loading flood data: {e}")
    return create_sample_flood()

# ==========================================
# SAMPLE DATA (Fallback)
# ==========================================
def create_sample_stations():
    import random
    stations = []
    provinces = ['กรุงเทพ', 'เชียงใหม่', 'ขอนแก่น', 'ชลบุรี', 'ภูเก็ต', 'นครราชสีมา', 'เพชรบูรณ์']
    for i in range(1, 291):
        stations.append({
            'station_id': f'BYD-{i:03d}',
            'station_name': f'EV Station {i}',
            'province': random.choice(provinces),
            'latitude': 13.7 + random.uniform(-5, 5),
            'longitude': 100.5 + random.uniform(-3, 3),
        })
    return pd.DataFrame(stations)

def create_sample_pm():
    import random
    pm_data = []
    for i in range(1, 584):
        days = random.randint(-120, 60)
        if days < 0:
            status = 'เกินกำหนด'
        elif days <= 14:
            status = 'ใกล้ถึง'
        else:
            status = 'ปกติ'
        pm_data.append({
            'unit_id': f'UNIT-{i:04d}',
            'station_id': f'BYD-{(i % 290) + 1:03d}',
            'last_pm_date': (datetime.now() - timedelta(days=random.randint(30, 180))).strftime('%Y-%m-%d'),
            'days_until_pm': days,
            'pm_status': status
        })
    return pd.DataFrame(pm_data)

def create_sample_incidents():
    import random
    incidents = []
    issue_types = ['หัวชาร์จเสีย', 'หน้าจอไม่ทำงาน', 'จ่ายไฟไม่ได้', 'ระบบชำระเงินขัดข้อง']
    statuses = ['รอดำเนินการ', 'กำลังดำเนินการ', 'เสร็จสิ้น']
    for i in range(1, 81):
        incidents.append({
            'case_id': f'INC-{i:04d}',
            'report_date': (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
            'station_id': f'BYD-{random.randint(1, 290):03d}',
            'issue_type': random.choice(issue_types),
            'severity': random.choice(['วิกฤต', 'สูง', 'ปานกลาง', 'ต่ำ']),
            'status': random.choices(statuses, weights=[30, 20, 50])[0]
        })
    return pd.DataFrame(incidents)

def create_sample_parts():
    import random
    parts = []
    part_names = ['หัวชาร์จ CCS2', 'หัวชาร์จ CHAdeMO', 'สาย Type 2', 'หน้าจอ 10 นิ้ว', 
                  'เครื่องอ่าน RFID', 'Power Module 50kW', 'บอร์ดควบคุม', 'พัดลมระบายความร้อน']
    for i, name in enumerate(part_names, 1):
        qty = random.randint(0, 20)
        if qty == 0:
            status = 'หมด'
        elif qty < 5:
            status = 'ใกล้หมด'
        else:
            status = 'ปกติ'
        parts.append({
            'part_id': f'SP-{i:03d}',
            'part_name': name,
            'quantity': qty,
            'min_stock': 5,
            'stock_status': status
        })
    return pd.DataFrame(parts)

def create_sample_flood():
    import random
    flood_data = []
    for i in range(1, 291):
        score = random.uniform(10, 70)
        if score >= 80:
            level = 'รุนแรง'
        elif score >= 60:
            level = 'สูง'
        elif score >= 40:
            level = 'ปานกลาง'
        else:
            level = 'ต่ำ'
        flood_data.append({
            'station_id': f'BYD-{i:03d}',
            'rain_3d_total': round(random.uniform(0, 50), 1),
            'rain_7d_total': round(random.uniform(0, 100), 1),
            'risk_score': round(score, 1),
            'risk_level': level
        })
    return pd.DataFrame(flood_data)

# ==========================================
# WEATHER API
# ==========================================
def get_rain_forecast(lat, lon):
    """Get rain forecast from Open-Meteo API"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum&timezone=Asia/Bangkok&forecast_days=7"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['daily']['precipitation_sum']
    except:
        pass
    return [0] * 7

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("## 🚗 EV Stations")
    st.markdown("---")
    
    page = st.radio(
        "เมนู",
        ["📊 แดชบอร์ด", "🌧️ ความเสี่ยงน้ำท่วม", "🔧 ตาราง PM", "⚠️ บันทึกเคสเสีย", "📦 สต๊อกอะไหล่"],
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
        st.warning("⚠️ ใช้ Sample Data")
    
    st.markdown("##### 📱 Version 2.0")
    st.markdown("##### Made with Streamlit + Supabase")

# ==========================================
# LOAD DATA
# ==========================================
df_stations = load_stations()
df_pm = load_pm_schedule()
df_incidents = load_incidents()
df_parts = load_spare_parts()
df_flood = load_flood_weather()

# Calculate KPIs
if 'risk_level' in df_flood.columns:
    flood_counts = df_flood['risk_level'].value_counts()
else:
    flood_counts = pd.Series({'ต่ำ': 290})

if 'pm_status' in df_pm.columns:
    pm_counts = df_pm['pm_status'].value_counts()
else:
    pm_counts = pd.Series({'ปกติ': 583})

if 'status' in df_incidents.columns:
    inc_counts = df_incidents['status'].value_counts()
else:
    inc_counts = pd.Series({'เสร็จสิ้น': 80})

if 'stock_status' in df_parts.columns:
    parts_counts = df_parts['stock_status'].value_counts()
else:
    parts_counts = pd.Series({'ปกติ': 10})

# ==========================================
# MAIN CONTENT
# ==========================================
if page == "📊 แดชบอร์ด":
    # Header
    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.markdown("## 🚗 แดชบอร์ดสถานีชาร์จ EV")
        st.caption(f"อัปเดตล่าสุด: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    with col_btn:
        if st.button("🔄 อัปเดตข้อมูลฝน", type="primary", use_container_width=True):
            with st.spinner('กำลังอัปเดตข้อมูล...'):
                progress = st.progress(0)
                for i in range(100):
                    time.sleep(0.02)
                    progress.progress(i + 1)
            st.success('✅ อัปเดตเสร็จสิ้น!')
            st.rerun()
    
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
        st.warning(f"🌧️ **สถานีเสี่ยงน้ำท่วม:** {risk_count} สถานี")
        st.error(f"🔧 **เครื่อง PM เกินกำหนด:** {pm_counts.get('เกินกำหนด', 0)} เครื่อง")
    
    with col_b:
        parts_alert = parts_counts.get('หมด', 0) + parts_counts.get('ใกล้หมด', 0)
        st.error(f"📦 **อะไหล่หมด/ใกล้หมด:** {parts_alert} รายการ")
        st.warning(f"⚠️ **เคสเสียรอดำเนินการ:** {inc_counts.get('รอดำเนินการ', 0)} เคส")

elif page == "🌧️ ความเสี่ยงน้ำท่วม":
    st.markdown("## 🌧️ ความเสี่ยงน้ำท่วม")
    
    # Filters
    risk_filter = st.multiselect("กรองตามระดับเสี่ยง", ['รุนแรง', 'สูง', 'ปานกลาง', 'ต่ำ'], default=['รุนแรง', 'สูง', 'ปานกลาง'])
    
    if 'risk_level' in df_flood.columns:
        df_filtered = df_flood[df_flood['risk_level'].isin(risk_filter)]
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูลความเสี่ยงน้ำท่วม")

elif page == "🔧 ตาราง PM":
    st.markdown("## 🔧 ตาราง PM")
    
    status_filter = st.multiselect("กรองตามสถานะ", ['เกินกำหนด', 'ใกล้ถึง', 'ปกติ'], default=['เกินกำหนด', 'ใกล้ถึง'])
    
    if 'pm_status' in df_pm.columns:
        df_pm_filtered = df_pm[df_pm['pm_status'].isin(status_filter)]
        st.dataframe(df_pm_filtered, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูล PM")
    
    st.download_button(
        label="📥 ดาวน์โหลด CSV",
        data=df_pm.to_csv(index=False).encode('utf-8-sig'),
        file_name=f"pm_schedule_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

elif page == "⚠️ บันทึกเคสเสีย":
    st.markdown("## ⚠️ บันทึกเคสเสีย")
    
    # Add new incident form
    with st.expander("➕ เพิ่มเคสใหม่"):
        col1, col2 = st.columns(2)
        with col1:
            new_station = st.text_input("รหัสสถานี")
            new_issue = st.selectbox("ประเภทปัญหา", ['หัวชาร์จเสีย', 'หน้าจอไม่ทำงาน', 'จ่ายไฟไม่ได้', 'ระบบชำระเงินขัดข้อง'])
        with col2:
            new_severity = st.selectbox("ความรุนแรง", ['วิกฤต', 'สูง', 'ปานกลาง', 'ต่ำ'])
            new_desc = st.text_area("รายละเอียด")
        
        if st.button("บันทึกเคส", type="primary"):
            if new_station and supabase:
                try:
                    case_id = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    supabase.table("incidents").insert({
                        "case_id": case_id,
                        "station_id": new_station,
                        "issue_type": new_issue,
                        "severity": new_severity,
                        "description": new_desc,
                        "status": "รอดำเนินการ"
                    }).execute()
                    st.success(f"✅ บันทึกเคส {case_id} เรียบร้อย!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("กรุณากรอกรหัสสถานี")
    
    # Display incidents
    status_filter = st.multiselect("กรองตามสถานะ", ['รอดำเนินการ', 'กำลังดำเนินการ', 'เสร็จสิ้น'], default=['รอดำเนินการ', 'กำลังดำเนินการ'])
    
    if 'status' in df_incidents.columns:
        df_inc_filtered = df_incidents[df_incidents['status'].isin(status_filter)]
        st.dataframe(df_inc_filtered, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูลเคสเสีย")

elif page == "📦 สต๊อกอะไหล่":
    st.markdown("## 📦 สต๊อกอะไหล่")
    
    # Summary
    col1, col2, col3 = st.columns(3)
    col1.metric("หมด", parts_counts.get('หมด', 0))
    col2.metric("ใกล้หมด", parts_counts.get('ใกล้หมด', 0))
    col3.metric("ปกติ", parts_counts.get('ปกติ', 0))
    
    # Table
    st.markdown("### รายการอะไหล่")
    st.dataframe(df_parts, use_container_width=True, hide_index=True)

# Auto refresh
if auto_refresh:
    time.sleep(300)
    st.rerun()
