"""
visualise.py
Publication-quality figures for Nepal ERA5 climate trend analysis.

Fig 1 - Annual temperature and precipitation time series with trend lines
Fig 2 - Seasonal temperature trends (4-panel)
Fig 3 - Spatial temperature trend map (Mann-Kendall slope, significance stippling)
Fig 4 - Spatial precipitation trend map
Fig 5 - Warming rate comparison by season (bar chart with significance markers)
"""

import os
import warnings
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import geopandas as gpd
from scipy import stats

warnings.filterwarnings("ignore")

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
RESULTS_DIR   = os.path.join(os.path.dirname(__file__), "..", "outputs", "results")
FIGURES_DIR   = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["figure.dpi"]  = 130

SEASON_COLORS = {
    "Pre-monsoon (MAM)":  "#f4a261",
    "Monsoon (JJAS)":     "#2a9d8f",
    "Post-monsoon (ON)":  "#e76f51",
    "Winter (DJF)":       "#457b9d",
}

IPCC_PERIODS = {
    "Pre-AR4":  (1980, 2007),
    "AR4":      (2007, 2013),
    "AR5":      (2013, 2021),
    "Post-AR6": (2021, 2024),
}


def theil_sen(values, years):
    """Return slope and intercept from Theil-Sen estimator (scipy v1.7+)."""
    result    = stats.theilslopes(values, years)
    slope     = result.slope
    intercept = result.intercept
    return slope, intercept


def add_trend_line(ax, years, values, color="red", lw=2):
    """Add Theil-Sen trend line to axis."""
    slope, intercept = theil_sen(values, years)
    y_trend = slope * years + intercept
    ax.plot(years, y_trend, color=color, lw=lw, linestyle="--",
            label=f"Trend: {slope*10:+.3f}/decade")
    return slope


# ── Fig 1: Annual time series ─────────────────────────────────
def fig1_annual_timeseries():
    t2m_df = pd.read_csv(os.path.join(PROCESSED_DIR, "t2m_annual_timeseries.csv"))
    tp_df  = pd.read_csv(os.path.join(PROCESSED_DIR, "tp_annual_timeseries.csv"))

    fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=True)

    # Temperature
    ax    = axes[0]
    years = t2m_df["year"].values
    temps = t2m_df["temperature_C"].values
    ax.fill_between(years, temps, temps.mean(),
                    where=temps > temps.mean(),
                    alpha=0.4, color="#e63946", label="Above mean")
    ax.fill_between(years, temps, temps.mean(),
                    where=temps <= temps.mean(),
                    alpha=0.4, color="#457b9d", label="Below mean")
    ax.plot(years, temps, color="#1d3557", lw=1.5, alpha=0.8)
    add_trend_line(ax, years, temps, color="#e63946", lw=2.5)
    ax.axhline(temps.mean(), color="grey", lw=0.8, linestyle=":")

    for year, label in [(2007, "AR4"), (2013, "AR5"), (2021, "AR6")]:
        ax.axvline(year, color="grey", lw=1.0, linestyle="--", alpha=0.6)
        ax.text(year + 0.2, temps.max() * 0.995, label, fontsize=7.5,
                color="grey", rotation=90, va="top")

    ax.set_ylabel("Temperature (°C)", fontsize=12)
    ax.set_title(
        "Nepal Mean Annual Temperature (1980-2023) - ERA5 Reanalysis\n"
        "Mann-Kendall: τ=0.393, p=0.0002, slope=+0.211°C/decade, total change=+0.908°C",
        fontsize=11, fontweight="bold"
    )
    ax.legend(loc="upper left", fontsize=8, ncol=3)
    ax.grid(True, alpha=0.3)

    # Precipitation
    ax    = axes[1]
    years = tp_df["year"].values
    prec  = tp_df["precipitation_mm"].values
    ax.bar(years, prec,
           color=np.where(prec > prec.mean(), "#2a9d8f", "#e9c46a"),
           alpha=0.75, width=0.8, label="Annual mean precipitation")
    add_trend_line(ax, years, prec, color="#264653", lw=2.5)
    ax.axhline(prec.mean(), color="grey", lw=0.8, linestyle=":")

    for year, label in [(2007, "AR4"), (2013, "AR5"), (2021, "AR6")]:
        ax.axvline(year, color="grey", lw=1.0, linestyle="--", alpha=0.6)
        ax.text(year + 0.2, prec.max() * 0.98, label, fontsize=7.5,
                color="grey", rotation=90, va="top")

    ax.set_ylabel("Precipitation (mm/month)", fontsize=12)
    ax.set_xlabel("Year", fontsize=12)
    ax.set_title(
        "Nepal Mean Annual Precipitation (1980-2023) - ERA5 Reanalysis\n"
        "Mann-Kendall: τ=0.243, p=0.021, slope=+0.113 mm/month/decade",
        fontsize=11, fontweight="bold"
    )
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(1979, 2024)

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "fig1_annual_timeseries.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Fig 1 saved")


