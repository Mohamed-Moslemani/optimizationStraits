"""Historical reference series (prices + activity).

Two monthly time series, both with very simple "look up by YYYY-MM" loaders:

  - data/brent_monthly_usd.csv         EIA Europe Brent spot (USD/bbl)
  - data/kilian_igrea_monthly.csv      Kilian's Index of Global Real Economic
                                        Activity (deviation-from-trend %).
                                        Standard demand-side proxy in the oil
                                        macro literature.

Honors the data-hygiene point of Conlon, Cotter & Eyiah-Donkor (2024)
"Forecasting the price of oil: A cautionary note": which underlying series
you use materially changes results.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _load_period_series(path: Path, value_col: str) -> pd.Series:
    df = pd.read_csv(path)
    return pd.Series(
        df[value_col].astype(float).values,
        index=df["period"].astype(str),
        name=value_col,
    )


def load_brent_monthly(path: Path) -> pd.Series:
    """Return Series indexed by YYYY-MM, values in USD/bbl."""
    return _load_period_series(path, "price_usd_per_bbl")


def load_kilian_monthly(path: Path) -> pd.Series:
    """Return Series indexed by YYYY-MM, values in deviation-from-trend %.

    Negative = below-trend global real activity (recession-like).
    Positive = above-trend (boom). Std-dev historically ~30.
    """
    return _load_period_series(path, "igrea_index")


def _at(series: pd.Series, period: str, fallback: float) -> float:
    if period in series.index:
        return float(series[period])
    sorted_idx = sorted(series.index)
    earlier = [p for p in sorted_idx if p <= period]
    if earlier:
        return float(series[earlier[-1]])
    return fallback


def brent_at(series: pd.Series, period: str, fallback: float = 85.0) -> float:
    """Look up Brent for a period like '2023-03'. Falls back if missing."""
    return _at(series, period, fallback)


def kilian_at(series: pd.Series, period: str, fallback: float = 0.0) -> float:
    """Look up IGREA for a period like '2022-05'. Falls back if missing."""
    return _at(series, period, fallback)


def kilian_demand_scale(igrea_value: float, sensitivity: float = 0.001) -> float:
    """Convert a Kilian index value to an *optional* demand scaling factor.

    Rough rule of thumb based on oil-demand elasticity to global activity:
    a 1-std-dev deviation (~30 IGREA) translates to ~3% demand deviation,
    so default sensitivity = 0.03 / 30 = 0.001 per IGREA point. The sign is
    intuitive: positive activity → above-trend demand → factor > 1.

    Returns a multiplicative factor; multiply each country's consumption_mbd
    by this to obtain a demand level appropriate for the historical month.
    """
    return 1.0 + sensitivity * float(igrea_value)
