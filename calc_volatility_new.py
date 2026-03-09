import pandas as pd
import numpy as np
from pathlib import Path
import json

def get_date_col(df):
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    for col in df.columns:
        if "date" in col.lower() or "time" in col.lower():
            try:
                converted = pd.to_datetime(df[col], errors='coerce')
                if converted.notna().sum() > 0:
                    df[col] = converted
                    return col
            except:
                continue
    return None

def calculate_quarterly_volatility(df, date_col, price_col, name):
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    
    # Handle duplicates by date (mean price)
    df = df.groupby(date_col)[price_col].mean().reset_index()
    
    # Calculate Log Returns: r_t = ln(P_t) - ln(P_{t-1})
    df['log_ret'] = np.log(df[price_col] / df[price_col].shift(1))
    
    # Drop first NaN
    df = df.dropna(subset=['log_ret'])
    
    # Identify Quarter
    df['quarter'] = df[date_col].dt.to_period('Q').astype(str)
    
    # Calculate Std Dev of Log Returns per Quarter
    vol = df.groupby('quarter')['log_ret'].std().reset_index()
    vol = vol.rename(columns={'log_ret': f'vol_{name}'})
    
    return vol

def main():
    base_path = Path('.')
    
    # --- 1. Load START.csv for GDP and Time Frame ---
    print("Loading START.csv...")
    try:
        start_df = pd.read_csv(base_path / "START.csv")
        # Ensure quarter column exists
        if 'quarter' not in start_df.columns:
            print("START.csv missing 'quarter' column")
            return
            
        # Calculate Weighted GDP
        # Check columns
        if 'china_gdp' in start_df.columns and 'primary_industry_share' in start_df.columns:
             start_df['weighted_gdp'] = start_df['china_gdp'] * (start_df['primary_industry_share'] / 100.0)
        else:
            print("Missing GDP columns in START.csv, using placeholders")
            start_df['weighted_gdp'] = np.nan
            
        final_df = start_df[['quarter', 'weighted_gdp']].copy()
    except Exception as e:
        print(f"Error loading START.csv: {e}")
        return

    # --- 2. Process Crude Oil ---
    print("Processing Crude Oil...")
    try:
        oil = pd.read_excel(base_path / "Crude Oil Prices Daily.xlsx")
        date_col = get_date_col(oil)
        if date_col:
            price_cols = [c for c in oil.columns if c != date_col]
            price_col = None
            for c in price_cols:
                if pd.api.types.is_numeric_dtype(oil[c]):
                    price_col = c
                    break
            
            if price_col:
                oil_vol = calculate_quarterly_volatility(oil, date_col, price_col, "oil")
                final_df = pd.merge(final_df, oil_vol, on='quarter', how='left')
            else:
                print("No numeric price column found in Oil data")
    except Exception as e:
        print(f"Error processing Oil: {e}")

    # --- 3. Process WFP Food ---
    print("Processing WFP Food...")
    try:
        wfp = pd.read_csv(base_path / "Global WFP Food Prices.csv")
        # Filter for Cereals and Tubers
        # Note: 'category' column might be capitalized differently, check unique values if needed
        # But based on build_start.py, it is "cereals and tubers"
        wfp = wfp[wfp['category'] == 'cereals and tubers']
        
        if not wfp.empty:
            wfp['date'] = pd.to_datetime(wfp['date'], errors='coerce')
            wfp = wfp.dropna(subset=['date', 'price_usd'])
            
            # Global Daily Average
            daily_food = wfp.groupby('date')['price_usd'].mean().reset_index()
            
            food_vol = calculate_quarterly_volatility(daily_food, 'date', 'price_usd', 'food')
            final_df = pd.merge(final_df, food_vol, on='quarter', how='left')
        else:
            print("WFP data empty after filtering")
    except Exception as e:
        print(f"Error processing Food: {e}")

    # --- 4. Output ---
    final_df = final_df.sort_values('quarter')
    
    # Fill NaN with null for JSON
    output = {
        "quarters": final_df['quarter'].tolist(),
        "series": {
            "weighted_gdp": final_df['weighted_gdp'].where(final_df['weighted_gdp'].notna(), None).tolist(),
            "vol_oil": final_df['vol_oil'].where(final_df['vol_oil'].notna(), None).tolist() if 'vol_oil' in final_df.columns else [],
            "vol_food": final_df['vol_food'].where(final_df['vol_food'].notna(), None).tolist() if 'vol_food' in final_df.columns else []
        }
    }
    
    with open('volatility_gdp_data.js', 'w', encoding='utf-8') as f:
        f.write("var volatilityData = ")
        json.dump(output, f, ensure_ascii=False)
        f.write(";")
    
    print("Done! Saved to volatility_gdp_data.js")

if __name__ == "__main__":
    main()
