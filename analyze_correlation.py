import pandas as pd
import numpy as np
from scipy.stats import pearsonr
from pathlib import Path

def calculate_p_values(df):
    df = df._get_numeric_data()
    dfcols = df.columns
    pvalues = df.corr(method=lambda x, y: pearsonr(x, y)[1]) - np.eye(len(dfcols))
    return pvalues

def main():
    base_path = Path('.')
    input_path = base_path / "foundation.csv"
    
    if not input_path.exists():
        print("Error: foundation.csv not found.")
        return

    print("Loading foundation.csv...")
    df = pd.read_csv(input_path)
    
    # Select numeric columns relevant for analysis
    # We exclude 'quarter' and potentially other non-numeric or ID columns
    numeric_df = df.select_dtypes(include=[np.number])
    
    # Drop columns that are completely empty
    numeric_df = numeric_df.dropna(axis=1, how='all')
    
    print(f"Analyzing {len(numeric_df.columns)} numeric variables...")

    # 1. Correlation Matrix
    print("Calculating Correlation Matrix...")
    corr_matrix = numeric_df.corr()
    
    # 2. P-value Matrix
    print("Calculating P-values...")
    # Fill NaN with 0 for p-value calculation (or handle properly)
    # Pearsonr requires no NaNs in the pair.
    # We need to loop manually to handle NaNs pairwise like pandas corr does
    p_values = pd.DataFrame(index=numeric_df.columns, columns=numeric_df.columns)
    
    for col1 in numeric_df.columns:
        for col2 in numeric_df.columns:
            if col1 == col2:
                p_values.loc[col1, col2] = 0.0
                continue
            
            # Drop NaNs for the pair
            temp_df = numeric_df[[col1, col2]].dropna()
            
            if len(temp_df) > 1:
                stat, p = pearsonr(temp_df[col1], temp_df[col2])
                p_values.loc[col1, col2] = p
            else:
                p_values.loc[col1, col2] = np.nan

    # Save results
    corr_matrix.to_csv(base_path / "correlation_matrix.csv")
    p_values.to_csv(base_path / "p_values_matrix.csv")
    
    print("Saved 'correlation_matrix.csv' and 'p_values_matrix.csv'.")

    # 3. Focus on Weighted GDP
    target = 'weighted_gdp'
    if target in numeric_df.columns:
        print(f"\nCorrelations with {target}:")
        print(f"{'Variable':<40} | {'Corr':<10} | {'P-value':<10} | {'Significance'}")
        print("-" * 80)
        
        target_corr = corr_matrix[target].sort_values(ascending=False)
        
        for var, corr in target_corr.items():
            if var == target:
                continue
            
            pval = p_values.loc[var, target]
            sig = ""
            if pd.notna(pval):
                if pval < 0.01: sig = "***"
                elif pval < 0.05: sig = "**"
                elif pval < 0.1: sig = "*"
            
            print(f"{var:<40} | {corr:>.4f}    | {pval:>.4f}    | {sig}")
    
    # 4. Focus on Volatility
    print("\nCorrelations between Volatility and GDP:")
    vol_cols = [c for c in numeric_df.columns if 'vol_' in c]
    for vol in vol_cols:
        if vol in numeric_df.columns and target in numeric_df.columns:
            corr = corr_matrix.loc[vol, target]
            pval = p_values.loc[vol, target]
            sig = ""
            if pd.notna(pval):
                if pval < 0.01: sig = "***"
                elif pval < 0.05: sig = "**"
                elif pval < 0.1: sig = "*"
            print(f"{vol:<40} vs {target:<15}: Corr={corr:.4f}, P={pval:.4f} {sig}")

if __name__ == "__main__":
    main()