# ── Fig 2: Seasonal trends ────────────────────────────────────
def fig2_seasonal_trends():
    t2m_s      = pd.read_csv(os.path.join(PROCESSED_DIR, "t2m_seasonal_timeseries.csv"))
    tp_s       = pd.read_csv(os.path.join(PROCESSED_DIR, "tp_seasonal_timeseries.csv"))
    t2m_trends = pd.read_csv(os.path.join(RESULTS_DIR,   "t2m_seasonal_trends.csv"))
    tp_trends  = pd.read_csv(os.path.join(RESULTS_DIR,   "tp_seasonal_trends.csv"))

    seasons = [
        "Pre-monsoon (MAM)", "Monsoon (JJAS)",
        "Post-monsoon (ON)", "Winter (DJF)"
    ]

    fig, axes = plt.subplots(2, 4, figsize=(16, 9))

    for col, season in enumerate(seasons):
        color = SEASON_COLORS[season]

        # Temperature row
        ax  = axes[0, col]
        sub = t2m_s[t2m_s["season"] == season].sort_values("year")
        yrs = sub["year"].values
        val = sub["temperature_C"].values
        ax.plot(yrs, val, color=color, lw=1.5, alpha=0.8)
        ax.fill_between(yrs, val, val.mean(), alpha=0.25, color=color)
        slope, intercept = theil_sen(val, yrs)
        ax.plot(yrs, slope * yrs + intercept, "k--", lw=1.5)

        row = t2m_trends[t2m_trends["season"] == season].iloc[0]
        p   = row["mk_pvalue"]
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        ax.set_title(f"{season}\n{slope*10:+.3f}°C/decade {sig}",
                     fontsize=9, fontweight="bold", color=color)
        ax.set_ylabel("Temperature (°C)" if col == 0 else "", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis="x", rotation=30, labelsize=7)

        # Precipitation row
        ax2  = axes[1, col]
        sub2 = tp_s[tp_s["season"] == season].sort_values("year")
        yrs2 = sub2["year"].values
        val2 = sub2["precipitation_mm"].values
        ax2.bar(yrs2, val2, color=color, alpha=0.6, width=0.8)
        slope2, intercept2 = theil_sen(val2, yrs2)
        ax2.plot(yrs2, slope2 * yrs2 + intercept2, "k--", lw=1.5)

        row2 = tp_trends[tp_trends["season"] == season].iloc[0]
        p2   = row2["mk_pvalue"]
        sig2 = "***" if p2 < 0.001 else "**" if p2 < 0.01 else "*" if p2 < 0.05 else "ns"
        ax2.set_title(f"{slope2*10:+.4f} mm/mo/decade {sig2}",
                      fontsize=8, color=color)
        ax2.set_ylabel("Precip. (mm/month)" if col == 0 else "", fontsize=9)
        ax2.set_xlabel("Year", fontsize=8)
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis="x", rotation=30, labelsize=7)

    plt.suptitle(
        "Seasonal Climate Trends - Nepal ERA5 (1980-2023)\n"
        "Theil-Sen slope (dashed) | *** p<0.001, ** p<0.01, * p<0.05, ns not significant",
        fontsize=12, fontweight="bold"
    )
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "fig2_seasonal_trends.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Fig 2 saved")


# ── Fig 3 and 4: Spatial trend maps ──────────────────────────
def fig_spatial_trend(nc_path, title, units, cmap, fig_name,
                      vmin=None, vmax=None, center=None):
    ds    = xr.open_dataset(nc_path)
    slope = ds["slope"]
    sig   = ds["significant"]
    lats  = slope.latitude.values
    lons  = slope.longitude.values

    if center is not None:
        norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=center, vmax=vmax)
    else:
        norm = None

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax_idx, (ax, show_sig) in enumerate(zip(axes, [False, True])):
        im = ax.pcolormesh(
            lons, lats, slope.values,
            cmap=cmap, norm=norm,
            vmin=vmin if norm is None else None,
            vmax=vmax if norm is None else None,
            shading="auto"
        )

        if show_sig:
            sig_vals = sig.values
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if sig_vals[i, j] < 0.5:
                        ax.plot(lon, lat, "x", color="grey",
                                markersize=4, alpha=0.5, markeredgewidth=0.8)
            ax.set_title("With significance stippling\n(x = p > 0.05, not significant)",
                         fontsize=10)
        else:
            ax.set_title("Trend magnitude (all grid cells)", fontsize=10)

        # Nepal boundary box
        ax.plot([80.0, 88.5, 88.5, 80.0, 80.0],
                [26.0, 26.0, 30.5, 30.5, 26.0],
                "k-", lw=1.5, alpha=0.8)

        ax.set_xlabel("Longitude (°E)", fontsize=10)
        ax.set_ylabel("Latitude (°N)" if ax_idx == 0 else "", fontsize=10)
        ax.set_xlim(79.5, 89.0)
        ax.set_ylim(25.5, 31.0)
        ax.grid(True, alpha=0.2, linestyle=":")

        cb = plt.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
        cb.set_label(units, fontsize=9)

    plt.suptitle(
        f"{title}\nERA5 Monthly Reanalysis | Mann-Kendall Test | 1980-2023 (44 years)",
        fontsize=12, fontweight="bold"
    )
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, fig_name)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {fig_name} saved")


