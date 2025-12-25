
import pyreadr
import pandas as pd

file_path = "/Users/js/Downloads/NBA_games_info.RData"

try:
    print(f"Loading {file_path}...")
    result = pyreadr.read_r(file_path)
    
    print("\n>>> Keys found in RData:")
    print(result.keys())
    
    # Iterate through keys and print info
    for key in result.keys():
        print(f"\nObject Name: {key}")
        df = result[key]
        if isinstance(df, pd.DataFrame):
            print(f"Type: DataFrame, Shape: {df.shape}")
            print(f"Columns ({len(df.columns)}):")
            for col in df.columns:
                print(f" - {col} ({df[col].dtype})")
            print("\nFirst 3 rows (transposed for readability):")
            print(df.head(3).T.to_string())
        else:
            print(f"Type: {type(df)}")

except Exception as e:
    print(f"Error reading file: {e}")
