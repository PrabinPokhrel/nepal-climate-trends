"""
preprocess.py
Loads ERA5 NetCDF files for Nepal, converts units, computes
seasonal aggregates, and prepares data for trend analysis.

Conversions:
  Temperature: Kelvin to Celsius (subtract 273.15)
  Precipitation: m/month to mm/month (multiply by 1000)

Seasons (Nepal climatology):
  Pre-monsoon : March-May (MAM)
  Monsoon     : June-September (JJAS)
  Post-monsoon: October-November (ON)
  Winter      : December-February (DJF)
"""

import os
import numpy as np
import pandas as pd
import xarray as xr

RAW_DIR       = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

T2M_PATH = os.path.join(RAW_DIR, "era5_t2m_1980_2023.nc")
TP_PATH  = os.path.join(RAW_DIR, "era5_tp_1980_2023.nc")

SEASONS = {
    "Pre-monsoon (MAM)":  [3, 4, 5],
    "Monsoon (JJAS)":     [6, 7, 8, 9],
    "Post-monsoon (ON)":  [10, 11],
    "Winter (DJF)":       [12, 1, 2],
}


def load_temperature():
    print("Loading temperature data...")
    ds = xr.open_dataset(T2M_PATH)
    print(f"  Variables : {list(ds.data_vars)}")
    print(f"  Dimensions: {dict(ds.dims)}")
    time_dim = "valid_time" if "valid_time" in ds.dims else "time"
    ds = ds.rename({time_dim: "time"})
    print(f"  Time range: {str(ds.time.values[0])[:10]} to {str(ds.time.values[-1])[:10]}")

    # Find temperature variable
    var = None
    for v in ["t2m", "VAR_2T", "2m_temperature"]:
        if v in ds:
            var = v
            break
    if var is None:
        var = list(ds.data_vars)[0]
    print(f"  Using variable: {var}")

    # Convert K to C
    t2m = ds[var] - 273.15
    t2m.attrs["units"] = "degC"
    t2m.name = "t2m_C"
    print(f"  Temperature range: {float(t2m.min()):.1f} to {float(t2m.max()):.1f} degC")
    return t2m


def load_precipitation():
    print("\nLoading precipitation data...")
    ds = xr.open_dataset(TP_PATH)
    print(f"  Variables : {list(ds.data_vars)}")
    time_dim = "valid_time" if "valid_time" in ds.dims else "time"
    ds = ds.rename({time_dim: "time"})

    # Find precipitation variable
    var = None
    for v in ["tp", "total_precipitation"]:
        if v in ds:
            var = v
            break
    if var is None:
        var = list(ds.data_vars)[0]
    print(f"  Using variable: {var}")

    # Convert m/month to mm/month
    tp = ds[var] * 1000
    tp.attrs["units"] = "mm/month"
    tp.name = "tp_mm"

    # ERA5 monthly tp can be negative due to floating point - clip
    tp = tp.clip(min=0)
    print(f"  Precipitation range: {float(tp.min()):.1f} to {float(tp.max()):.1f} mm/month")
    return tp


def compute_annual_means(da):
    """Annual mean per grid cell."""
    return da.groupby("time.year").mean("time")


def compute_seasonal_means(da):
    """Seasonal mean per grid cell per year."""
    seasonal = {}
    for season_name, months in SEASONS.items():
        mask = da.time.dt.month.isin(months)
        s    = da.sel(time=mask).groupby("time.year").mean("time")
        seasonal[season_name] = s
    return seasonal


def compute_spatial_mean(da):
    """
    Area-weighted spatial mean over Nepal domain.
    Weights by cosine of latitude to correct for grid cell area.
    """
    weights = np.cos(np.deg2rad(da.latitude))
    return da.weighted(weights).mean(["latitude", "longitude"])


def save_timeseries(da, name, label):
    """Save spatially averaged annual time series to CSV."""
    annual = compute_annual_means(da)
    ts     = compute_spatial_mean(annual)
    df     = ts.to_dataframe().reset_index()
    # Keep only year and value columns
    df     = df[["year", ts.name]].copy()
    df.columns = ["year", label]
    out_path = os.path.join(PROCESSED_DIR, f"{name}_annual_timeseries.csv")
    df.to_csv(out_path, index=False)
    print(f"  Saved: {out_path}")
    return df


def save_seasonal_timeseries(da, name, label):
    """Save spatially averaged seasonal time series to CSV."""
    seasonal = compute_seasonal_means(da)
    records  = []
    for season_name, s in seasonal.items():
        ts  = compute_spatial_mean(s)
        df  = ts.to_dataframe().reset_index()
        df  = df[["year", ts.name]].copy()
        df.columns = ["year", label]
        df["season"] = season_name
        records.append(df)
    combined = pd.concat(records, ignore_index=True)
    out_path = os.path.join(PROCESSED_DIR, f"{name}_seasonal_timeseries.csv")
    combined.to_csv(out_path, index=False)
    print(f"  Saved: {out_path}")
    return combined


def save_gridded_trends_input(da, name):
    """
    Save per-grid-cell annual means as NetCDF for trend analysis.
    Each grid cell will get its own Mann-Kendall test in trend_analysis.py.
    """
    annual   = compute_annual_means(da)
    out_path = os.path.join(PROCESSED_DIR, f"{name}_annual_gridded.nc")
    annual.to_netcdf(out_path)
    print(f"  Saved: {out_path}")
    return annual


def main():
    print("=" * 60)
    print("ERA5 PREPROCESSING - NEPAL CLIMATE TRENDS")
    print("=" * 60)

    # Load and convert
    t2m = load_temperature()
    tp  = load_precipitation()

    print("\nComputing annual time series...")
    df_t2m = save_timeseries(t2m, "t2m", "temperature_C")
    df_tp  = save_timeseries(tp,  "tp",  "precipitation_mm")

    print("\nComputing seasonal time series...")
    df_t2m_s = save_seasonal_timeseries(t2m, "t2m", "temperature_C")
    df_tp_s  = save_seasonal_timeseries(tp,  "tp",  "precipitation_mm")

    print("\nSaving gridded annual means for trend analysis...")
    save_gridded_trends_input(t2m, "t2m")
    save_gridded_trends_input(tp,  "tp")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    t_series = df_t2m.set_index("year")["temperature_C"]
    p_series = df_tp.set_index("year")["precipitation_mm"]

    print(f"\nTemperature (Nepal spatial mean):")
    print(f"  1980s mean : {t_series[t_series.index < 1990].mean():.2f} degC")
    print(f"  2010s mean : {t_series[(t_series.index >= 2010) & (t_series.index < 2020)].mean():.2f} degC")
    print(f"  2020s mean : {t_series[t_series.index >= 2020].mean():.2f} degC")
    print(f"  Total range: {t_series.min():.2f} to {t_series.max():.2f} degC")

    print(f"\nPrecipitation (Nepal spatial mean, monthly):")
    print(f"  1980s mean : {p_series[p_series.index < 1990].mean():.1f} mm/month")
    print(f"  2010s mean : {p_series[(p_series.index >= 2010) & (p_series.index < 2020)].mean():.1f} mm/month")
    print(f"  Total range: {p_series.min():.1f} to {p_series.max():.1f} mm/month")

    print(f"\n✓ PREPROCESSING COMPLETE")
    print(f"  Files saved to: {PROCESSED_DIR}")
    print(f"\n[NEXT] Run: python src/trend_analysis.py")


if __name__ == "__main__":
    main()