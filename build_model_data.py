import pandas as pd
import numpy as np
from pathlib import Path

# --- Configuration ---
base_path = Path(r"c:\Users\Administrator\Desktop\lunwenxiangguan\lunwen")
input_file = base_path / "START.csv"
output_file = base_path / "START_prediction_dataset.csv"
output_file_selected_global = base_path / "START_prediction_dataset_selected_global.csv"
output_file_selected_per_commodity = base_path / "START_prediction_dataset_selected_per_commodity.csv"

# Columns to process (Target + Exogenous)
target_col = "primary_weighted_gdp"
# Map original names to cleaner ones if needed, or use directly
# "wfp_soybeans_price_usd_mean", "wfp_wheat_price_usd_mean", etc.
exog_cols = [
    "crude_oil_price",
    "wfp_wheat_price_usd_mean",
    "wfp_maize_price_usd_mean",
    "wfp_soybeans_price_usd_mean",
    "wfp_cotton_price_usd_mean",
    "wfp_palm_oil_price_usd_mean",
    "exchange_rate_cny_usd" # If available
]

def _is_number(x):
    try:
        return x is not None and np.isfinite(float(x))
    except Exception:
        return False

def _best_lag_by_rule(corrs, pvals, alpha=0.05):
    best = {"lag": 0, "corr": 0.0, "pval": None, "significant": False}
    best_sig_abs = -1.0
    best_abs = -1.0
    for k in range(9):
        c = corrs[k] if corrs is not None and len(corrs) > k else 0.0
        if not _is_number(c):
            c = 0.0
        p = pvals[k] if pvals is not None and len(pvals) > k else None
        sig = _is_number(p) and float(p) < alpha
        abs_c = float(abs(float(c)))
        if sig and abs_c > best_sig_abs:
            best_sig_abs = abs_c
            best = {"lag": int(k), "corr": float(c), "pval": float(p), "significant": True}
        if (not sig) and abs_c > best_abs:
            best_abs = abs_c
            if not best["significant"]:
                best = {"lag": int(k), "corr": float(c), "pval": float(p) if _is_number(p) else None, "significant": False}
    if best_sig_abs < 0 and best_abs >= 0:
        best = {"lag": best["lag"], "corr": best["corr"], "pval": best["pval"], "significant": False}
    return best

def _read_lag_table(path: Path):
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if "variable" not in df.columns:
        return None
    df = df.set_index("variable")
    return df

def _method_recommendations(base_path: Path, variables):
    df_delta = _read_lag_table(base_path / "START_lagged_correlations.csv")
    df_ewma = _read_lag_table(base_path / "START_lagged_correlations_ewma.csv")
    df_shock = _read_lag_table(base_path / "START_lagged_correlations_shock.csv")
    known = set()
    for d in (df_delta, df_ewma, df_shock):
        if d is not None:
            known |= set(d.index.tolist())
    if known:
        variables = [v for v in variables if v in known]

    def pick_from_df(df, var):
        if df is None or var not in df.index:
            return {"lag": 0, "corr": 0.0, "pval": None, "significant": False}
        corrs = []
        pvals = []
        for k in range(9):
            c = df.loc[var].get(f"lag_{k}", 0.0)
            p = df.loc[var].get(f"pval_{k}", None)
            corrs.append(float(c) if _is_number(c) else 0.0)
            pvals.append(float(p) if _is_number(p) else None)
        return _best_lag_by_rule(corrs, pvals)

    methods = {
        "dlog": {"name": "ΔLog", "df": df_delta},
        "ewma": {"name": "EWMA", "df": df_ewma},
        "shock": {"name": "预白化冲击", "df": df_shock},
    }

    per_method = {}
    for key, meta in methods.items():
        rows = []
        for var in variables:
            best = pick_from_df(meta["df"], var)
            rows.append({"variable": var, **best})
        per_method[key] = rows

    def method_score(rows):
        sig_rows = [r for r in rows if r.get("significant")]
        sig_count = int(len(sig_rows))
        sig_avg_abs = float(np.mean([abs(r["corr"]) for r in sig_rows])) if sig_rows else 0.0
        overall_avg_abs = float(np.mean([abs(r["corr"]) for r in rows])) if rows else 0.0
        return (sig_count, sig_avg_abs, overall_avg_abs)

    winner_key = max(per_method.keys(), key=lambda k: method_score(per_method[k]))
    global_selected = {r["variable"]: {"method": winner_key, **r} for r in per_method[winner_key]}

    per_commodity_selected = {}
    for var in variables:
        candidates = []
        for m in per_method.keys():
            row = next((x for x in per_method[m] if x["variable"] == var), None)
            if row is None:
                continue
            candidates.append({"method": m, **row})
        sig_candidates = [c for c in candidates if c.get("significant")]
        pool = sig_candidates if sig_candidates else candidates
        best = max(pool, key=lambda x: abs(x.get("corr", 0.0)) if _is_number(x.get("corr")) else 0.0) if pool else {"method": winner_key, "lag": 0, "corr": 0.0, "pval": None, "significant": False}
        per_commodity_selected[var] = best

    return {
        "winner_method": winner_key,
        "global": global_selected,
        "per_commodity": per_commodity_selected,
    }

