"""Historical episodes for model validation.

Each episode pairs a configurable model scenario with **published** observed
market outcomes (with sources). The runner solves the scenario, extracts the
relevant metrics, and reports model-vs-observed.

If the model lands within ±30% of observed ranges, that is reasonable
calibration for a free-public-data model that doesn't include grade
differentials, futures expectations, or inventory dynamics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ObservedMetric:
    """A published quantitative observation about an episode.

    `value` may be a single number or a (low, high) tuple representing the
    range reported across sources or the period of interest.
    """

    value: float | tuple[float, float]
    unit: str
    source: str
    note: str = ""

    @property
    def low(self) -> float:
        return self.value[0] if isinstance(self.value, tuple) else self.value

    @property
    def high(self) -> float:
        return self.value[1] if isinstance(self.value, tuple) else self.value

    @property
    def mid(self) -> float:
        return 0.5 * (self.low + self.high)


@dataclass
class Episode:
    id: str
    name: str
    date: str
    description: str
    # Scenario passed to the API: same shape as web-UI scenarios.
    scenario: dict[str, Any] = field(default_factory=dict)
    # Observed metrics, keyed by metric_id. Currently used keys (model auto-checks):
    #   brent_change_usd        -> model's global_avg_price_delta_usd
    #   freight_premium_eu_usd  -> model's (NLD - SAU price) delta
    #   freight_premium_asia_usd-> model's (CHN - SAU price) delta
    #   cape_diverted_mbd       -> model's increase in satl_io flow vs base
    observed: dict[str, ObservedMetric] = field(default_factory=dict)
    notes: str = ""


EPISODES: list[Episode] = [
    # --------------------------------------------------------------------- #
    Episode(
        id="suez_2021",
        name="Ever Given Suez blockage",
        date="2021-03-23 to 2021-03-29 (6 days)",
        description=(
            "Container ship Ever Given runs aground and blocks the Suez Canal. "
            "SUMED pipeline keeps running (~2.5 mb/d capacity). The "
            "model treats this as steady-state, so it overstates the price "
            "impact of a 6-day disruption that markets expected would resolve."
        ),
        scenario={
            # Suez capacity in our data (10 mb/d) bundles canal + SUMED.
            # Drop to 2.5 mb/d for SUMED-only flow.
            "strait_capacity_overrides": {"suez": 2.5},
            # Short-run rigid demand (days-weeks horizon).
            "demand_elasticity": 0.05,
            # Modest freight stress during 6-day uncertainty.
            "ship_day_cost_usd_per_bbl": 1.3,
        },
        observed={
            "brent_change_usd": ObservedMetric(
                value=(2.0, 4.0),
                unit="USD/bbl",
                source="EIA STEO Apr 2021; Reuters 2021-03-25",
                note="Brent rose ~$3 from Mar 22 to Mar 24 ($61 -> $64-65)",
            ),
            "avg_freight_premium_usd": ObservedMetric(
                value=(0.5, 1.5),
                unit="USD/bbl",
                source="Baltic Exchange TD3 reports; S&P Platts",
                note="VLCC AG-Europe Worldscale jumped from WS40 to WS60",
            ),
        },
        notes=(
            "Real markets priced in expected resolution within days, so "
            "Brent's spike was muted. Our steady-state model assumes "
            "indefinite disruption — expect the modeled premium to exceed "
            "observed by 2-4x. That's a feature: the model bounds the "
            "what-if 'never reopens' tail risk."
        ),
    ),
    # --------------------------------------------------------------------- #
    Episode(
        id="russia_2022",
        name="Russia sanctions, rerouting begins",
        date="2022-Q2 (post-invasion, pre-EU-embargo)",
        description=(
            "Russian seaborne crude redirects from Europe to India and China "
            "after the Feb 24 invasion. Production drops ~600 kb/d. Tanker "
            "voyages lengthen as Asia replaces Europe as primary buyer."
        ),
        scenario={
            "country_production_overrides": {"RUS": 9.5},
            # Danish Straits transits to Western Europe drop sharply
            "strait_capacity_overrides": {"danish_straits": 1.5},
            # Short-run inelastic with sustained dislocation
            "demand_elasticity": 0.08,
            # Tanker rates rose ~70% in Q2 2022
            "ship_day_cost_usd_per_bbl": 1.7,
        },
        observed={
            "brent_change_usd": ObservedMetric(
                value=(10.0, 25.0),
                unit="USD/bbl",
                source="ICE Brent settlements; EIA STEO 2022",
                note="Brent went from ~$90 in mid-Feb to $100-115 sustained Q2",
            ),
            "avg_freight_premium_usd": ObservedMetric(
                value=(2.0, 5.0),
                unit="USD/bbl",
                source="Baltic Exchange BDTI 2022",
                note="VLCC dirty rates rose 50-100%",
            ),
        },
        notes=(
            "We cannot model the Urals-Brent grade discount (no grade "
            "differentiation in v1). The scenario captures supply tightening "
            "and route lengthening, which are the freight-price components."
        ),
    ),
    # --------------------------------------------------------------------- #
    Episode(
        id="red_sea_2024",
        name="Red Sea / Bab-el-Mandeb crisis",
        date="2024-Q1",
        description=(
            "Houthi attacks on Red Sea shipping force ~50% of Suez and "
            "Bab el-Mandeb tanker traffic to reroute around the Cape of "
            "Good Hope, adding 10-14 days to Asia-Europe voyages."
        ),
        scenario={
            "strait_capacity_overrides": {
                "bab_el_mandeb": 3.0,   # ~33% of nominal
                "suez": 4.5,            # ~45% of nominal (incl. SUMED)
            },
            "demand_elasticity": 0.07,
            # VLCC rates roughly tripled on Asia-Europe routes
            "ship_day_cost_usd_per_bbl": 2.2,
        },
        observed={
            "brent_change_usd": ObservedMetric(
                value=(3.0, 7.0),
                unit="USD/bbl",
                source="EIA STEO Mar 2024; Bloomberg energy desk",
                note="Modest spike attributable also to Middle East tensions",
            ),
            "avg_freight_premium_usd": ObservedMetric(
                value=(2.0, 4.0),
                unit="USD/bbl",
                source="Baltic Exchange TD3/TD20 reports Q1 2024",
                note="VLCC AG-Europe rates rose from ~$2 to ~$6/bbl",
            ),
            "cape_diverted_mbd": ObservedMetric(
                value=(1.5, 3.0),
                unit="mb/d",
                source="EIA, Vortexa, Kpler tracker reports Q1 2024",
                note="Additional Cape of Good Hope traffic",
            ),
        },
        notes=(
            "The single best-documented modern shock and the closest fit "
            "to a v1 model: pure capacity reduction with no supply/demand "
            "shift, well-quantified by ship-tracking data."
        ),
    ),
]
