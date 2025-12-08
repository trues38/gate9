from g9_macro_factory.config import get_supabase_client
import json
import os

def export_lehman_week():
    sb = get_supabase_client()
    print("Fetching Lehman Week Data...")
    
    # Fetch data
    res = sb.table('daily_reports')\
        .select('date, content')\
        .gte('date', '2008-09-15')\
        .lte('date', '2008-09-22')\
        .order('date')\
        .execute()
        
    if not res.data:
        print("No data found for Lehman Week.")
        return

    markdown_content = "# 📉 Lehman Week Report (2008-09-15 ~ 2008-09-22)\n\n"
    markdown_content += "Verification of G9 Engine's response to the 2008 Financial Crisis start.\n\n"
    
    for row in res.data:
        date = row['date']
        raw_content = row['content']
        
        if isinstance(raw_content, str):
            data = json.loads(raw_content)
        else:
            data = raw_content
            
        summary = "\n".join([f"> {line}" for line in data.get('summary_3line', [])])
        risk_level = data.get('risk_signals', {}).get('level', 'N/A')
        risk_factors = ", ".join(data.get('risk_signals', {}).get('risk_factors', []))
        insight = data.get('structural_insight', {}).get('narrative', 'N/A')
        
        markdown_content += f"## 📅 {date}\n"
        markdown_content += f"**Risk Level**: `{risk_level}` | **Factors**: `{risk_factors}`\n\n"
        markdown_content += f"### 📝 Summary\n{summary}\n\n"
        markdown_content += f"### 🏗️ Structural Insight\n{insight}\n\n"
        markdown_content += "---\n\n"

    # Save to file
    output_path = "lehman_week_report.md"
    with open(output_path, "w") as f:
        f.write(markdown_content)
        
    print(f"✅ Exported to {output_path}")

if __name__ == "__main__":
    export_lehman_week()
