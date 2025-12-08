import streamlit as st
import pandas as pd
import altair as alt

def render_json_visuals(json_data):
    """Render visualizations for the JSON meta data."""
    
    # 1. Gravity Score Gauge
    score = json_data.get('gravity_score', 50)
    st.metric("🌌 Gravity Score", f"{score}/100", delta=None)
    st.progress(score / 100)
    
    # 2. Bull/Bear Ratio
    ratio_str = json_data.get('bull_bear_ratio', "50:50")
    try:
        bull, bear = map(int, ratio_str.split(':'))
        df_ratio = pd.DataFrame({
            'Sentiment': ['Bull', 'Bear'],
            'Value': [bull, bear]
        })
        
        c = alt.Chart(df_ratio).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="Value", type="quantitative"),
            color=alt.Color(field="Sentiment", type="nominal", scale=alt.Scale(domain=['Bull', 'Bear'], range=['#00E5FF', '#FF4B4B']))
        ).properties(height=200)
        
        st.altair_chart(c, use_container_width=True)
    except:
        st.text(f"Bull/Bear: {ratio_str}")

    # 3. Country Bias Table
    bias = json_data.get('country_bias', {})
    if bias:
        st.markdown("#### 🌍 Country Bias")
        df_bias = pd.DataFrame(list(bias.items()), columns=['Country', 'Bias'])
        st.table(df_bias)

    # 4. Key Tickers
    tickers = json_data.get('key_tickers', [])
    if tickers:
        st.markdown("#### 💹 Key Tickers")
        st.write(", ".join([f"`{t}`" for t in tickers]))

    # 5. Risk Factor
    risk = json_data.get('biggest_risk_factor', "None")
    st.error(f"⚠️ Risk: {risk}")