# ── Fig 5: Seasonal summary bar chart ────────────────────────
def fig5_seasonal_summary():
    t2m_trends = pd.read_csv(os.path.join(RESULTS_DIR, "t2m_seasonal_trends.csv"))
    tp_trends  = pd.read_csv(os.path.join(RESULTS_DIR, "tp_seasonal_trends.csv"))

    seasons = [
        "Annual",
        "Pre-monsoon (MAM)", "Monsoon (JJAS)",
        "Post-monsoon (ON)", "Winter (DJF)"
    ]

    annual_t = pd.DataFrame([{
        "season": "Annual", "slope_per_decade": 0.2111,
        "mk_pvalue": 0.0002, "significant": True
    }])
    annual_p = pd.DataFrame([{
        "season": "Annual", "slope_per_decade": 0.1126,
        "mk_pvalue": 0.0205, "significant": True
    }])

    t2m_all = pd.concat([annual_t, t2m_trends], ignore_index=True)
    tp_all  = pd.concat([annual_p, tp_trends],  ignore_index=True)

    colors_all = ["#264653"] + [SEASON_COLORS[s] for s in list(SEASON_COLORS.keys())]

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))

    # Temperature panel
    ax   = axes[0]
    bars = ax.barh(
        range(len(seasons)),
        t2m_all["slope_per_decade"].values,
        color=colors_all, alpha=0.85, edgecolor="white", height=0.65
    )
    ax.set_yticks(range(len(seasons)))
    ax.set_yticklabels(seasons, fontsize=10)
    ax.axvline(0, color="black", lw=0.8)

    for bar, row in zip(bars, t2m_all.itertuples()):
        p   = row.mk_pvalue
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        x   = bar.get_width()
        ax.text(x + 0.005, bar.get_y() + bar.get_height()/2,
                f"{x:+.4f} {sig}", va="center", fontsize=9)

    ax.set_xlabel("Temperature trend (°C/decade)", fontsize=11)
    ax.set_title("Temperature Warming Rate by Season\n(°C/decade, Theil-Sen slope)",
                 fontsize=11, fontweight="bold")
    ax.grid(axis="x", alpha=0.3)
    ax.set_xlim(-0.05, 0.60)

    # Precipitation panel
    ax2   = axes[1]
    bars2 = ax2.barh(
        range(len(seasons)),
        tp_all["slope_per_decade"].values,
        color=colors_all, alpha=0.85, edgecolor="white", height=0.65
    )
    ax2.set_yticks(range(len(seasons)))
    ax2.set_yticklabels(seasons, fontsize=10)
    ax2.axvline(0, color="black", lw=0.8)

    for bar, row in zip(bars2, tp_all.itertuples()):
        p      = row.mk_pvalue
        sig    = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        x      = bar.get_width()
        offset = 0.005 if x >= 0 else -0.030
        ax2.text(x + offset, bar.get_y() + bar.get_height()/2,
                 f"{x:+.4f} {sig}", va="center", fontsize=9)

    ax2.set_xlabel("Precipitation trend (mm/month/decade)", fontsize=11)
    ax2.set_title("Precipitation Trend by Season\n(mm/month/decade, Theil-Sen slope)",
                  fontsize=11, fontweight="bold")
    ax2.grid(axis="x", alpha=0.3)

    plt.suptitle(
        "Nepal Climate Trend Summary by Season (1980-2023)\n"
        "ERA5 Reanalysis | Mann-Kendall | *** p<0.001, ** p<0.01, * p<0.05, ns not significant",
        fontsize=12, fontweight="bold"
    )
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "fig5_seasonal_summary.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Fig 5 saved")


# ── Main ──────────────────────────────────────────────────────
def main():
    print("Generating figures...\n")

    fig1_annual_timeseries()
    fig2_seasonal_trends()
    fig_spatial_trend(
        nc_path=os.path.join(RESULTS_DIR, "t2m_trend_maps.nc"),
        title="Nepal Temperature Trend (1980-2023)",
        units="°C/decade", cmap="RdYlBu_r",
        fig_name="fig3_t2m_spatial_trend.png",
        vmin=-0.1, vmax=0.6, center=0.0
    )
    fig_spatial_trend(
        nc_path=os.path.join(RESULTS_DIR, "tp_trend_maps.nc"),
        title="Nepal Precipitation Trend (1980-2023)",
        units="mm/month/decade", cmap="BrBG",
        fig_name="fig4_tp_spatial_trend.png",
        vmin=-0.3, vmax=0.3, center=0.0
    )
    fig5_seasonal_summary()

    print(f"\n✓ ALL FIGURES SAVED → {FIGURES_DIR}")
    print(f"  fig1_annual_timeseries.png     - Annual T and P trends")
    print(f"  fig2_seasonal_trends.png       - 4-season panel T and P")
    print(f"  fig3_t2m_spatial_trend.png     - Temperature spatial trend map")
    print(f"  fig4_tp_spatial_trend.png      - Precipitation spatial trend map")
    print(f"  fig5_seasonal_summary.png      - Seasonal warming rate summary")


if __name__ == "__main__":
    main()