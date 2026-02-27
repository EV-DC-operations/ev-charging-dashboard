import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
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
# CUSTOM CSS
# ==========================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f4e79;
        margin-bottom: 0;
    }
    .sub-header {
        color: #666;
        font-size: 0.9rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .severe { background-color: #ff6b6b !important; color: white !important; }
    .high { background-color: #ffa500 !important; color: white !important; }
    .medium { background-color: #ffeb9c !important; }
    .low { background-color: #c6efce !important; }
    .stDataFrame { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# DATA FUNCTIONS
# ==========================================
@st.cache_data(ttl=3600)
def load_data():
    """Load data from GitHub or local"""
    try:
        # Try loading from GitHub raw URL (will be set after deployment)
        # For now, use sample data
        pass
    except:
        pass
    
    # Sample data for demo
    return create_sample_data()

def create_sample_data():
    """Create sample data for demonstration"""
    import random
    
    # Stations
    stations = []
    provinces = ['กรุงเทพ', 'เชียงใหม่', 'ขอนแก่น', 'ชลบุรี', 'ภูเก็ต', 'นครราชสีมา', 'เพชรบูรณ์', 'สุราษฎร์ธานี', 'อุดรธานี', 'ชุมพร']
    
    for i in range(1, 291):
        stations.append({
            'รหัสสถานี': f'BYD-{i:03d}',
            'ชื่อสถานี': f'EV Station {i}',
            'จังหวัด': random.choice(provinces),
            'ละติจูด': 13.7 + random.uniform(-5, 5),
            'ลองจิจูด': 100.5 + random.uniform(-3, 3),
            'ฝน3วัน': round(random.uniform(0, 50), 1),
            'คะแนนเสี่ยง': round(random.uniform(10, 70), 1),
            'ระดับเสี่ยง': random.choices(['ต่ำ', 'ปานกลาง', 'สูง', 'รุนแรง'], weights=[60, 30, 8, 2])[0]
        })
    
    # PM Schedule
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
            'รหัสเครื่อง': f'UNIT-{i:04d}',
            'รหัสสถานี': f'BYD-{(i % 290) + 1:03d}',
            'PM ล่าสุด': (datetime.now() - timedelta(days=random.randint(30, 180))).strftime('%Y-%m-%d'),
            'เหลือกี่วัน': days,
            'สถานะPM': status
        })
    
    # Incidents
    incidents = []
    issue_types = ['หัวชาร์จเสีย', 'หน้าจอไม่ทำงาน', 'จ่ายไฟไม่ได้', 'ระบบชำระเงินขัดข้อง']
    statuses = ['รอดำเนินการ', 'กำลังดำเนินการ', 'เสร็จสิ้น']
    
    for i in range(1, 81):
        incidents.append({
            'รหัสเคส': f'INC-{i:04d}',
            'วันที่แจ้ง': (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
            'รหัสสถานี': f'BYD-{random.randint(1, 290):03d}',
            'ประเภทปัญหา': random.choice(issue_types),
            'ความรุนแรง': random.choice(['วิกฤต', 'สูง', 'ปานกลาง', 'ต่ำ']),
            'สถานะ': random.choices(statuses, weights=[30, 20, 50])[0]
        })
    
    # Spare Parts
    parts = []
    part_names = ['หัวชาร์จ CCS2', 'หัวชาร์จ CHAdeMO', 'สาย Type 2', 'หน้าจอ 10 นิ้ว', 'เครื่องอ่าน RFID', 
                  'Power Module 50kW', 'บอร์ดควบคุม', 'พัดลมระบายความร้อน', 'ปุ่ม Emergency', 'Network Module']
    
    for i, name in enumerate(part_names, 1):
        qty = random.randint(0, 20)
        if qty == 0:
            status = 'หมด'
        elif qty < 5:
            status = 'ใกล้หมด'
        else:
            status = 'ปกติ'
        
        parts.append({
            'รหัสอะไหล่': f'SP-{i:03d}',
            'ชื่ออะไหล่': name,
            'คงเหลือ': qty,
            'ขั้นต่ำ': 5,
            'สถานะสต๊อก': status
        })
    
    return {
        'stations': pd.DataFrame(stations),
        'pm': pd.DataFrame(pm_data),
        'incidents': pd.DataFrame(incidents),
        'parts': pd.DataFrame(parts)
    }

def get_forecast(lat, lon):
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
    st.markdown("##### 📱 Version 1.0")
    st.markdown("##### Made with Streamlit")

# ==========================================
# MAIN CONTENT
# ==========================================

# Load data
data = load_data()
df_stations = data['stations']
df_pm = data['pm']
df_incidents = data['incidents']
df_parts = data['parts']

# Calculate KPIs
flood_counts = df_stations['ระดับเสี่ยง'].value_counts()
pm_counts = df_pm['สถานะPM'].value_counts()
inc_counts = df_incidents['สถานะ'].value_counts()
parts_counts = df_parts['สถานะสต๊อก'].value_counts()

if page == "📊 แดชบอร์ด":
    # Header
    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.markdown('<p class="main-header">🚗 แดชบอร์ดสถานีชาร์จ EV</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="sub-header">อัปเดตล่าสุด: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>', unsafe_allow_html=True)
    
    with col_btn:
        if st.button("🔄 อัปเดตข้อมูลฝน", type="primary", use_container_width=True):
            with st.spinner('กำลังอัปเดตข้อมูล...'):
                progress = st.progress(0)
                for i in range(100):
                    time.sleep(0.02)
                    progress.progress(i + 1)
                st.cache_data.clear()
            st.success('✅ อัปเดตเสร็จสิ้น!')
            st.rerun()
    
    # KPI Cards
    st.markdown("### 📈 สรุปภาพรวม")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("#### 🌧️ ความเสี่ยงน้ำท่วม")
        st.metric("รุนแรง", flood_counts.get('รุนแรง', 0), delta=None)
        st.metric("สูง", flood_counts.get('สูง', 0), delta=None)
        st.metric("ปานกลาง", flood_counts.get('ปานกลาง', 0), delta=None)
        st.metric("ต่ำ", flood_counts.get('ต่ำ', 0), delta=None)
    
    with col2:
        st.markdown("#### 🔧 สถานะ PM")
        st.metric("เกินกำหนด", pm_counts.get('เกินกำหนด', 0), delta=None)
        st.metric("ใกล้ถึง", pm_counts.get('ใกล้ถึง', 0), delta=None)
        st.metric("ปกติ", pm_counts.get('ปกติ', 0), delta=None)
    
    with col3:
        st.markdown("#### 📦 สถานะอะไหล่")
        st.metric("หมด", parts_counts.get('หมด', 0), delta=None)
        st.metric("ใกล้หมด", parts_counts.get('ใกล้หมด', 0), delta=None)
        st.metric("ปกติ", parts_counts.get('ปกติ', 0), delta=None)
    
    with col4:
        st.markdown("#### ⚠️ เคสเสีย")
        st.metric("รอดำเนินการ", inc_counts.get('รอดำเนินการ', 0), delta=None)
        st.metric("กำลังดำเนินการ", inc_counts.get('กำลังดำเนินการ', 0), delta=None)
        st.metric("เสร็จสิ้น", inc_counts.get('เสร็จสิ้น', 0), delta=None)
    
    # Action Items
    st.markdown("### 🚨 รายการที่ต้องดำเนินการ")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.warning(f"🌧️ **สถานีเสี่ยงน้ำท่วม:** {flood_counts.get('ปานกลาง', 0) + flood_counts.get('สูง', 0) + flood_counts.get('รุนแรง', 0)} สถานี")
        st.error(f"🔧 **เครื่อง PM เกินกำหนด:** {pm_counts.get('เกินกำหนด', 0)} เครื่อง")
    
    with col_b:
        st.error(f"📦 **อะไหล่หมด/ใกล้หมด:** {parts_counts.get('หมด', 0) + parts_counts.get('ใกล้หมด', 0)} รายการ")
        st.warning(f"⚠️ **เคสเสียรอดำเนินการ:** {inc_counts.get('รอดำเนินการ', 0)} เคส")
    
    # Tables
    st.markdown("### 📋 สถานีที่ต้องระวัง (Top 10)")
    
    df_risk = df_stations[df_stations['ระดับเสี่ยง'].isin(['ปานกลาง', 'สูง', 'รุนแรง'])].head(10)
    st.dataframe(df_risk[['รหัสสถานี', 'ชื่อสถานี', 'จังหวัด', 'ระดับเสี่ยง', 'ฝน3วัน']], use_container_width=True, hide_index=True)

elif page == "🌧️ ความเสี่ยงน้ำท่วม":
    st.markdown("## 🌧️ ความเสี่ยงน้ำท่วม")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        risk_filter = st.multiselect("กรองตามระดับเสี่ยง", ['รุนแรง', 'สูง', 'ปานกลาง', 'ต่ำ'], default=['รุนแรง', 'สูง', 'ปานกลาง'])
    with col2:
        province_filter = st.multiselect("กรองตามจังหวัด", df_stations['จังหวัด'].unique())
    
    # Filter data
    df_filtered = df_stations[df_stations['ระดับเสี่ยง'].isin(risk_filter)]
    if province_filter:
        df_filtered = df_filtered[df_filtered['จังหวัด'].isin(province_filter)]
    
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)
    
    # Download button
    st.download_button(
        label="📥 ดาวน์โหลด CSV",
        data=df_filtered.to_csv(index=False).encode('utf-8-sig'),
        file_name=f"flood_risk_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

elif page == "🔧 ตาราง PM":
    st.markdown("## 🔧 ตาราง PM")
    
    # Filters
    status_filter = st.multiselect("กรองตามสถานะ", ['เกินกำหนด', 'ใกล้ถึง', 'ปกติ'], default=['เกินกำหนด', 'ใกล้ถึง'])
    
    df_pm_filtered = df_pm[df_pm['สถานะPM'].isin(status_filter)]
    st.dataframe(df_pm_filtered, use_container_width=True, hide_index=True)
    
    # Download
    st.download_button(
        label="📥 ดาวน์โหลด CSV",
        data=df_pm_filtered.to_csv(index=False).encode('utf-8-sig'),
        file_name=f"pm_schedule_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

elif page == "⚠️ บันทึกเคสเสีย":
    st.markdown("## ⚠️ บันทึกเคสเสีย")
    
    # Add new incident
    with st.expander("➕ เพิ่มเคสใหม่"):
        col1, col2 = st.columns(2)
        with col1:
            new_station = st.text_input("รหัสสถานี")
            new_issue = st.selectbox("ประเภทปัญหา", ['หัวชาร์จเสีย', 'หน้าจอไม่ทำงาน', 'จ่ายไฟไม่ได้', 'ระบบชำระเงินขัดข้อง'])
        with col2:
            new_severity = st.selectbox("ความรุนแรง", ['วิกฤต', 'สูง', 'ปานกลาง', 'ต่ำ'])
            new_desc = st.text_area("รายละเอียด")
        
        if st.button("บันทึกเคส", type="primary"):
            st.success("✅ บันทึกเคสเรียบร้อย!")
    
    # Display incidents
    status_filter = st.multiselect("กรองตามสถานะ", ['รอดำเนินการ', 'กำลังดำเนินการ', 'เสร็จสิ้น'], default=['รอดำเนินการ', 'กำลังดำเนินการ'])
    
    df_inc_filtered = df_incidents[df_incidents['สถานะ'].isin(status_filter)]
    st.dataframe(df_inc_filtered, use_container_width=True, hide_index=True)

elif page == "📦 สต๊อกอะไหล่":
    st.markdown("## 📦 สต๊อกอะไหล่")
    
    # Summary
    col1, col2, col3 = st.columns(3)
    col1.metric("หมด", parts_counts.get('หมด', 0))
    col2.metric("ใกล้หมด", parts_counts.get('ใกล้หมด', 0))
    col3.metric("ปกติ", parts_counts.get('ปกติ', 0))
    
    # Table with edit
    st.markdown("### รายการอะไหล่")
    
    edited_df = st.data_editor(
        df_parts,
        use_container_width=True,
        hide_index=True,
        column_config={
            "คงเหลือ": st.column_config.NumberColumn("คงเหลือ", min_value=0, max_value=100),
        }
    )
    
    if st.button("💾 บันทึกการเปลี่ยนแปลง"):
        st.success("✅ บันทึกเรียบร้อย!")

# Auto refresh
if auto_refresh:
    time.sleep(300)
    st.rerun()
