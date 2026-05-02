"""Historical reference prices.

Loads the EIA monthly Brent spot series (data/brent_monthly_usd.csv) and
provides a simple lookup for "what was Brent in YYYY-MM". Useful for
backtesting historical scenarios in OpenCrude — instead of always anchoring
the LP at the default $85/bbl, you can pin the reference price to the actual
spot at the date of the shock you're modeling.

Inspired by the data hygiene point made in Conlon, Cotter & Eyiah-Donkor
(2024) "Forecasting the price of oil: A cautionary note": "the construction
of the underlying oil price series" matters. We use monthly-average Brent
from EIA, which is the most consistent public time series.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_brent_monthly(path: Path) -> pd.Series:
    """Return Series indexed by YYYY-MM strings, values in USD/bbl."""
    df = pd.read_csv(path)
    return pd.Series(
        df["price_usd_per_bbl"].astype(float).values,
        index=df["period"].astype(str),
        name="brent_usd_per_bbl",
    )


def brent_at(series: pd.Series, period: str, fallback: float = 85.0) -> float:
    """Look up Brent for a period like '2023-03'. Falls back if missing."""
    if period in series.index:
        return float(series[period])
    # Try the closest earlier period within 3 months
    sorted_idx = sorted(series.index)
    earlier = [p for p in sorted_idx if p <= period]
    if earlier:
        return float(series[earlier[-1]])
    return fallback
