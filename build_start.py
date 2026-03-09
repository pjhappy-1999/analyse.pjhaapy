import pandas as pd
import numpy as np
from pathlib import Path
from functools import reduce
import json
import math


def load_crude_oil_quarterly(base_path: Path) -> pd.DataFrame:
    oil_path = base_path / "Crude Oil Prices Daily.xlsx"
    oil = pd.read_excel(oil_path)

    date_col = None
    for col in oil.columns:
        if pd.api.types.is_datetime64_any_dtype(oil[col]):
            date_col = col
            break

    if date_col is None:
        for col in oil.columns:
            converted = pd.to_datetime(oil[col], errors="coerce")
            if converted.notna().sum() > 0:
                oil[col] = converted
                date_col = col
                break

    if date_col is None:
        raise ValueError("无法在原油价格数据中识别日期列")

    price_cols = [c for c in oil.columns if c != date_col]
    for col in price_cols:
        oil[col] = pd.to_numeric(oil[col], errors="coerce")

    oil = oil.dropna(subset=[date_col])
    oil["quarter"] = oil[date_col].dt.to_period("Q").astype(str)

    oil_q = oil.groupby("quarter")[price_cols].mean(numeric_only=True).reset_index()

    if len(price_cols) == 1:
        oil_q = oil_q.rename(columns={price_cols[0]: "crude_oil_price"})
    else:
        oil_q["crude_oil_price"] = oil_q[price_cols].mean(axis=1)
        oil_q = oil_q[["quarter", "crude_oil_price"]]

    return oil_q


def load_fx_quarterly(base_path: Path) -> pd.DataFrame:
    fx_path = base_path / "Foreign_Exchange_Rates.csv"
    fx = pd.read_csv(fx_path)

    first_col = fx.columns[0]
    if first_col.startswith("Unnamed"):
        fx = fx.drop(columns=[first_col])

    fx = fx.rename(columns={"Time Serie": "date"})
    fx["date"] = pd.to_datetime(fx["date"], errors="coerce")
    fx = fx.dropna(subset=["date"])

    for col in fx.columns:
        if col == "date":
            continue
        fx[col] = pd.to_numeric(fx[col], errors="coerce")

    fx["quarter"] = fx["date"].dt.to_period("Q").astype(str)
    fx_q = fx.groupby("quarter").mean(numeric_only=True).reset_index()
    return fx_q


def load_wfp_food_quarterly(base_path: Path) -> pd.DataFrame:
    wfp_path = base_path / "Global WFP Food Prices.csv"
    wfp = pd.read_csv(wfp_path)

    wfp["date"] = pd.to_datetime(wfp["date"], errors="coerce")
    wfp = wfp.dropna(subset=["date"])

    wfp["price_usd"] = pd.to_numeric(wfp["price_usd"], errors="coerce")
    wfp = wfp.dropna(subset=["price_usd"])

    wfp["quarter"] = wfp["date"].dt.to_period("Q").astype(str)

    cereals = wfp[wfp["category"] == "cereals and tubers"]
    cereals_q = (
        cereals.groupby("quarter", as_index=False)["price_usd"]
        .mean()
        .rename(columns={"price_usd": "wfp_food_price_usd_mean"})
    )

    target_defs = {
        "wheat": ["Wheat"],
        "maize": ["Maize"],
        "soybeans": ["Soybean", "Soybeans"],
        "cotton": ["Cotton"],
        "palm_oil": ["Palm oil", "Oil (palm)"],
    }

    dfs = [cereals_q]
    for key, patterns in target_defs.items():
        mask = wfp["commodity"].str.contains(patterns[0], case=False, na=False, regex=False)
        if len(patterns) > 1:
            for p in patterns[1:]:
                mask = mask | wfp["commodity"].str.contains(p, case=False, na=False, regex=False)
        subset = wfp[mask]
        if subset.empty:
            continue
        q = (
            subset.groupby("quarter", as_index=False)["price_usd"]
            .mean()
            .rename(columns={"price_usd": f"wfp_{key}_price_usd_mean"})
        )
        dfs.append(q)

    result = reduce(lambda left, right: pd.merge(left, right, on="quarter", how="outer"), dfs)
    return result