def _prewhiten_shock(series: pd.Series, alpha=0.15):
    r = series.astype(float)
    r_l1 = r.shift(1)
    mask = r.notna() & r_l1.notna()
    if int(mask.sum()) >= 10:
        num = float((r[mask] * r_l1[mask]).sum())
        den = float((r_l1[mask] * r_l1[mask]).sum())
        phi = num / den if den != 0 else 0.0
    else:
        phi = 0.0
    e = r - phi * r_l1
    ewma_sigma = e.pow(2).ewm(alpha=alpha, adjust=False).mean().pow(0.5)
    s = e / ewma_sigma
    return s

def _build_selected_dataset(ret_df: pd.DataFrame, y_name: str, selection: dict, alpha=0.15):
    if y_name not in ret_df.columns:
        return None
    y = ret_df[y_name]
    features = pd.DataFrame(index=ret_df.index)
    for lag in [1, 2, 3, 4]:
        features[f"y_lag{lag}"] = y.shift(lag)

    for var, rec in selection.items():
        method = rec.get("method", "dlog")
        lag = int(rec.get("lag", 0))
        if var not in ret_df.columns:
            continue
        base = ret_df[var]
        if method == "ewma":
            x = base.ewm(alpha=alpha, adjust=False).mean()
        elif method == "shock":
            x = _prewhiten_shock(base, alpha=alpha)
        else:
            x = base
        features[f"x_{var}_{method}_lag{lag}"] = x.shift(lag)

    q = pd.Series(features.index.quarter, index=features.index)
    dummies = pd.get_dummies(q, prefix="Q", drop_first=True)
    features = pd.concat([features, dummies], axis=1)

    out = pd.concat([y.rename("y"), features], axis=1).dropna()
    return out

