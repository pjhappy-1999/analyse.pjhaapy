import pandas as pd
import numpy as np
from pathlib import Path

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
    # Ensure we have unique daily prices before calculating returns
    df = df.groupby(date_col)[price_col].mean().reset_index()
    
    # Calculate Log Returns: r_t = ln(P_t) - ln(P_{t-1})
    df['log_ret'] = np.log(df[price_col] / df[price_col].shift(1))
    
    # Drop first NaN (caused by shift)
    df = df.dropna(subset=['log_ret'])
    
    # Identify Quarter
    df['quarter'] = df[date_col].dt.to_period('Q').astype(str)
    
    # Calculate Std Dev of Log Returns per Quarter
    # This is the realized volatility for the quarter
    vol = df.groupby('quarter')['log_ret'].std().reset_index()
    vol = vol.rename(columns={'log_ret': f'vol_{name}'})
    
    return vol

def main():
    base_path = Path('.')
    print("Starting foundation table creation...")
    
    # --- 1. Load START.csv (Base Table) ---
    start_csv_path = base_path / "START.csv"
    if not start_csv_path.exists():
        print("Error: START.csv not found.")
        return

    print("Loading START.csv...")
    foundation_df = pd.read_csv(start_csv_path)
    
    # Ensure quarter column exists
    if 'quarter' not in foundation_df.columns:
        print("Error: START.csv missing 'quarter' column")
        return

    # --- 2. Calculate Weighted GDP ---
    print("Calculating Weighted GDP...")
    if 'china_gdp' in foundation_df.columns and 'primary_industry_share' in foundation_df.columns:
        # Weighted GDP = China GDP * (Primary Industry Share / 100)
        foundation_df['weighted_gdp'] = foundation_df['china_gdp'] * (foundation_df['primary_industry_share'] / 100.0)
    else:
        print("Warning: Missing GDP columns in START.csv, weighted_gdp will be NaN")
        foundation_df['weighted_gdp'] = np.nan

    # --- 3. Process Crude Oil Volatility ---
    print("Processing Crude Oil Volatility...")
    try:
        oil_path = base_path / "Crude Oil Prices Daily.xlsx"
        if oil_path.exists():
            oil = pd.read_excel(oil_path)
            date_col = get_date_col(oil)
            
            # Find price column (first numeric non-date column)
            price_col = None
            if date_col:
                for c in oil.columns:
                    if c != date_col and pd.api.types.is_numeric_dtype(oil[c]):
                        price_col = c
                        break
            
            if date_col and price_col:
                oil_vol = calculate_quarterly_volatility(oil, date_col, price_col, "oil")
                # Merge volatility into foundation_df
                foundation_df = pd.merge(foundation_df, oil_vol, on='quarter', how='left')
                print("Merged Oil volatility.")
            else:
                print("Warning: Could not identify date or price column in Oil data.")
        else:
            print("Warning: Crude Oil Prices Daily.xlsx not found.")
    except Exception as e:
        print(f"Error processing Oil: {e}")

    # --- 4. Process WFP Food Volatility ---
    print("Processing Food Volatility...")
    try:
        wfp_path = base_path / "Global WFP Food Prices.csv"
        if wfp_path.exists():
            wfp = pd.read_csv(wfp_path)
            
            # Standardize columns if necessary (though usually they are standard in this dataset)
            # Filter for 'cereals and tubers' as per previous logic
            if 'category' in wfp.columns:
                 wfp = wfp[wfp['category'] == 'cereals and tubers']
            
            if not wfp.empty and 'date' in wfp.columns and 'price_usd' in wfp.columns:
                wfp['date'] = pd.to_datetime(wfp['date'], errors='coerce')
                wfp = wfp.dropna(subset=['date', 'price_usd'])
                
                # Global Daily Average price across all commodities/regions in the category
                daily_food = wfp.groupby('date')['price_usd'].mean().reset_index()
                
                food_vol = calculate_quarterly_volatility(daily_food, 'date', 'price_usd', 'food')
                # Merge volatility into foundation_df
                foundation_df = pd.merge(foundation_df, food_vol, on='quarter', how='left')
                print("Merged Food volatility.")
            else:
                print("Warning: WFP data empty after filtering or missing columns.")
        else:
            print("Warning: Global WFP Food Prices.csv not found.")
    except Exception as e:
        print(f"Error processing Food: {e}")

    # --- 5. Save Foundation Table ---
    output_path = base_path / "foundation.csv"
    foundation_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Success! Foundation table saved to: {output_path.resolve()}")
    print("Columns in foundation table:", foundation_df.columns.tolist())

if __name__ == "__main__":
    main()