def load_china_gdp_quarterly(base_path: Path) -> pd.DataFrame:
    gdp_path = base_path / "GDP_2005_2025_final.csv"
    gdp = pd.read_csv(gdp_path)

    year_cols = [c for c in gdp.columns if c != "Country"]
    for col in year_cols:
        gdp[col] = pd.to_numeric(gdp[col], errors="coerce")

    china = gdp[gdp["Country"] == "China"]
    if china.empty:
        raise ValueError("在GDP数据中未找到中国的记录")

    china_row = china.iloc[0][year_cols]
    china_gdp_by_year = china_row.reset_index()
    china_gdp_by_year.columns = ["year", "china_gdp"]
    china_gdp_by_year["year"] = china_gdp_by_year["year"].astype(float).astype(int)

    rows = []
    china_gdp_by_year = china_gdp_by_year.sort_values("year").reset_index(drop=True)
    n = len(china_gdp_by_year)
    for i in range(n):
        y = int(china_gdp_by_year.loc[i, "year"])
        Ay = china_gdp_by_year.loc[i, "china_gdp"]
        if pd.isna(Ay):
            continue
        if i < n - 1 and not pd.isna(china_gdp_by_year.loc[i + 1, "china_gdp"]):
            A_next = china_gdp_by_year.loc[i + 1, "china_gdp"]
            if Ay and A_next and Ay > 0 and A_next > 0:
                r = (A_next / Ay) ** (1 / 4)
                quarters = [Ay * (r ** k) for k in range(4)]
            else:
                step = (A_next - Ay) / 4
                quarters = [Ay + step * k for k in range(4)]
        else:
            quarters = [Ay] * 4
        for q_idx, val in enumerate(quarters, start=1):
            rows.append({"quarter": f"{y}Q{q_idx}", "china_gdp": float(val)})

    gdp_quarterly = pd.DataFrame(rows)
    return gdp_quarterly


def load_industry_contribution(base_path: Path) -> pd.DataFrame:
    contrib_path = base_path / "GDP_Industry_Contribution.csv"
    if not contrib_path.exists():
        return pd.DataFrame()
    
    df = pd.read_csv(contrib_path)
    
    rows = []
    for _, row in df.iterrows():
        year = int(row["Year"])
        for q in range(1, 5):
            new_row = row.to_dict()
            new_row["quarter"] = f"{year}Q{q}"
            del new_row["Year"]
            rows.append(new_row)
            
    df_q = pd.DataFrame(rows)
    df_q = df_q.rename(columns={
        "GDP_Growth": "gdp_growth_rate",
        "Primary_Pull": "primary_industry_pull",
        "Secondary_Pull": "secondary_industry_pull",
        "Tertiary_Pull": "tertiary_industry_pull"
    })
    total = df_q["primary_industry_pull"] + df_q["secondary_industry_pull"] + df_q["tertiary_industry_pull"]
    df_q["primary_industry_share"] = df_q["primary_industry_pull"] / total.replace(0, pd.NA) * 100
    return df_q


def build_start_table():
    base_path = Path(__file__).parent

    oil_q = load_crude_oil_quarterly(base_path)
    fx_q = load_fx_quarterly(base_path)
    wfp_q = load_wfp_food_quarterly(base_path)
    gdp_q = load_china_gdp_quarterly(base_path)
    contrib_q = load_industry_contribution(base_path)

    dfs = [oil_q, fx_q, wfp_q, gdp_q]
    if not contrib_q.empty:
        dfs.append(contrib_q)
        
    start = reduce(lambda left, right: pd.merge(left, right, on="quarter", how="outer"), dfs)
    start = start.sort_values("quarter").reset_index(drop=True)

    q = pd.PeriodIndex(start["quarter"], freq="Q")
    start = start[q.year >= 2005].reset_index(drop=True)
    if "wfp_food_price_usd_mean" in start.columns:
        start = start.drop(columns=["wfp_food_price_usd_mean"])

    out_path = base_path / "START.csv"
    start.to_csv(out_path, index=False)


