import pandas as pd
import numpy as np
import json

def get_quarter(date):
    return f"{date.year}Q{date.quarter}"

def main():
    # Load WFP data
    print("Loading Global WFP Food Prices.csv...")
    df = pd.read_csv('Global WFP Food Prices.csv', usecols=['date', 'commodity', 'price_usd'], low_memory=False)
    
    # Filter for valid prices
    df = df[df['price_usd'] > 0]
    df['date'] = pd.to_datetime(df['date'])
    
    # Define commodity mapping
    # Wheat: 'Wheat', 'Wheat (white)', 'Wheat (mixed)', 'Wheat (imported)'
    # Maize: 'Maize', 'Maize (white)', 'Maize (yellow)', 'Maize (imported)', 'Maize (local)'
    # Soybeans: 'Soybeans'
    # Cotton: 'Cotton'
    # Palm Oil: 'Oil (palm)'
    
    # Create a mapping function or filter
    def map_commodity(c):
        c_lower = str(c).lower()
        if 'wheat' in c_lower and 'flour' not in c_lower and 'bread' not in c_lower and 'seed' not in c_lower and 'meal' not in c_lower:
            return 'Wheat'
        if 'maize' in c_lower and 'flour' not in c_lower and 'meal' not in c_lower and 'bran' not in c_lower and 'seed' not in c_lower and 'oil' not in c_lower:
            return 'Maize'
        if 'soybeans' in c_lower and 'oil' not in c_lower:
            return 'Soybeans'
        if 'cotton' in c_lower:
            # Include Oil (cotton) as proxy for Cotton since crop data is sparse
            return 'Cotton'
        if 'oil (palm)' in c_lower:
            return 'Palm Oil'
        if 'cotton' in c_lower and 'oil' in c_lower: # If 'Cotton' raw is scarce, maybe check oil? But user asked for crops.
            # User asked for "5 crops". Cotton is a crop. Oil (cotton) is a product.
            # But let's check if 'Cotton' has enough data. If not, maybe use 'Oil (cotton)' as proxy?
            # Earlier check showed 'Cotton' exists.
            pass 
        return None

    df['target_commodity'] = df['commodity'].apply(map_commodity)
    df = df.dropna(subset=['target_commodity'])
    
    # Calculate global monthly average price per commodity
    # We group by year-month and commodity
    df['year_month'] = df['date'].dt.to_period('M')
    
    print("Calculating monthly prices...")
    monthly_prices = df.groupby(['target_commodity', 'year_month'])['price_usd'].mean().reset_index()
    monthly_prices['date'] = monthly_prices['year_month'].dt.to_timestamp()
    monthly_prices = monthly_prices.sort_values(['target_commodity', 'date'])
    
    # Calculate Log Returns
    # ln(P_t / P_{t-1})
    monthly_prices['log_return'] = monthly_prices.groupby('target_commodity')['price_usd'].transform(lambda x: np.log(x / x.shift(1)))
    
    # Add Quarter
    monthly_prices['quarter'] = monthly_prices['date'].apply(get_quarter)
    
    # Calculate Quarterly Volatility (Std Dev of Log Returns)
    print("Calculating quarterly volatility...")
    volatility = monthly_prices.groupby(['target_commodity', 'quarter'])['log_return'].std().reset_index()
    
    # Pivot to get columns: quarter, vol_wheat, vol_maize, etc.
    vol_pivot = volatility.pivot(index='quarter', columns='target_commodity', values='log_return').reset_index()
    
    # Rename columns
    column_map = {
        'Wheat': 'vol_wheat',
        'Maize': 'vol_maize',
        'Soybeans': 'vol_soybeans',
        'Cotton': 'vol_cotton',
        'Palm Oil': 'vol_palm_oil'
    }
    vol_pivot = vol_pivot.rename(columns=column_map)
    
    # Load Foundation Data (Full)
    print("Loading foundation.csv...")
    foundation = pd.read_csv('foundation.csv')
    
    # List of new volatility columns
    vol_cols = ['vol_wheat', 'vol_maize', 'vol_soybeans', 'vol_cotton', 'vol_palm_oil']
    
    # Remove existing vol columns from foundation if present (to allow update)
    cols_to_drop = [c for c in vol_cols if c in foundation.columns]
    if cols_to_drop:
        print(f"Dropping existing columns from foundation to update: {cols_to_drop}")
        foundation = foundation.drop(columns=cols_to_drop)
    
    # Merge vol_pivot into foundation
    # vol_pivot has: quarter, vol_wheat, vol_maize, vol_soybeans, vol_cotton, vol_palm_oil
    foundation_updated = pd.merge(foundation, vol_pivot, on='quarter', how='left')
    
    # Save back to foundation.csv
    print("Updating foundation.csv with new volatility data...")
    foundation_updated.to_csv('foundation.csv', index=False)
    
    # Prepare data for JS
    # We use the updated foundation data
    # Fill NaN with 0 for JS JSON serialization (or handle otherwise)
    merged = foundation_updated.fillna(0)
    
    # Ensure vol_oil exists
    if 'vol_oil' not in merged.columns:
        print("Warning: vol_oil column missing in foundation.csv, adding dummy.")
        merged['vol_oil'] = 0
    
    output_data = {
        'quarter': merged['quarter'].tolist(),
        'weighted_gdp': merged['weighted_gdp'].tolist(),
        'vol_oil': merged['vol_oil'].tolist(),
        'vol_wheat': merged['vol_wheat'].tolist() if 'vol_wheat' in merged.columns else [0]*len(merged),
        'vol_maize': merged['vol_maize'].tolist() if 'vol_maize' in merged.columns else [0]*len(merged),
        'vol_soybeans': merged['vol_soybeans'].tolist() if 'vol_soybeans' in merged.columns else [0]*len(merged),
        'vol_cotton': merged['vol_cotton'].tolist() if 'vol_cotton' in merged.columns else [0]*len(merged),
        'vol_palm_oil': merged['vol_palm_oil'].tolist() if 'vol_palm_oil' in merged.columns else [0]*len(merged),
    }
    
    # Write to JS file
    js_content = f"const volatility_gdp_data = {json.dumps(output_data, indent=2)};"
    
    with open('volatility_gdp_data.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print("volatility_gdp_data.js updated successfully.")
    
    # Print some stats
    print("Data Preview (Foundation Updated):")
    print(foundation_updated[['quarter', 'weighted_gdp'] + vol_cols].tail())

if __name__ == "__main__":
    main()
