
import pandas as pd
import numpy as np

def check_correlations():
    df = pd.read_csv("START.csv")
    
    # Ensure primary_weighted_gdp exists
    if "primary_industry_share" in df.columns and "china_gdp" in df.columns:
        df["primary_weighted_gdp"] = df["china_gdp"] * df["primary_industry_share"] / 100
    
    commodities = [
        "wfp_wheat_price_usd_mean",
        "wfp_maize_price_usd_mean",
        "wfp_soybeans_price_usd_mean",
        "wfp_cotton_price_usd_mean",
        "wfp_palm_oil_price_usd_mean",
        "crude_oil_price"
    ]
    
    # 1. Level Correlation with Lags
    print("--- Correlation of Levels (Lagged Commodities) ---")
    for comm in commodities:
        if comm not in df.columns: continue
        corrs = []
        for lag in range(0, 9): # 0 to 8 quarters (2 years)
            # We lag the COMMODITY price. Price(t-k) vs GDP(t)
            # Because Price affects GDP (Assumption)
            shifted = df[comm].shift(lag)
            c = df["primary_weighted_gdp"].corr(shifted)
            corrs.append(f"Lag{lag}: {c:.3f}")
        print(f"{comm}: {', '.join(corrs)}")
        
    # 2. Growth Correlation
    print("\n--- Correlation of YoY Growth ---")
    df_growth = df.copy()
    for col in ["primary_weighted_gdp"] + commodities:
        if col in df.columns:
            # YoY growth (4 quarters)
            df_growth[col] = df[col].pct_change(4)
            
    for comm in commodities:
        if comm not in df_growth.columns: continue
        # Lagged Growth
        corrs = []
        for lag in range(0, 5):
            shifted = df_growth[comm].shift(lag)
            c = df_growth["primary_weighted_gdp"].corr(shifted)
            corrs.append(f"Lag{lag}: {c:.3f}")
    # 3. Log Correlation
    print("\n--- Correlation of Log Levels ---")
    df_log = df.copy()
    for col in ["primary_weighted_gdp"] + commodities:
        if col in df_log.columns:
            # Handle zeros or negative? Prices are positive.
            # GDP Weight might be negative if pull is negative? 
            # Check descriptive stats or handle error.
            try:
                df_log[col] = np.log(df[col])
            except:
                pass
            
    for comm in commodities:
        if comm not in df_log.columns: continue
        corrs = []
        for lag in range(0, 5):
            shifted = df_log[comm].shift(lag)
            c = df_log["primary_weighted_gdp"].corr(shifted)
            corrs.append(f"Lag{lag}: {c:.3f}")
        print(f"{comm}: {', '.join(corrs)}")

    # 4. Volatility Correlation (Log Difference)
    print("\n--- Correlation of Log Volatility (Quarterly) ---")
    df_vol = df.copy()
    for col in ["primary_weighted_gdp"] + commodities:
        if col in df_vol.columns:
            # Log first, then diff
            try:
                # Add small epsilon to avoid log(0) if any
                s = df[col]
                s = s.where(s > 0, np.nan)
                df_vol[col] = np.log(s).diff()
            except:
                pass
            
    for comm in commodities:
        if comm not in df_vol.columns: continue
        corrs = []
        for lag in range(0, 5):
            shifted = df_vol[comm].shift(lag)
            # Correlation between Vol(GDP)_t and Vol(Price)_{t-lag}
            c = df_vol["primary_weighted_gdp"].corr(shifted)
            corrs.append(f"Lag{lag}: {c:.3f}")
        print(f"{comm}: {', '.join(corrs)}")

if __name__ == "__main__":
    check_correlations()
