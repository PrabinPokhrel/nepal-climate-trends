"""
download_era5.py
Downloads ERA5 monthly averaged surface data for Nepal (1980-2023).

Variables:
  - 2m air temperature (t2m)
  - Total precipitation (tp)

Spatial extent: Nepal bounding box (26N-30.5N, 80E-88.5E)
Temporal extent: 1980-2023 (44 years)
Resolution: 0.25 degrees (~28km)

Source: ERA5 monthly averaged data on single levels
        Copernicus Climate Data Store (CDS)
        https://cds.climate.copernicus.eu
"""

import os
import cdsapi

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(OUT_DIR, exist_ok=True)

# Nepal bounding box: North, West, South, East
NEPAL_BBOX = [30.5, 80.0, 26.0, 88.5]

YEARS  = [str(y) for y in range(1980, 2024)]
MONTHS = [f"{m:02d}" for m in range(1, 13)]


def download_variable(variable, short_name):
    """Download one ERA5 variable for all years and months."""
    out_path = os.path.join(OUT_DIR, f"era5_{short_name}_1980_2023.nc")

    if os.path.exists(out_path):
        print(f"  Already exists: {out_path} - skipping download")
        return out_path

    print(f"\nDownloading ERA5 {variable} (1980-2023)...")
    print(f"  Years : 1980-2023 ({len(YEARS)} years)")
    print(f"  Months: all 12 months")
    print(f"  Area  : Nepal ({NEPAL_BBOX})")
    print(f"  Output: {out_path}")
    print(f"  Estimated size: 50-150 MB")
    print(f"  Estimated time: 5-15 minutes\n")

    c = cdsapi.Client()

    c.retrieve(
        "reanalysis-era5-single-levels-monthly-means",
        {
            "product_type": "monthly_averaged_reanalysis",
            "variable":     [variable],
            "year":         YEARS,
            "month":        MONTHS,
            "time":         "00:00",
            "area":         NEPAL_BBOX,
            "format":       "netcdf",
        },
        out_path
    )

    print(f"\n✓ Downloaded → {out_path}")
    return out_path


def main():
    print("=" * 60)
    print("ERA5 DATA DOWNLOAD - NEPAL CLIMATE TRENDS")
    print("=" * 60)

    # Download temperature
    download_variable("2m_temperature", "t2m")

    # Download precipitation
    download_variable("total_precipitation", "tp")

    print("\n" + "=" * 60)
    print("✓ DOWNLOAD COMPLETE")
    print(f"  Files saved to: {OUT_DIR}")
    print(f"  era5_t2m_1980_2023.nc  - 2m air temperature")
    print(f"  era5_tp_1980_2023.nc   - Total precipitation")
    print("\n[NEXT] Run: python src/preprocess.py")


if __name__ == "__main__":
    main()