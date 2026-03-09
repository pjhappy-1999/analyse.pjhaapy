import pandas as pd
import sys

try:
    print("Loading CSV...")
    df = pd.read_csv('Global WFP Food Prices.csv', low_memory=False)
    print(f"Loaded {len(df)} rows.")

    target_crops = ['Wheat', 'Maize', 'Soybeans', 'Cotton', 'Palm Oil']
    print(f"Searching for {target_crops}...")
    
    # Check if 'commodity' column exists
    if 'commodity' not in df.columns:
        print("Error: 'commodity' column not found.")
        print(df.columns)
        sys.exit(1)

    # Use str.contains with case=False
    mask = df['commodity'].str.contains('|'.join(target_crops), case=False, na=False)
    
    filtered = df[mask]
    print(f"Found {len(filtered)} matches.")

    if len(filtered) > 0:
        result = filtered.groupby(['commodity', 'unit']).size()
        with open('check_units_output.txt', 'w', encoding='utf-8') as f:
            f.write(result.to_string())
        print("Output written to check_units_output.txt")
    else:
        print("No matches found.")

except Exception as e:
    print(f"An error occurred: {e}")