def analyze_and_visualize_start(base_path: Path):
    start_path = base_path / "START.csv"
    df = pd.read_csv(start_path)

    gdp_col = "china_gdp"
    if gdp_col in df.columns and "primary_industry_share" in df.columns:
        df["primary_weighted_gdp"] = df[gdp_col] * df["primary_industry_share"] / 100

    vars_of_interest = [
        "crude_oil_price",
        "wfp_wheat_price_usd_mean",
        "wfp_maize_price_usd_mean",
        "wfp_soybeans_price_usd_mean",
        "wfp_cotton_price_usd_mean",
        "wfp_palm_oil_price_usd_mean",
        "china_gdp",
        "primary_industry_share",
        "primary_weighted_gdp",
    ]

    existing_vars = [c for c in vars_of_interest if c in df.columns]
    if not existing_vars:
        return

    numeric_df = df[existing_vars].copy()
    desc = numeric_df.describe().T
    desc_path = base_path / "START_descriptive_stats.csv"
    desc.to_csv(desc_path)

    corr = numeric_df.corr()
    corr_path = base_path / "START_correlations.csv"
    corr.to_csv(corr_path)

    if gdp_col in corr.columns:
        corr_gdp = corr[[gdp_col]].drop(index=gdp_col, errors="ignore")
        corr_gdp_path = base_path / "START_correlation_for_plot.csv"
        corr_gdp.to_csv(corr_gdp_path)

    rel_gdp_col = "primary_weighted_gdp"
    if rel_gdp_col in df.columns:
        rel_cols = [
            "crude_oil_price",
            "wfp_wheat_price_usd_mean",
            "wfp_maize_price_usd_mean",
            "wfp_soybeans_price_usd_mean",
            "wfp_cotton_price_usd_mean",
            "wfp_palm_oil_price_usd_mean",
            rel_gdp_col,
        ]
        rel_cols = [c for c in rel_cols if c in df.columns]
        if rel_cols:
            df_rel = df[rel_cols].copy()
            for c in rel_cols:
                df_rel[c] = pd.to_numeric(df_rel[c], errors="coerce")
                df_rel.loc[df_rel[c] <= 0, c] = np.nan
                df_rel[c] = np.log(df_rel[c])
            
            corr_rel = df_rel.corr()
            if rel_gdp_col in corr_rel.columns:
                corr_rel_gdp = corr_rel[[rel_gdp_col]].drop(index=rel_gdp_col, errors="ignore")
                corr_rel_path = base_path / "START_correlation_rel_gdp.csv"
                corr_rel_gdp.to_csv(corr_rel_path)

            df_rel_diff = df_rel.diff()
            corr_rel_diff = df_rel_diff.corr()
            if rel_gdp_col in corr_rel_diff.columns:
                corr_rel_diff_gdp = corr_rel_diff[[rel_gdp_col]].drop(index=rel_gdp_col, errors="ignore")
                corr_rel_diff_path = base_path / "START_correlation_rel_gdp_vol.csv"
                corr_rel_diff_gdp.to_csv(corr_rel_diff_path)

            def corr_and_pvalue(x: pd.Series, y: pd.Series):
                mask = x.notna() & y.notna()
                n = int(mask.sum())
                if n < 3:
                    return None, None, n
                r = float(x[mask].corr(y[mask]))
                if not np.isfinite(r):
                    return None, None, n
                if abs(r) >= 1:
                    return r, 0.0, n
                t = r * math.sqrt((n - 2) / (1 - r * r))
                dfree = n - 2
                try:
                    from scipy import stats

                    p = float(stats.t.sf(abs(t), df=dfree) * 2)
                except Exception:
                    z = abs(t)
                    p = float(2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2)))))
                return r, p, n

            summary_rows = []
            for col in rel_cols:
                if col == rel_gdp_col:
                    continue
                r1, p1, n1 = corr_and_pvalue(df_rel[rel_gdp_col], df_rel[col])
                r2, p2, n2 = corr_and_pvalue(df_rel_diff[rel_gdp_col], df_rel_diff[col])
                summary_rows.append(
                    {
                        "variable": col,
                        "corr_log_level": r1,
                        "p_log_level": p1,
                        "n_log_level": n1,
                        "corr_log_return": r2,
                        "p_log_return": p2,
                        "n_log_return": n2,
                    }
                )
            if summary_rows:
                summary_df = pd.DataFrame(summary_rows).set_index("variable")
                summary_path = base_path / "START_elasticity_corr_summary.csv"
                summary_df.to_csv(summary_path)

            # --- NEW: Lagged Correlation Analysis (Log Difference / Volatility) ---
            lag_rows = []
            max_lag = 8
            for col in rel_cols:
                if col == rel_gdp_col:
                    continue
                
                # Calculate correlation for each lag k=0..8
                # We want to see if Price_{t-k} affects GDP_t
                row_data = {"variable": col}
                for k in range(max_lag + 1):
                    # shift(k) moves data down by k rows, so index t has data from t-k
                    shifted_series = df_rel_diff[col].shift(k)
                    r, p, n = corr_and_pvalue(df_rel_diff[rel_gdp_col], shifted_series)
                    row_data[f"lag_{k}"] = r
                    row_data[f"pval_{k}"] = p
                
                lag_rows.append(row_data)
            
            if lag_rows:
                lag_df = pd.DataFrame(lag_rows).set_index("variable")
                lag_path = base_path / "START_lagged_correlations.csv"
                lag_df.to_csv(lag_path)
            ewma_rows = []
            shock_rows = []
            alpha = 0.15
            for col in rel_cols:
                if col == rel_gdp_col:
                    continue
                r = df_rel[col].diff()
                r_l1 = r.shift(1)
                mask = r.notna() & r_l1.notna()
                if int(mask.sum()) >= 10:
                    num = float((r[mask] * r_l1[mask]).sum())
                    den = float((r_l1[mask] * r_l1[mask]).sum())
                    phi = num / den if den != 0 else 0.0
                else:
                    phi = 0.0
                e = r - phi * r_l1
                ewma_r = r.ewm(alpha=alpha, adjust=False).mean()
                row_e = {"variable": col}
                row_s = {"variable": col}
                ewma_sigma = e.pow(2).ewm(alpha=alpha, adjust=False).mean().pow(0.5)
                s = e / ewma_sigma
                for k in range(max_lag + 1):
                    x1 = ewma_r.shift(k)
                    rr1, pp1, _ = corr_and_pvalue(df_rel_diff[rel_gdp_col], x1)
                    row_e[f"lag_{k}"] = rr1
                    row_e[f"pval_{k}"] = pp1
                    x2 = s.shift(k)
                    rr2, pp2, _ = corr_and_pvalue(df_rel_diff[rel_gdp_col], x2)
                    row_s[f"lag_{k}"] = rr2
                    row_s[f"pval_{k}"] = pp2
                ewma_rows.append(row_e)
                shock_rows.append(row_s)
            # Agri Factor (equal-weighted z-score across commodities, excluding crude oil and rel_gdp)
            comm_cols = [c for c in rel_cols if c not in (rel_gdp_col, "crude_oil_price")]
            z_df = pd.DataFrame(index=df_rel_diff.index)
            for c in comm_cols:
                series_c = df_rel_diff[c]
                mu = series_c.mean()
                sd = series_c.std(ddof=0)
                if sd and sd != 0 and np.isfinite(sd):
                    z_df[c] = (series_c - mu) / sd
                else:
                    z_df[c] = np.nan
            agri_factor = z_df.mean(axis=1, skipna=True)
            row_f = {"variable": "agri_factor"}
            for k in range(max_lag + 1):
                rv, pv, _ = corr_and_pvalue(df_rel_diff[rel_gdp_col], agri_factor.shift(k))
                row_f[f"lag_{k}"] = rv
                row_f[f"pval_{k}"] = pv
            if lag_rows is not None:
                # Append to lag_df on write path
                lag_rows.append(row_f)
                lag_df = pd.DataFrame(lag_rows).set_index("variable")
                lag_path = base_path / "START_lagged_correlations.csv"
                lag_df.to_csv(lag_path)
            # EWMA for factor
            ewma_r_f = agri_factor.ewm(alpha=alpha, adjust=False).mean()
            row_fe = {"variable": "agri_factor"}
            # Prewhiten factor shocks
            r_l1_f = agri_factor.shift(1)
            mask_f = agri_factor.notna() & r_l1_f.notna()
            if int(mask_f.sum()) >= 10:
                num_f = float((agri_factor[mask_f] * r_l1_f[mask_f]).sum())
                den_f = float((r_l1_f[mask_f] * r_l1_f[mask_f]).sum())
                phi_f = num_f / den_f if den_f != 0 else 0.0
            else:
                phi_f = 0.0
            e_f = agri_factor - phi_f * r_l1_f
            ewma_sigma_f = e_f.pow(2).ewm(alpha=alpha, adjust=False).mean().pow(0.5)
            s_f = e_f / ewma_sigma_f
            row_fs = {"variable": "agri_factor"}
            for k in range(max_lag + 1):
                rr1f, pp1f, _ = corr_and_pvalue(df_rel_diff[rel_gdp_col], ewma_r_f.shift(k))
                row_fe[f"lag_{k}"] = rr1f
                row_fe[f"pval_{k}"] = pp1f
                rr2f, pp2f, _ = corr_and_pvalue(df_rel_diff[rel_gdp_col], s_f.shift(k))
                row_fs[f"lag_{k}"] = rr2f
                row_fs[f"pval_{k}"] = pp2f
            if ewma_rows is not None:
                ewma_rows.append(row_fe)
            if shock_rows is not None:
                shock_rows.append(row_fs)
            if ewma_rows:
                ewma_df = pd.DataFrame(ewma_rows).set_index("variable")
                (base_path / "START_lagged_correlations_ewma.csv").write_text(ewma_df.to_csv(), encoding="utf-8")
            if shock_rows:
                shock_df = pd.DataFrame(shock_rows).set_index("variable")
                (base_path / "START_lagged_correlations_shock.csv").write_text(shock_df.to_csv(), encoding="utf-8")

    df_plot = df[["quarter"] + existing_vars].dropna()
    if not df_plot.empty:
        q_period = pd.PeriodIndex(df_plot["quarter"], freq="Q")
        df_plot["quarter_dt"] = q_period.to_timestamp()
        ts_df = df_plot[["quarter_dt"] + existing_vars]
        ts_path = base_path / "START_timeseries.csv"
        ts_df.to_csv(ts_path, index=False)

    # 相关性热力图仅使用 START_correlation_for_plot.csv 中“各变量与GDP”的相关系数


