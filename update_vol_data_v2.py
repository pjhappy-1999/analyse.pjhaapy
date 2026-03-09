import pandas as pd
import numpy as np
import json
import re

# 1. Load WFP Data
print("Loading WFP Data...")
df = pd.read_csv('Global WFP Food Prices.csv', low_memory=False)

# 2. Define Commodities and Units
# Mapping: Target Name -> (WFP Name, Unit)
commodities = {
    'vol_wheat': ('Wheat', 'KG'),
    'vol_maize': ('Maize', 'KG'),
    'vol_soybeans': ('Soybeans', 'KG'),
    'vol_cotton': ('Oil (cotton)', 'L'), # Proxy for Cotton
    'vol_palm_oil': ('Oil (palm)', 'L')
}

# 3. Process Data
print("Processing Data...")
# Filter for relevant commodities
wfp_names = [v[0] for v in commodities.values()]
df = df[df['commodity'].isin(wfp_names)]

# Convert date
df['date'] = pd.to_datetime(df['date'])

# Dictionary to store quarterly volatility series
vol_series = {k: {} for k in commodities.keys()}

for key, (wfp_name, unit) in commodities.items():
    print(f"Processing {wfp_name} ({unit})...")
    
    # Filter specific commodity and unit
    subset = df[(df['commodity'] == wfp_name) & (df['unit'] == unit)].copy()
    
    # Aggregate to Global Monthly Price (mean of all markets)
    # We assume 'price_usd' is the correct column
    monthly_prices = subset.groupby('date')['price_usd'].mean().reset_index()
    monthly_prices = monthly_prices.sort_values('date')
    
    # Calculate Log Returns
    # r_t = ln(P_t / P_{t-1})
    monthly_prices['price_shift'] = monthly_prices['price_usd'].shift(1)
    monthly_prices['log_return'] = np.log(monthly_prices['price_usd'] / monthly_prices['price_shift'])
    
    # Assign Quarter
    # format: YYYYQX
    monthly_prices['quarter'] = monthly_prices['date'].dt.to_period('Q').astype(str)
    
    # Calculate Quarterly Volatility (Std Dev of Log Returns)
    # We need at least 2 data points to calculate std dev
    q_vol = monthly_prices.groupby('quarter')['log_return'].std()
    
    # Store in dict
    for q, vol in q_vol.items():
        if not np.isnan(vol):
            vol_series[key][q] = vol

# 4. Load Existing JS Data
print("Loading JS Data...")
with open('volatility_gdp_data.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract JSON
# Assuming format: var volatilityData = { ... };
match = re.search(r'var volatilityData = ({[\s\S]*});', content)
if not match:
    print("Error: Could not find JSON object in JS file.")
    exit(1)

json_str = match.group(1)
try:
    data = json.loads(json_str)
except json.JSONDecodeError as e:
    print(f"JSON Parse Error: {e}")
    exit(1)

# 5. Merge Data
if 'series' not in data:
    data['series'] = {}

quarters = data['quarters']
print(f"Aligning to {len(quarters)} quarters...")

for key in commodities.keys():
    new_data = []
    for q in quarters:
        # q is like "2005Q1"
        val = vol_series[key].get(q, None)
        new_data.append(val)
    
    # CORRECTED: Store inside 'series' object
    data['series'][key] = new_data
    print(f"Added {key} to series: {len(new_data)} points")

# 6. Write Back
print("Saving JS Data...")
new_json_str = json.dumps(data, indent=4)
new_content = f"var volatilityData = {new_json_str};\n"

with open('volatility_gdp_data.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Done.")