def create_prediction_dataset():
    print("Loading data...")
    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        return

    df = pd.read_csv(input_file)
    
    # Ensure 'date' or 'quarter' is handled
    # START.csv has a 'quarter' column like "2005Q1", "2005Q2"
    if "quarter" in df.columns:
        def parse_quarter(q_str):
            try:
                # Format: 2005Q1
                year = int(q_str[:4])
                q = int(q_str[-1])
                month = (q - 1) * 3 + 1
                return pd.Timestamp(year=year, month=month, day=1)
            except:
                return pd.NaT
            
        df["date"] = df["quarter"].apply(parse_quarter)
        df = df.dropna(subset=["date"])
        df.set_index("date", inplace=True)
    elif "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
    else:
        print("Error: No 'quarter' or 'date' column found.")
        return

    # 1. Filter relevant columns
    # Check if exchange rate exists, if not, remove from list
    available_cols = [col for col in exog_cols if col in df.columns]
    
    # Check if target column exists
    # If primary_weighted_gdp is missing, we need to construct it
    if target_col not in df.columns:
        # Check if we have components to build it: china_gdp * primary_industry_share / 100
        if "china_gdp" in df.columns and "primary_industry_share" in df.columns:
            print(f"Constructing {target_col} from china_gdp and primary_industry_share...")
            df[target_col] = df["china_gdp"] * df["primary_industry_share"] / 100
        else:
            print(f"Error: Target column '{target_col}' not found and cannot be constructed.")
            print("Available columns:", df.columns.tolist())
            return

    working_df = df[[target_col] + available_cols].copy()
    
    # 2. Log Transformation (Stabilize variance)
    # We use log(X) for all price/GDP variables
    log_df = np.log(working_df)
    log_df.columns = [f"log_{col}" for col in working_df.columns]
    
    # 3. Differencing (Stationarity)
    # Calculate Quarter-over-Quarter Growth (approx. percentage change)
    # This removes the trend component, making data stationary for regression
    diff_df = log_df.diff()
    diff_df.columns = [f"diff_{col}" for col in log_df.columns]
    
    # Drop the first row (NaN due to differencing)
    diff_df.dropna(inplace=True)
    
    # 4. Feature Engineering
    
    # 4.1 Lagged Features (Autoregressive & Exogenous Lags)
    # Based on our analysis, Lags 1-4 are crucial.
    # We will create lags for ALL variables (including target)
    lags = [1, 2, 3, 4]
    lagged_data = diff_df.copy()
    
    for col in diff_df.columns:
        for lag in lags:
            lagged_data[f"{col}_lag{lag}"] = diff_df[col].shift(lag)
            
    # 4.2 Rolling Statistics (Volatility/Trend)
    # Calculate 4-quarter rolling mean and standard deviation (volatility)
    # We apply this to the DIFFERENCED data to capture volatility regimes
    windows = [4] # 1 year window
    for col in diff_df.columns:
        for window in windows:
            lagged_data[f"{col}_roll_mean_{window}"] = diff_df[col].rolling(window=window).mean().shift(1) # Shift 1 to avoid data leakage!
            lagged_data[f"{col}_roll_std_{window}"] = diff_df[col].rolling(window=window).std().shift(1)

    # 4.3 Seasonality (Quarter Dummies)
    # Add dummy variables for quarters (Q1, Q2, Q3) - Q4 is reference
    # Using index from original df (aligned)
    # Note: diff_df has fewer rows, need to align index
    lagged_data["quarter"] = lagged_data.index.quarter
    dummies = pd.get_dummies(lagged_data["quarter"], prefix="Q", drop_first=True)
    lagged_data = pd.concat([lagged_data, dummies], axis=1)
    lagged_data.drop("quarter", axis=1, inplace=True) # Drop raw quarter column

    # 5. Interaction Terms (Optional but powerful)
    # Example: Interaction between Oil Price Volatility and Crop Price Volatility
    # (Energy costs often drive agricultural costs)
    # diff_log_crude * diff_log_soybeans
    oil_col = "diff_log_crude_oil_price"
    if oil_col in lagged_data.columns:
        for col in available_cols:
            target_var = f"diff_log_{col}"
            if target_var in lagged_data.columns and target_var != oil_col:
                lagged_data[f"inter_{oil_col}_x_{target_var}"] = lagged_data[oil_col] * lagged_data[target_var]

    # 6. Final Cleanup
    # Drop NaN rows generated by lagging and rolling
    # Max lag is 4, max rolling is 4. So we lose first 4-5 rows.
    final_df = lagged_data.dropna()
    
    print(f"Original shape: {df.shape}")
    print(f"Processed shape: {final_df.shape}")
    print(f"Features created: {len(final_df.columns)}")
    
    # Save
    final_df.to_csv(output_file)
    print(f"Saved prediction dataset to: {output_file}")

    available_exog = [c for c in available_cols if c != target_col]
    corr_vars = [c for c in available_exog if c in df.columns]
    try:
        recs = _method_recommendations(base_path, corr_vars)
        ret_cols = [target_col] + corr_vars
        ret_df = pd.DataFrame(index=diff_df.index)
        for c in ret_cols:
            nm = f"diff_log_{c}"
            if nm in diff_df.columns:
                ret_df[c] = diff_df[nm]

        ds_global = _build_selected_dataset(ret_df, target_col, recs["global"])
        if ds_global is not None and not ds_global.empty:
            ds_global.to_csv(output_file_selected_global)
            print(f"Saved correlation-selected dataset (global method={recs['winner_method']}) to: {output_file_selected_global}")

        ds_pc = _build_selected_dataset(ret_df, target_col, recs["per_commodity"])
        if ds_pc is not None and not ds_pc.empty:
            ds_pc.to_csv(output_file_selected_per_commodity)
            print(f"Saved correlation-selected dataset (per commodity) to: {output_file_selected_per_commodity}")
    except Exception as e:
        print(f"Skip correlation-selected datasets due to error: {e}")
    
    # 7. Quick Correlation Report for the Target
    target_diff_col = f"diff_log_{target_col}"
    correlations = final_df.corr()[target_diff_col].sort_values(ascending=False)
    
    # Remove self-correlation (correlation with itself is 1.0)
    if target_diff_col in correlations:
        correlations = correlations.drop(target_diff_col)

    print("\n--- Top 10 Positive Predictors for GDP Growth ---")
    top_pos = correlations.head(10)
    print(top_pos)
    print("\n--- Top 10 Negative Predictors for GDP Growth ---")
    top_neg = correlations.tail(10)
    print(top_neg)
    
    # 8. Export Top Predictors to JSON for Web Display
    import json
    
    # Helper to clean variable names for display
    def clean_var_name(name):
        name = name.replace("diff_log_", "ΔLog ")
        name = name.replace("wfp_", "").replace("_price_usd_mean", "")
        name = name.replace("_lag", " (Lag ").replace("_roll_mean_", " (Roll Mean ").replace("_roll_std_", " (Roll Volatility ")
        name = name.replace("inter_", "Interaction: ")
        name = name.replace("_x_", " x ")
        name = name.replace("primary_weighted_gdp", "GDP")
        name = name.replace("crude_oil_price", "Crude Oil")
        
        # Close parenthesis if opened
        if "(" in name and not name.endswith(")"):
            name += ")"
            
        return name

    top_predictors = {
        "positive": [{"name": clean_var_name(k), "value": round(v, 3), "original_name": k} for k, v in top_pos.items()],
        "negative": [{"name": clean_var_name(k), "value": round(v, 3), "original_name": k} for k, v in top_neg.sort_values(ascending=True).items()]
    }
    
    json_path = base_path / "START_top_predictors.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(top_predictors, f, ensure_ascii=False, indent=2)
    print(f"Saved top predictors to: {json_path}")

    selected_features = []
    for item in top_predictors["positive"] + top_predictors["negative"]:
        original_name = item.get("original_name")
        if not original_name:
            continue
        if "primary_weighted_gdp" in original_name:
            continue
        if "crude_oil" in original_name:
            continue
        selected_features.append(original_name)
    selected_features = list(dict.fromkeys(selected_features))

    model_df = final_df[[target_diff_col] + [c for c in selected_features if c in final_df.columns]].dropna().copy()
    if model_df.shape[0] >= 10 and model_df.shape[1] >= 3:
        X = model_df.drop(columns=[target_diff_col]).to_numpy(dtype=float)
        y = model_df[target_diff_col].to_numpy(dtype=float)
        X1 = np.column_stack([np.ones(X.shape[0]), X])
        beta, _, _, _ = np.linalg.lstsq(X1, y, rcond=None)
        intercept = float(beta[0])
        coef = beta[1:].astype(float)
        y_pred = X @ coef + intercept

        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = float("nan") if ss_tot == 0 else float(1 - ss_res / ss_tot)
        rmse = float(np.sqrt(np.mean((y - y_pred) ** 2)))

        X_mean = np.mean(X, axis=0)
        X_std = np.std(X, axis=0, ddof=0)
        y_mean = float(np.mean(y))
        y_std = float(np.std(y, ddof=0))
        Xs = (X - X_mean) / np.where(X_std == 0, 1, X_std)
        ys = (y - y_mean) / (y_std if y_std != 0 else 1)
        beta_std, _, _, _ = np.linalg.lstsq(Xs, ys, rcond=None)
        coef_std = beta_std.astype(float)

        quarters_labels = [f"{d.year}Q{((d.month - 1) // 3) + 1}" for d in model_df.index.to_pydatetime()]
        feature_labels = [clean_var_name(c) for c in model_df.drop(columns=[target_diff_col]).columns.tolist()]

        multivar_model = {
            "target": clean_var_name(target_diff_col),
            "features": feature_labels,
            "features_original": model_df.drop(columns=[target_diff_col]).columns.tolist(),
            "coef": [float(v) for v in coef],
            "coef_std": [float(v) for v in coef_std],
            "intercept": intercept,
            "r2": r2,
            "rmse": rmse,
            "n": int(model_df.shape[0]),
            "series": {
                "quarters": quarters_labels,
                "actual": [float(v) for v in y],
                "pred": [float(v) for v in y_pred],
            }
        }
    else:
        multivar_model = None
    
    # Also append to JS file for easy loading
    js_path = base_path / "start_echarts_data.js"
    if js_path.exists():
        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()
        
        lines = js_content.splitlines()
        lines = [L for L in lines if not L.strip().startswith("var topPredictors =") and not L.strip().startswith("var multivarModel =")]
        new_content = "\n".join(lines)
        
        js_data = f"\nvar topPredictors = {json.dumps(top_predictors, ensure_ascii=False)};"
        if multivar_model is not None:
            js_data += f"\nvar multivarModel = {json.dumps(multivar_model, ensure_ascii=False)};"
        try:
            dl_results = {}
            commodities = [
                "wfp_wheat_price_usd_mean",
                "wfp_maize_price_usd_mean",
                "wfp_soybeans_price_usd_mean",
                "wfp_cotton_price_usd_mean",
                "wfp_palm_oil_price_usd_mean",
            ]
            for c in commodities:
                lag_feats = [f"diff_log_{c}_lag{k}" for k in [1, 2, 3, 4] if f"diff_log_{c}_lag{k}" in final_df.columns]
                aux = []
                for q in ["Q_2", "Q_3"]:
                    if q in final_df.columns:
                        aux.append(q)
                cols = [target_diff_col] + lag_feats + aux
                sub = final_df[cols].dropna()
                if sub.shape[0] >= 10 and len(lag_feats) > 0:
                    X = sub[lag_feats + aux].to_numpy(dtype=float)
                    y = sub[target_diff_col].to_numpy(dtype=float)
                    X1 = np.column_stack([np.ones(X.shape[0]), X])
                    beta, _, _, _ = np.linalg.lstsq(X1, y, rcond=None)
                    intercept = float(beta[0])
                    coef = beta[1:].astype(float)
                    y_pred = X @ coef + intercept
                    ss_res = float(np.sum((y - y_pred) ** 2))
                    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
                    r2m = float("nan") if ss_tot == 0 else float(1 - ss_res / ss_tot)
                    rmsem = float(np.sqrt(np.mean((y - y_pred) ** 2)))
                    r_multi = float(np.corrcoef(y, y_pred)[0, 1]) if np.std(y) > 0 and np.std(y_pred) > 0 else float("nan")
                else:
                    r2m = float("nan")
                    rmsem = float("nan")
                    r_multi = float("nan")
                    intercept = float("nan")
                    coef = np.array([], dtype=float)
                r0 = None
                base_col = f"diff_log_{c}"
                if base_col in final_df.columns:
                    r0 = final_df[[target_diff_col, base_col]].dropna().corr().iloc[0, 1]
                best_lag = None
                best_r = None
                for k in [0, 1, 2, 3, 4]:
                    cn = base_col if k == 0 else f"{base_col}_lag{k}"
                    if cn in final_df.columns:
                        rv = final_df[[target_diff_col, cn]].dropna().corr().iloc[0, 1]
                        if best_r is None or abs(rv) > abs(best_r):
                            best_r = float(rv)
                            best_lag = int(k)
                r_roll = None
                roll_col = f"{base_col}_roll_mean_4"
                if roll_col in final_df.columns:
                    r_roll = final_df[[target_diff_col, roll_col]].dropna().corr().iloc[0, 1]
                coef_map = {}
                for i, name in enumerate(lag_feats + aux):
                    coef_map[name] = float(coef[i]) if i < len(coef) else None
                dl_results[c] = {
                    "name": clean_var_name(base_col),
                    "r_multi": r_multi,
                    "r2_multi": r2m,
                    "rmse_multi": rmsem,
                    "n_multi": int(sub.shape[0]) if 'sub' in locals() else 0,
                    "intercept": intercept,
                    "coef": coef_map,
                    "r0": float(r0) if r0 is not None else None,
                    "best_lag": best_lag,
                    "r_best_lag": best_r,
                    "r_roll_mean_4": float(r_roll) if r_roll is not None else None,
                }
        except Exception as e:
            dl_results = {}
        if dl_results:
            js_data += f"\nvar distLagResults = {json.dumps(dl_results, ensure_ascii=False)};"
        new_content += js_data
        
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated top predictors in: {js_path}")

if __name__ == "__main__":
    create_prediction_dataset()
