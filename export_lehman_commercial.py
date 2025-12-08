import json
from g9_macro_factory.config import get_supabase_client

def export_report():
    sb = get_supabase_client()
    
    # Fetch Daily Reports
    res = sb.table('daily_reports').select('*').gte('date', '2008-09-15').lte('date', '2008-09-22').order('date').execute()
    daily_reports = res.data
    
    # Fetch Weekly Report
    res_w = sb.table('weekly_summaries').select('*').eq('start_date', '2008-09-15').execute()
    weekly_report = res_w.data[0] if res_w.data else None
    
    md_content = "# 📊 Lehman Week Report (Commercial Version)\n\n"
    
    md_content += "## 📅 Daily Reports\n"
    for r in daily_reports:
        try:
            content = json.loads(r['content']) if isinstance(r['content'], str) else r['content']
            
            md_content += f"### {r['date']} ({content.get('market_context', {}).get('regime', 'N/A')})\n"
            
            # Z-Score Analysis
            zscore = content.get('zscore_focus', {})
            md_content += f"**📉 Z-Score Focus**: {zscore.get('top_sector', 'N/A')}\n"
            
            # Chain (Strict 3 Steps)
            chain = zscore.get('event_chain', [])
            if isinstance(chain, list):
                md_content += "**🔗 Chain**:\n"
                for step in chain:
                    md_content += f"  - {step}\n"
            else:
                md_content += f"**🔗 Chain**: {chain}\n"
            
            md_content += "\n"
            
            # Action Drivers
            drivers = content.get('action_drivers', {})
            md_content += f"**🚀 Action Drivers**:\n"
            md_content += f"- Primary: {drivers.get('primary', 'N/A')}\n"
            md_content += f"- Bias: {drivers.get('intraday_bias', 'N/A')} ({drivers.get('pressure_direction', 'N/A')})\n"
            md_content += f"- Strength: {drivers.get('driver_strength', 'N/A')}\n\n"
            
            # Summary
            md_content += "**📝 Summary**:\n"
            for line in content.get('summary_3line', []):
                md_content += f"- {line}\n"
            
            md_content += "\n---\n"
        except Exception as e:
            md_content += f"Error parsing {r['date']}: {e}\n\n"

    if weekly_report:
        md_content += "## 📅 Weekly Report (2008-09-15 ~ 2008-09-21)\n"
        try:
            content = json.loads(weekly_report['content']) if isinstance(weekly_report['content'], str) else weekly_report['content']
            md_content += "**Executive Summary (Strict 3-Line)**:\n"
            for line in content.get('executive_summary', []):
                md_content += f"- {line}\n"
        except:
            md_content += "Error parsing weekly report.\n"

    with open("lehman_week_report_commercial.md", "w") as f:
        f.write(md_content)
    
    print("Exported to lehman_week_report_commercial.md")

if __name__ == "__main__":
    export_report()
