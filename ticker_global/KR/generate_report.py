import pandas as pd
from collections import Counter
import os
import datetime

def analyze_and_generate_report(input_path, output_path):
    print(f"Loading data from {input_path}...")
    df = pd.read_csv(input_path)
    
    # Convert published_at to datetime
    df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce')
    
    # Filter for the latest available date in the dataset to simulate "Today's Briefing"
    latest_date = df['published_at'].max().date()
    target_date_str = latest_date.strftime('%Y-%m-%d')
    print(f"Generating report for date: {target_date_str}")
    
    # Filter data for that date
    daily_df = df[df['published_at'].dt.date == latest_date]
    
    if daily_df.empty:
        print("No data found for the latest date.")
        return

    # --- Analytics ---
    
    # 1. Top Signals (High Volume Tickers/Concepts)
    ticker_counts = daily_df['ticker'].value_counts().head(5)
    top_tickers = ticker_counts.index.tolist()
    
    # 2. Sentiment Analysis by Sector/Macro
    # Assuming 'sentiment' column exists and is numeric or convertible. 
    # If it's text (positive/negative), we map it.
    # For this script, let's assume it's missing or raw text, so we'll use keyword frequency as a proxy for "Heat".
    
    # 3. Extract Headlines for Top Tickers
    top_headlines = {}
    for ticker in top_tickers:
        row = daily_df[daily_df['ticker'] == ticker].iloc[0]
        top_headlines[ticker] = {
            "name": row['company_name'],
            "title": row['title'],
            "type": row.get('ticker_type', 'COMPANY')
        }

    # 4. Sector Trends
    sectors = daily_df[daily_df['ticker_type'] == 'SECTOR']['company_name'].value_counts().head(3).index.tolist()
    sector_summary = []
    for sector in sectors:
        headlines = daily_df[daily_df['company_name'] == sector]['title'].head(2).tolist()
        sector_summary.append(f"- **{sector}**: {headlines[0] if headlines else '관련 뉴스 없음'}")

    # 5. Macro/Risk Analysis
    macro_df = daily_df[daily_df['ticker_type'].isin(['MACRO', 'COMMODITY'])]
    macro_headlines = macro_df['title'].head(3).tolist()

    # --- Report Generation (Template Filling) ---
    
    report_content = f"""
==============================
📌 **오늘의 국내 경제 브리핑** ({target_date_str})
(소비자 대상 / 데이터 기반 분석)

### 1) 오늘 가장 강한 시그널 (Top 3)
"""
    for i, ticker in enumerate(top_tickers[:3]):
        info = top_headlines[ticker]
        report_content += f"- **[{info['name']}]**: {info['title']}\n"

    report_content += f"""
### 2) 생활 경제에 직접 영향 (Macro & Consumer)
- **거시경제 흐름**: {macro_headlines[0] if macro_headlines else '특이사항 없음'}
- **소비자 영향**: 최근 {top_headlines[top_tickers[0]]['name']} 관련 이슈가 시장의 주목을 받고 있으며, 이는 투자 심리에 직접적인 영향을 줄 수 있습니다.

### 3) 산업별 주요 흐름 (Sector Trends)
"""
    for item in sector_summary:
        report_content += f"{item}\n"

    report_content += """
### 4) 오늘의 리스크 & 기회
- **[Risk]**: 글로벌 불확실성(환율/금리)이 여전히 상존하는 가운데, 매크로 지표의 변동성에 유의해야 합니다.
- **[Opportunity]**: 거래량이 급증한 섹터나 기업(위 시그널 참조)에서 단기적인 모멘텀이 발생할 수 있습니다.

### 5) 한 문장 요약
"""
    main_topic = top_headlines[top_tickers[0]]['name']
    report_content += f'"오늘 한국 경제는 **{main_topic}** 이슈가 시장을 주도하며 뚜렷한 방향성을 보였습니다."'
    
    report_content += "\n=============================="

    print(f"Saving report to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print("Done!")

if __name__ == "__main__":
    BASE_DIR = "/Users/js/g9"
    # The file is in "ticker_global/KR/csv/"
    INPUT_CSV = os.path.join(BASE_DIR, "ticker_global/KR/csv/cleaned_events_final.csv")
    OUTPUT_REPORT = os.path.join(BASE_DIR, "ticker_global/KR/daily_briefing.md")
    
    analyze_and_generate_report(INPUT_CSV, OUTPUT_REPORT)
