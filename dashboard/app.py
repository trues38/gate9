import streamlit as st
import sys
import os
from pathlib import Path

# Add parent dir to path to import orchestra
sys.path.append(str(Path(__file__).parent.parent))

from orchestra.agent_orchestrator import run_orchestra
from dashboard.components.json_visualizer import render_json_visuals
from dashboard.utils.pdf_exporter import create_pdf

# Page Config
st.set_page_config(
    page_title="G9 Antigravity Dashboard",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
with open("dashboard/assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🌌 G9 Antigravity")
st.sidebar.markdown("---")

# 1. Country Selection
country = st.sidebar.selectbox(
    "🏳️ Primary Perspective",
    ["KR", "US", "JP", "CN", "GLOBAL"],
    index=0
)

# 1.5 Date Selection
from datetime import date
target_date = st.sidebar.date_input(
    "📅 Analysis Date",
    value=date(2024, 1, 1),
    min_value=date(2000, 1, 1),
    max_value=date(2025, 12, 31)
)

# 2. Report Level
level = st.sidebar.radio(
    "📊 Report Depth",
    ["G3 (Daily)", "G7 (Tactical)", "G9 (Strategic)"],
    index=1
)
level_code = level.split(" ")[0] # G3, G7, G9

# 3. Generation Mode
st.sidebar.markdown("---")
mode = st.sidebar.radio("⚙️ Generation Mode", ["Daily Auto Report", "Custom Query"])

query = None
if mode == "Custom Query":
    query = st.sidebar.text_area("📝 Enter your query", placeholder="e.g. Compare NVIDIA supply chain impact...")

# Generate Button
if st.sidebar.button("🚀 Generate Report", type="primary"):
    with st.spinner("🌌 Orchestrating 4-Nation Multi-Brain Analysis..."):
        try:
            # Call Engine
            result = run_orchestra(
                country=country,
                level=level_code,
                mode="custom" if query else "daily",
                query=query,
                target_date=str(target_date)
            )
            
            st.session_state['report_data'] = result
            st.success("Analysis Complete!")
        except Exception as e:
            st.error(f"Orchestration Failed: {e}")

# Main Content
if 'report_data' in st.session_state:
    data = st.session_state['report_data']
    
    # Header
    st.title(f"G9 Antigravity Report ({country} Perspective)")
    st.markdown(f"**Level**: {level} | **Mode**: {mode}")
    st.markdown("---")
    
    col1, col2 = st.columns([1.2, 0.8])
    
    with col1:
        st.subheader("📄 Strategic Insight")
        st.markdown(data['markdown_report'])
        
    with col2:
        st.subheader("📊 Gravity Metrics")
        if data.get('json_meta'):
            render_json_visuals(data['json_meta'])
        else:
            st.warning("No Meta Data Available")
            
    # Download Section
    st.markdown("---")
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        st.download_button(
            label="📦 Download JSON Packet",
            data=str(data['raw_packet']),
            file_name="g9_meta_packet.json",
            mime="application/json"
        )
    with d_col2:
        # PDF Export (Placeholder text for now)
        pdf_data = create_pdf(data['markdown_report'])
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_data,
            file_name="g9_report.pdf",
            mime="application/pdf"
        )

else:
    st.info("👈 Select options and click 'Generate Report' to start the G9 Engine.")
    st.markdown("""
    ### 🌌 Welcome to G9 Antigravity
    This dashboard provides a **multi-national strategic analysis** powered by the G9 Orchestrator.
    
    **Features:**
    - **4-Nation Rashomon Analysis**: US, CN, JP, KR perspectives.
    - **Gravity Mapping**: Structural, Financial, Psychological gravity analysis.
    - **Antigravity Momentum**: Identifying the single force breaking the gravity.
    """)
