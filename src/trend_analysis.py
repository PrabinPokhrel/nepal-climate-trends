"""
trend_analysis.py
Mann-Kendall trend tests on ERA5 Nepal climate data (1980-2023).

Methods:
  - Mann-Kendall test (pymannkendall) - non-parametric monotonic trend
  - Theil-Sen slope estimator - robust trend magnitude
  - Applied per grid cell for spatial trend maps
  - Applied to seasonal aggregates for seasonal trend analysis

Mann-Kendall is the standard method for hydroclimatic trend analysis
(Yue and Wang 2004; Burn and Hag Elnur 2002) and is used throughout
the IPCC AR5/AR6 regional chapters for trend detection.

Output:
  - Per grid cell trend maps (temperature and precipitation)
  - Seasonal trend tables
  - Station-level trend comparison
"""

import os
import warnings
import numpy as np
import pandas as pd
import xarray as xr
import pymannkendall as mk
from scipy import stats

warnings.filterwarnings("ignore")

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
RESULTS_DIR   = os.path.join(os.path.dirname(__file__), "..", "outputs", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def mann_kendall_grid(da_annual):
    """
    Apply Mann-Kendall test to each grid cell.
    Returns DataArrays of trend slope, p-value, and significance.

    da_annual: xarray DataArray with dims (year, latitude, longitude)
    """
    lats   = da_annual.latitude.values
    lons   = da_annual.longitude.values
    years  = da_annual.year.values
    n_yrs  = len(years)

    slopes    = np.full((len(lats), len(lons)), np.nan)
    pvalues   = np.full((len(lats), len(lons)), np.nan)
    tau       = np.full((len(lats), len(lons)), np.nan)
    intercepts = np.full((len(lats), len(lons)), np.nan)

    print(f"  Running Mann-Kendall on {len(lats) * len(lons)} grid cells...")

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            ts = da_annual.sel(latitude=lat, longitude=lon).values
            if np.sum(np.isfinite(ts)) < 10:
                continue
            try:
                result = mk.original_test(ts)
                slopes[i, j]     = result.slope
                pvalues[i, j]    = result.p
                tau[i, j]        = result.Tau
                # Theil-Sen intercept
                intercepts[i, j] = np.median(ts) - result.slope * np.median(years)
            except Exception:
                continue

    # Wrap back into DataArrays
    coords = {"latitude": lats, "longitude": lons}
    slope_da  = xr.DataArray(slopes,    coords=coords, dims=["latitude", "longitude"],
                              attrs={"long_name": "Theil-Sen slope (units/year)"})
    pval_da   = xr.DataArray(pvalues,   coords=coords, dims=["latitude", "longitude"],
                              attrs={"long_name": "Mann-Kendall p-value"})
    sig_da    = xr.DataArray((pvalues < 0.05).astype(float),
                              coords=coords, dims=["latitude", "longitude"],
                              attrs={"long_name": "Significant trend (p<0.05)"})
    tau_da    = xr.DataArray(tau,        coords=coords, dims=["latitude", "longitude"],
                              attrs={"long_name": "Kendall Tau"})

    return slope_da, pval_da, sig_da, tau_da


def seasonal_trends(ts_path, label):
    """
    Mann-Kendall trend test for each season.
    Returns summary DataFrame.
    """
    df = pd.read_csv(ts_path)
    seasons = df["season"].unique()
    records = []

    for season in seasons:
        sub = df[df["season"] == season].sort_values("year")
        ts  = sub[label].values
        yrs = sub["year"].values

        result = mk.original_test(ts)

        # Trend per decade
        slope_per_decade = result.slope * 10

        records.append({
            "season":           season,
            "mk_trend":         result.trend,
            "mk_tau":           round(result.Tau, 4),
            "mk_pvalue":        round(result.p, 4),
            "significant":      result.p < 0.05,
            "slope_per_year":   round(result.slope, 5),
            "slope_per_decade": round(slope_per_decade, 4),
            "mean_1980s":       round(float(ts[yrs < 1990].mean()), 3),
            "mean_2010s":       round(float(ts[(yrs >= 2010) & (yrs < 2020)].mean()), 3),
            "mean_2020s":       round(float(ts[yrs >= 2020].mean()), 3),
        })

    return pd.DataFrame(records)


def annual_trends(ts_path, label):
    """Mann-Kendall on annual time series."""
    df     = pd.read_csv(ts_path).sort_values("year")
    ts     = df[label].values
    yrs    = df["year"].values
    result = mk.original_test(ts)

    return {
        "trend":            result.trend,
        "tau":              round(result.Tau, 4),
        "pvalue":           round(result.p, 4),
        "significant":      result.p < 0.05,
        "slope_per_year":   round(result.slope, 5),
        "slope_per_decade": round(result.slope * 10, 4),
        "total_change":     round(result.slope * (yrs[-1] - yrs[0]), 3),
    }


def main():
    print("=" * 65)
    print("MANN-KENDALL TREND ANALYSIS - NEPAL ERA5 (1980-2023)")
    print("=" * 65)

    # ── Annual trend summary ──────────────────────────────────
    print("\n[1] Annual trend analysis")
    print("-" * 65)

    t2m_annual = annual_trends(
        os.path.join(PROCESSED_DIR, "t2m_annual_timeseries.csv"),
        "temperature_C"
    )
    tp_annual = annual_trends(
        os.path.join(PROCESSED_DIR, "tp_annual_timeseries.csv"),
        "precipitation_mm"
    )

    print(f"\nTemperature (annual mean, Nepal spatial average):")
    print(f"  Trend          : {t2m_annual['trend']}")
    print(f"  Kendall τ      : {t2m_annual['tau']}")
    print(f"  p-value        : {t2m_annual['pvalue']}")
    print(f"  Significant    : {t2m_annual['significant']} (p < 0.05)")
    print(f"  Slope/decade   : +{t2m_annual['slope_per_decade']:.4f} °C/decade")
    print(f"  Total change   : +{t2m_annual['total_change']:.3f} °C (1980-2023)")

    print(f"\nPrecipitation (annual mean, Nepal spatial average):")
    print(f"  Trend          : {tp_annual['trend']}")
    print(f"  Kendall τ      : {tp_annual['tau']}")
    print(f"  p-value        : {tp_annual['pvalue']}")
    print(f"  Significant    : {tp_annual['significant']} (p < 0.05)")
    print(f"  Slope/decade   : {tp_annual['slope_per_decade']:.4f} mm/month/decade")
    print(f"  Total change   : {tp_annual['total_change']:.3f} mm/month (1980-2023)")

    # Save annual summary
    annual_summary = pd.DataFrame([
        {"variable": "Temperature (°C)",       **t2m_annual},
        {"variable": "Precipitation (mm/mo)",  **tp_annual},
    ])
    annual_summary.to_csv(
        os.path.join(RESULTS_DIR, "annual_trend_summary.csv"), index=False
    )

    # ── Seasonal trends ───────────────────────────────────────
    print("\n[2] Seasonal trend analysis")
    print("-" * 65)

    t2m_seasonal = seasonal_trends(
        os.path.join(PROCESSED_DIR, "t2m_seasonal_timeseries.csv"),
        "temperature_C"
    )
    tp_seasonal = seasonal_trends(
        os.path.join(PROCESSED_DIR, "tp_seasonal_timeseries.csv"),
        "precipitation_mm"
    )

    print("\nTemperature trends by season (°C/decade):")
    for _, row in t2m_seasonal.iterrows():
        p   = row["mk_pvalue"]
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        print(f"  {row['season']:<25} {row['slope_per_decade']:+.4f} °C/decade  "
              f"p={p:.4f} {sig}")

    print("\nPrecipitation trends by season (mm/month/decade):")
    for _, row in tp_seasonal.iterrows():
        p   = row["mk_pvalue"]
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        print(f"  {row['season']:<25} {row['slope_per_decade']:+.4f} mm/mo/decade  "
              f"p={p:.4f} {sig}")

    t2m_seasonal.to_csv(
        os.path.join(RESULTS_DIR, "t2m_seasonal_trends.csv"), index=False
    )
    tp_seasonal.to_csv(
        os.path.join(RESULTS_DIR, "tp_seasonal_trends.csv"), index=False
    )

    # ── Gridded Mann-Kendall ──────────────────────────────────
    print("\n[3] Gridded Mann-Kendall trend maps")
    print("-" * 65)

    print("\nTemperature grid trends...")
    t2m_grid = xr.open_dataarray(
        os.path.join(PROCESSED_DIR, "t2m_annual_gridded.nc")
    )
    t2m_slope, t2m_pval, t2m_sig, t2m_tau = mann_kendall_grid(t2m_grid)

    print("Precipitation grid trends...")
    tp_grid = xr.open_dataarray(
        os.path.join(PROCESSED_DIR, "tp_annual_gridded.nc")
    )
    tp_slope, tp_pval, tp_sig, tp_tau = mann_kendall_grid(tp_grid)

    # Save gridded results
    ds_t2m = xr.Dataset({
        "slope":       t2m_slope * 10,   # per decade
        "pvalue":      t2m_pval,
        "significant": t2m_sig,
        "tau":         t2m_tau,
    })
    ds_t2m.to_netcdf(os.path.join(RESULTS_DIR, "t2m_trend_maps.nc"))

    ds_tp = xr.Dataset({
        "slope":       tp_slope * 10,    # per decade
        "pvalue":      tp_pval,
        "significant": tp_sig,
        "tau":         tp_tau,
    })
    ds_tp.to_netcdf(os.path.join(RESULTS_DIR, "tp_trend_maps.nc"))

    print(f"\nTemperature trend map:")
    print(f"  Mean slope     : +{float(t2m_slope.mean() * 10):.4f} °C/decade")
    print(f"  Max slope      : +{float(t2m_slope.max() * 10):.4f} °C/decade")
    print(f"  % significant  : {float(t2m_sig.mean()) * 100:.1f}% of grid cells (p<0.05)")

    print(f"\nPrecipitation trend map:")
    print(f"  Mean slope     : {float(tp_slope.mean() * 10):.4f} mm/mo/decade")
    print(f"  % significant  : {float(tp_sig.mean()) * 100:.1f}% of grid cells (p<0.05)")

    print(f"\n{'='*65}")
    print(f"✓ TREND ANALYSIS COMPLETE")
    print(f"  Results saved to: {RESULTS_DIR}")
    print(f"\n[NEXT] Run: python src/visualise.py")


if __name__ == "__main__":
    main()