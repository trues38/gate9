from g9_macro_factory.config import get_supabase_client

def cleanup():
    sb = get_supabase_client()
    print("Cleaning up Lehman Week Data...")
    
    # Delete Daily Reports
    res = sb.table('daily_reports').delete().gte('date', '2008-09-15').lte('date', '2008-09-22').execute()
    print(f"Deleted Daily Reports: {len(res.data)}")
    
    # Delete Weekly Reports
    res = sb.table('weekly_summaries').delete().eq('start_date', '2008-09-15').execute()
    print(f"Deleted Weekly Reports: {len(res.data)}")

if __name__ == "__main__":
    cleanup()