def build_echarts_data(base_path: Path):
    start_path = base_path / "START.csv"
    if not start_path.exists():
        return

    df = pd.read_csv(start_path)

    cols = [
        "crude_oil_price",
        "wfp_wheat_price_usd_mean",
        "wfp_maize_price_usd_mean",
        "wfp_soybeans_price_usd_mean",
        "wfp_cotton_price_usd_mean",
        "wfp_palm_oil_price_usd_mean",
        "china_gdp",
        "primary_industry_share"
    ]

    existing_cols = [c for c in cols if c in df.columns]
    if not existing_cols:
        return

    df_ts = df[["quarter"] + existing_cols].copy()
    quarters = df_ts["quarter"].tolist()

    def series_or_none(name: str) -> list:
        if name not in df_ts.columns:
            return []
        s = df_ts[name]
        s = s.where(s.notna(), None)
        return s.tolist()

    oil = series_or_none("crude_oil_price")
    wheat = series_or_none("wfp_wheat_price_usd_mean")
    maize = series_or_none("wfp_maize_price_usd_mean")
    soybeans = series_or_none("wfp_soybeans_price_usd_mean")
    cotton = series_or_none("wfp_cotton_price_usd_mean")
    palm_oil = series_or_none("wfp_palm_oil_price_usd_mean")
    gdp = series_or_none("china_gdp")
    primary_share = series_or_none("primary_industry_share")

    corr_path = base_path / "START_correlation_for_plot.csv"
    corr_rel_path = base_path / "START_correlation_rel_gdp.csv"
    corr_rel_vol_path = base_path / "START_correlation_rel_gdp_vol.csv"
    elasticity_summary_path = base_path / "START_elasticity_corr_summary.csv"
    corr_vars_en = [
        "crude_oil_price",
        "wfp_wheat_price_usd_mean",
        "wfp_maize_price_usd_mean",
        "wfp_soybeans_price_usd_mean",
        "wfp_cotton_price_usd_mean",
        "wfp_palm_oil_price_usd_mean",
    ]
    corr_vars_cn = [
        "原油价格",
        "小麦(USD)",
        "玉米(USD)",
        "大豆(USD)",
        "棉花(USD)",
        "棕榈油(USD)",
    ]
    
    corr_with_gdp = []
    if corr_path.exists():
        corr_df = pd.read_csv(corr_path, index_col=0)
        final_values = []
        for en in corr_vars_en:
            if en in corr_df.index:
                val = float(corr_df.loc[en].iloc[0])
                final_values.append(val)
            else:
                final_values.append(0.0)
        corr_with_gdp = final_values

    corr_with_rel_gdp = []
    pval_with_rel_gdp = []
    n_with_rel_gdp = []
    corr_with_rel_gdp_vol = []
    pval_with_rel_gdp_vol = []
    n_with_rel_gdp_vol = []

    # --- NEW: Lagged Correlation Data ---
    lag_data = {}
    lag_pval_data = {}
    lag_path = base_path / "START_lagged_correlations.csv"
    if lag_path.exists():
        lag_df = pd.read_csv(lag_path, index_col=0)
        # Structure: { 'crude_oil_price': [r0, r1, ... r8], ... }
        for en in corr_vars_en:
            if en in lag_df.index:
                corrs = []
                pvals = []
                # Check for lag_0 to lag_8
                for k in range(9):
                    col_name = f"lag_{k}"
                    p_name = f"pval_{k}"
                    if col_name in lag_df.columns:
                        val = lag_df.loc[en][col_name]
                        corrs.append(float(val) if pd.notna(val) else 0.0)
                    else:
                        corrs.append(0.0)
                    if p_name in lag_df.columns:
                        pv = lag_df.loc[en][p_name]
                        pvals.append(float(pv) if pd.notna(pv) else None)
                    else:
                        pvals.append(None)
                lag_data[en] = corrs
                lag_pval_data[en] = pvals
            else:
                lag_data[en] = [0.0] * 9
                lag_pval_data[en] = [None] * 9
    else:
        # Initialize with zeros if file doesn't exist yet
        for en in corr_vars_en:
            lag_data[en] = [0.0] * 9

    if elasticity_summary_path.exists():
        s_df = pd.read_csv(elasticity_summary_path, index_col=0)
        for en in corr_vars_en:
            if en in s_df.index:
                row = s_df.loc[en]
                corr_with_rel_gdp.append(None if pd.isna(row.get("corr_log_level")) else float(row.get("corr_log_level")))
                pval_with_rel_gdp.append(None if pd.isna(row.get("p_log_level")) else float(row.get("p_log_level")))
                n_with_rel_gdp.append(int(row.get("n_log_level")) if not pd.isna(row.get("n_log_level")) else 0)

                corr_with_rel_gdp_vol.append(None if pd.isna(row.get("corr_log_return")) else float(row.get("corr_log_return")))
                pval_with_rel_gdp_vol.append(None if pd.isna(row.get("p_log_return")) else float(row.get("p_log_return")))
                n_with_rel_gdp_vol.append(int(row.get("n_log_return")) if not pd.isna(row.get("n_log_return")) else 0)
            else:
                corr_with_rel_gdp.append(0.0)
                pval_with_rel_gdp.append(None)
                n_with_rel_gdp.append(0)
                corr_with_rel_gdp_vol.append(0.0)
                pval_with_rel_gdp_vol.append(None)
                n_with_rel_gdp_vol.append(0)
    else:
        if corr_rel_path.exists():
            corr_ret_df = pd.read_csv(corr_rel_path, index_col=0)
            for en in corr_vars_en:
                if en in corr_ret_df.index:
                    corr_with_rel_gdp.append(float(corr_ret_df.loc[en].iloc[0]))
                else:
                    corr_with_rel_gdp.append(0.0)
        if corr_rel_vol_path.exists():
            corr_vol_df = pd.read_csv(corr_rel_vol_path, index_col=0)
            for en in corr_vars_en:
                if en in corr_vol_df.index:
                    corr_with_rel_gdp_vol.append(float(corr_vol_df.loc[en].iloc[0]))
                else:
                    corr_with_rel_gdp_vol.append(0.0)

    js_lines = []
    js_lines.append("var quarters = " + json.dumps(quarters, ensure_ascii=False) + ";")
    js_lines.append("var oil = " + json.dumps(oil, ensure_ascii=False) + ";")
    js_lines.append("var wheat = " + json.dumps(wheat, ensure_ascii=False) + ";")
    js_lines.append("var maize = " + json.dumps(maize, ensure_ascii=False) + ";")
    js_lines.append("var soybeans = " + json.dumps(soybeans, ensure_ascii=False) + ";")
    js_lines.append("var cotton = " + json.dumps(cotton, ensure_ascii=False) + ";")
    js_lines.append("var palm_oil = " + json.dumps(palm_oil, ensure_ascii=False) + ";")
    js_lines.append("var gdp = " + json.dumps(gdp, ensure_ascii=False) + ";")
    js_lines.append("var primary_share = " + json.dumps(primary_share, ensure_ascii=False) + ";")
    js_lines.append("var corrVars = " + json.dumps(corr_vars_cn, ensure_ascii=False) + ";")
    js_lines.append("var corrWithGdp = " + json.dumps(corr_with_gdp, ensure_ascii=False) + ";")
    js_lines.append("var corrWithRelGdp = " + json.dumps(corr_with_rel_gdp, ensure_ascii=False) + ";")
    js_lines.append("var corrWithRelGdpVol = " + json.dumps(corr_with_rel_gdp_vol, ensure_ascii=False) + ";")
    js_lines.append("var pvalWithRelGdp = " + json.dumps(pval_with_rel_gdp, ensure_ascii=False) + ";")
    js_lines.append("var pvalWithRelGdpVol = " + json.dumps(pval_with_rel_gdp_vol, ensure_ascii=False) + ";")
    js_lines.append("var nWithRelGdp = " + json.dumps(n_with_rel_gdp, ensure_ascii=False) + ";")
    js_lines.append("var nWithRelGdpVol = " + json.dumps(n_with_rel_gdp_vol, ensure_ascii=False) + ";")
    
    # Structure for lagData: { "crude_oil_price": [r0, r1...], ... }
    # We should also export lag keys for convenience
    lag_keys = [f"Lag {k}" for k in range(9)]
    js_lines.append("var lagKeys = " + json.dumps(lag_keys, ensure_ascii=False) + ";")
    # Convert dict to simple array of series if needed, but dict is fine.
    # Actually, let's keep it as an object keyed by english var name, or better yet, align with corrVars order
    lag_series_data = []
    lag_pval_series_data = []
    for en in corr_vars_en:
        lag_series_data.append(lag_data.get(en, [0.0]*9))
        lag_pval_series_data.append(lag_pval_data.get(en, [None]*9))
    js_lines.append("var lagSeriesData = " + json.dumps(lag_series_data, ensure_ascii=False) + ";")
    js_lines.append("var lagPvalSeriesData = " + json.dumps(lag_pval_series_data, ensure_ascii=False) + ";")
    lag_data_ewma = {}
    lag_data_shock = {}
    lag_pval_ewma = {}
    lag_pval_shock = {}
    lag_path_ewma = base_path / "START_lagged_correlations_ewma.csv"
    lag_path_shock = base_path / "START_lagged_correlations_shock.csv"
    if lag_path_ewma.exists():
        lag_df_ewma = pd.read_csv(lag_path_ewma, index_col=0)
        for en in corr_vars_en:
            if en in lag_df_ewma.index:
                corrs = []
                pvals = []
                for k in range(9):
                    col_name = f"lag_{k}"
                    p_name = f"pval_{k}"
                    if col_name in lag_df_ewma.columns:
                        val = lag_df_ewma.loc[en][col_name]
                        corrs.append(float(val) if pd.notna(val) else 0.0)
                    else:
                        corrs.append(0.0)
                    if p_name in lag_df_ewma.columns:
                        pv = lag_df_ewma.loc[en][p_name]
                        pvals.append(float(pv) if pd.notna(pv) else None)
                    else:
                        pvals.append(None)
                lag_data_ewma[en] = corrs
                lag_pval_ewma[en] = pvals
            else:
                lag_data_ewma[en] = [0.0] * 9
                lag_pval_ewma[en] = [None] * 9
    else:
        for en in corr_vars_en:
            lag_data_ewma[en] = [0.0] * 9
    if lag_path_shock.exists():
        lag_df_shock = pd.read_csv(lag_path_shock, index_col=0)
        for en in corr_vars_en:
            if en in lag_df_shock.index:
                corrs = []
                pvals = []
                for k in range(9):
                    col_name = f"lag_{k}"
                    p_name = f"pval_{k}"
                    if col_name in lag_df_shock.columns:
                        val = lag_df_shock.loc[en][col_name]
                        corrs.append(float(val) if pd.notna(val) else 0.0)
                    else:
                        corrs.append(0.0)
                    if p_name in lag_df_shock.columns:
                        pv = lag_df_shock.loc[en][p_name]
                        pvals.append(float(pv) if pd.notna(pv) else None)
                    else:
                        pvals.append(None)
                lag_data_shock[en] = corrs
                lag_pval_shock[en] = pvals
            else:
                lag_data_shock[en] = [0.0] * 9
                lag_pval_shock[en] = [None] * 9
    else:
        for en in corr_vars_en:
            lag_data_shock[en] = [0.0] * 9
    lag_series_data_ewma = []
    lag_series_data_shock = []
    for en in corr_vars_en:
        lag_series_data_ewma.append(lag_data_ewma.get(en, [0.0]*9))
        lag_series_data_shock.append(lag_data_shock.get(en, [0.0]*9))
    js_lines.append("var lagSeriesDataEWMA = " + json.dumps(lag_series_data_ewma, ensure_ascii=False) + ";")
    js_lines.append("var lagSeriesDataShock = " + json.dumps(lag_series_data_shock, ensure_ascii=False) + ";")
    lag_pval_series_data_ewma = []
    lag_pval_series_data_shock = []
    for en in corr_vars_en:
        lag_pval_series_data_ewma.append(lag_pval_ewma.get(en, [None]*9))
        lag_pval_series_data_shock.append(lag_pval_shock.get(en, [None]*9))
    js_lines.append("var lagPvalSeriesDataEWMA = " + json.dumps(lag_pval_series_data_ewma, ensure_ascii=False) + ";")
    js_lines.append("var lagPvalSeriesDataShock = " + json.dumps(lag_pval_series_data_shock, ensure_ascii=False) + ";")
    # Export Agri Factor lag arrays separately for direct plotting
    # Read agri_factor rows explicitly if present
    agri_factor_lag = [0.0]*9
    agri_factor_lag_p = [None]*9
    if (base_path / "START_lagged_correlations.csv").exists():
        _df = pd.read_csv(base_path / "START_lagged_correlations.csv", index_col=0)
        if "agri_factor" in _df.index:
            agri_factor_lag = []
            agri_factor_lag_p = []
            for k in range(9):
                nm = f"lag_{k}"
                pm = f"pval_{k}"
                agri_factor_lag.append(float(_df.loc["agri_factor"][nm]) if nm in _df.columns and pd.notna(_df.loc["agri_factor"][nm]) else 0.0)
                agri_factor_lag_p.append(float(_df.loc["agri_factor"][pm]) if pm in _df.columns and pd.notna(_df.loc["agri_factor"][pm]) else None)
    agri_factor_lag_ewma = [0.0]*9
    agri_factor_lag_ewma_p = [None]*9
    if (base_path / "START_lagged_correlations_ewma.csv").exists():
        _df = pd.read_csv(base_path / "START_lagged_correlations_ewma.csv", index_col=0)
        if "agri_factor" in _df.index:
            agri_factor_lag_ewma = []
            agri_factor_lag_ewma_p = []
            for k in range(9):
                nm = f"lag_{k}"
                pm = f"pval_{k}"
                agri_factor_lag_ewma.append(float(_df.loc["agri_factor"][nm]) if nm in _df.columns and pd.notna(_df.loc["agri_factor"][nm]) else 0.0)
                agri_factor_lag_ewma_p.append(float(_df.loc["agri_factor"][pm]) if pm in _df.columns and pd.notna(_df.loc["agri_factor"][pm]) else None)
    agri_factor_lag_shock = [0.0]*9
    agri_factor_lag_shock_p = [None]*9
    if (base_path / "START_lagged_correlations_shock.csv").exists():
        _df = pd.read_csv(base_path / "START_lagged_correlations_shock.csv", index_col=0)
        if "agri_factor" in _df.index:
            agri_factor_lag_shock = []
            agri_factor_lag_shock_p = []
            for k in range(9):
                nm = f"lag_{k}"
                pm = f"pval_{k}"
                agri_factor_lag_shock.append(float(_df.loc["agri_factor"][nm]) if nm in _df.columns and pd.notna(_df.loc["agri_factor"][nm]) else 0.0)
                agri_factor_lag_shock_p.append(float(_df.loc["agri_factor"][pm]) if pm in _df.columns and pd.notna(_df.loc["agri_factor"][pm]) else None)
    js_lines.append("var agriFactorLag = " + json.dumps(agri_factor_lag, ensure_ascii=False) + ";")
    js_lines.append("var agriFactorLagEWMA = " + json.dumps(agri_factor_lag_ewma, ensure_ascii=False) + ";")
    js_lines.append("var agriFactorLagShock = " + json.dumps(agri_factor_lag_shock, ensure_ascii=False) + ";")
    js_lines.append("var agriFactorLagP = " + json.dumps(agri_factor_lag_p, ensure_ascii=False) + ";")
    js_lines.append("var agriFactorLagEWMAP = " + json.dumps(agri_factor_lag_ewma_p, ensure_ascii=False) + ";")
    js_lines.append("var agriFactorLagShockP = " + json.dumps(agri_factor_lag_shock_p, ensure_ascii=False) + ";")

    js_path = base_path / "start_echarts_data.js"
    js_path.write_text("\n".join(js_lines), encoding="utf-8")


if __name__ == "__main__":
    base = Path(__file__).parent
    try:
        build_start_table()
    except ImportError:
        if not (base / "START.csv").exists():
            raise
    analyze_and_visualize_start(base)
    build_echarts_data(base)

