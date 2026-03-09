import pandas as pd
import sys

try:
    print("Loading CSV...")
    df = pd.read_csv('Global WFP Food Prices.csv', low_memory=False)

    target_patterns = ['Wheat', 'Maize', 'Soybeans', 'Cotton', 'Palm']
    print(f"Searching for {target_patterns}...")
    
    mask = df['commodity'].str.contains('|'.join(target_patterns), case=False, na=False)
    
    filtered = df[mask]
    
    if len(filtered) > 0:
        result = filtered.groupby(['commodity', 'unit']).size()
        with open('check_units_output_2.txt', 'w', encoding='utf-8') as f:
            f.write(result.to_string())
        print("Output written to check_units_output_2.txt")
    else:
        print("No matches found.")

except Exception as e:
    print(f"An error occurred: {e}")
