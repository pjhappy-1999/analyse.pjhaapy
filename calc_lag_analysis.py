import pandas as pd
import numpy as np
import json

def main():
    print("Loading foundation.csv...")
    df = pd.read_csv('foundation.csv')
    
    # Calculate GDP Growth (Log Difference)
    # Ensure sorted by quarter
    df['quarter'] = pd.to_datetime(df['quarter'].str.replace('Q1', '-03-31').str.replace('Q2', '-06-30').str.replace('Q3', '-09-30').str.replace('Q4', '-12-31'))
    df = df.sort_values('quarter')
    
    # Re-convert quarter to string for output if needed, but index is now datetime
    # We will use the original quarter column for merging back or just index alignment
    
    # Calculate Log GDP Growth: ln(GDP_t) - ln(GDP_{t-1})
    # Note: weighted_gdp might have NaN
    df['log_gdp'] = np.log(df['weighted_gdp'])
    df['gdp_growth'] = df['log_gdp'].diff()
    
    # Define volatility columns
    vol_cols = ['vol_oil', 'vol_wheat', 'vol_maize', 'vol_soybeans', 'vol_cotton', 'vol_palm_oil']
    
    # Lags to analyze: 0 to 8 quarters (0 to 2 years)
    lags = list(range(9))
    
    # Calculate Lag Correlations...
    results = {
        'lags': lags,
        'series': {}
    }
    
    print("Calculating Lag Correlations...")
    
    analysis_summary = []
    
    for col in vol_cols:
        correlations = []
        # Human readable name key for JSON series
        series_key = col.replace('vol_', '')
        
        # Track best lag
        best_lag = -1
        max_abs_corr = -1
        best_corr = 0
        
        for k in lags:
            # Shift volatility by k quarters forward to align with current GDP
            # i.e., Corr(GDP_t, Vol_{t-k})
            # To do this, we shift Volatility DOWN by k (so Vol at t-k aligns with GDP at t)
            
            # Series for correlation
            series_gdp = df['gdp_growth']
            series_vol = df[col].shift(k) # Shift forward by k: value at t-k moves to t
            
            # Calculate correlation
            # Pandas handles NaN automatically
            corr = series_gdp.corr(series_vol)
            
            if pd.isna(corr):
                corr = 0
            
            correlations.append(round(corr, 4))
            
            # Check for best lag
            if abs(corr) > max_abs_corr:
                max_abs_corr = abs(corr)
                best_lag = k
                best_corr = corr
            
        results['series'][series_key] = correlations
        
        # Add to summary
        analysis_summary.append({
            'commodity': series_key,
            'best_lag': best_lag,
            'correlation': round(best_corr, 4)
        })
        
        print(f"{series_key}: Best Lag={best_lag} (Corr={best_corr:.4f})")

    results['analysis'] = analysis_summary

    # Output to JS
    js_content = f"const volatility_lag_data = {json.dumps(results, indent=2)};"
    
    with open('volatility_lag_data.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
        
    print("volatility_lag_data.js generated successfully.")

if __name__ == "__main__":
    main()
