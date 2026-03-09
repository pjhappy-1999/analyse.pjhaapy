import pandas as pd
import numpy as np
from scipy.stats import pearsonr
from pathlib import Path
import json

def main():
    base_path = Path('.')
    input_path = base_path / "foundation.csv"
    js_path = base_path / "volatility_gdp_data.js"
    
    if not input_path.exists():
        print("Error: foundation.csv not found.")
        return

    df = pd.read_csv(input_path)
    
    # Define pairs
    pairs = [
        ("vol_oil", "weighted_gdp", "原油波动率 (Oil Vol)"),
        ("vol_food", "weighted_gdp", "粮食波动率 (Food Vol)")
    ]
    
    stats = []
    
    for col1, col2, name in pairs:
        if col1 in df.columns and col2 in df.columns:
            temp = df[[col1, col2]].dropna()
            if len(temp) > 1:
                r, p = pearsonr(temp[col1], temp[col2])
                stats.append({
                    "name": name,
                    "r": r,
                    "p": p,
                    "n": len(temp)
                })
            else:
                stats.append({"name": name, "r": None, "p": None, "n": 0})
    
    # Create JS content
    js_content = f"\nvar volatilityStats = {json.dumps(stats, indent=4)};\n"
    
    # Append to JS file
    if js_path.exists():
        with open(js_path, "a", encoding="utf-8") as f:
            f.write(js_content)
        print(f"Appended stats to {js_path}")
    else:
        print(f"Error: {js_path} not found.")

if __name__ == "__main__":
    main()
