
import duckdb
import pandas as pd
import json

con = duckdb.connect("nba_sql.duckdb", read_only=True)
df = con.execute("SELECT * FROM rdata_treasury LIMIT 10").fetchdf()
df.columns = df.columns.str.lower()
con.close()

print("Columns:", df.columns.tolist())
print("\nSample Data:")
print(df[['date', 'team', 'opponent']].head())

# Check Date Type
print("\nDate Type:", type(df['date'].iloc[0]))
print("Date Value:", df['date'].iloc[0])

# Check Key Construction
df['date_dt'] = pd.to_datetime(df['date'])
df['key'] = df.apply(lambda x: f"{x['date_dt'].strftime('%Y%m%d')}_{x['team']}", axis=1)
print("\nGenerated Keys:")
print(df['key'].head())

# Check Story Mapping logic
# story: "2011-12-27", Team: "POR"
target_date = pd.to_datetime("2011-12-27")
target_key_por = f"{target_date.strftime('%Y%m%d')}_POR"
target_key_sac = f"{target_date.strftime('%Y%m%d')}_SAC"

print(f"\nTarget Keys: {target_key_por}, {target_key_sac}")
