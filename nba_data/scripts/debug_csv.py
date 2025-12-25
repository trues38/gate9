import pandas as pd
try:
    df = pd.read_csv('processed/rdata_treasury.csv', nrows=5)
    print(df[['Date', 'Team', 'Opponent']])
    with open('debug_head.txt', 'w') as f:
        f.write(df[['Date', 'Team', 'Opponent']].to_string())
except Exception as e:
    with open('debug_head.txt', 'w') as f:
        f.write(str(e))
