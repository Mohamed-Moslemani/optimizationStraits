from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import pandas as pd


@dataclass(frozen=True)
class Country:
    iso3: str
    name: str
    production_mbd: float = 0.0
    consumption_mbd: float = 0.0


@dataclass(frozen=True)
class Basin:
    basin_id: str
    name: str


@dataclass(frozen=True)
class Coastline:
    iso3: str
    basin_id: str


@dataclass(frozen=True)
class Strait:
    strait_id: str
    name: str
    basin_a: str
    basin_b: str
    kind: str           # "chokepoint" or "open"
    capacity_mbd: float
    distance_nm: float
    transit_days: float


COASTAL_ACCESS_COST = 0.25  # ship-days, lump for port -> basin entry
COASTAL_CAPACITY = 999.0    # mb/d, effectively unbounded


def build_oil_graph(
    countries: list[Country],
    basins: list[Basin],
    coastlines: list[Coastline],
    straits: list[Strait],
) -> nx.DiGraph:
    """Build the directed oil-trade graph.

    Node types:
      - country nodes (iso3): have 'supply' = max(prod - cons, 0)
                                       'demand' = max(cons - prod, 0)
      - basin nodes  (basin_id, prefixed 'b:'): pure transshipment, supply=demand=0

    Edge types:
      - country <-> basin: 'coastal', small cost, unbounded capacity
      - basin   <-> basin: 'strait', transit_days cost, strait capacity
    """
    g = nx.DiGraph()

    for c in countries:
        supply = max(c.production_mbd - c.consumption_mbd, 0.0)
        demand = max(c.consumption_mbd - c.production_mbd, 0.0)
        g.add_node(
            c.iso3,
            kind="country",
            name=c.name,
            supply=supply,
            demand=demand,
            production_mbd=c.production_mbd,
            consumption_mbd=c.consumption_mbd,
        )

    for b in basins:
        g.add_node(
            _bkey(b.basin_id),
            kind="basin",
            name=b.name,
            supply=0.0,
            demand=0.0,
        )

    country_ids = {c.iso3 for c in countries}
    basin_ids = {b.basin_id for b in basins}
    # Coastal edges are *directional* by country role: a net exporter only pushes
    # outbound (country -> basin); a net importer only pulls inbound (basin ->
    # country). This prevents countries from acting as free land bridges between
    # two basins they happen to both touch (e.g., Oman bypassing Hormuz).
    for coast in coastlines:
        if coast.iso3 not in country_ids:
            raise ValueError(
                f"coastlines.csv references unknown country {coast.iso3!r}"
            )
        if coast.basin_id not in basin_ids:
            raise ValueError(
                f"coastlines.csv references unknown basin {coast.basin_id!r}"
            )
        b = _bkey(coast.basin_id)
        node_data = g.nodes[coast.iso3]
        attrs = dict(
            kind="coastal",
            name=f"{coast.iso3}-{coast.basin_id}",
            capacity=COASTAL_CAPACITY,
            transit_days=COASTAL_ACCESS_COST,
            distance_nm=0.0,
        )
        if node_data["supply"] > 0:
            g.add_edge(coast.iso3, b, **attrs)
        if node_data["demand"] > 0:
            g.add_edge(b, coast.iso3, **attrs)

    for s in straits:
        a, b = _bkey(s.basin_a), _bkey(s.basin_b)
        attrs = dict(
            kind="strait",
            strait_id=s.strait_id,
            name=s.name,
            strait_kind=s.kind,
            capacity=s.capacity_mbd,
            transit_days=s.transit_days,
            distance_nm=s.distance_nm,
        )
        g.add_edge(a, b, **attrs)
        g.add_edge(b, a, **attrs)

    return g


def _bkey(basin_id: str) -> str:
    return f"b:{basin_id}"


def balance_supply_demand(g: nx.DiGraph, slack_node: str = "SAU") -> nx.DiGraph:
    """Scale supply so world supply == world demand.

    Real-world data won't perfectly balance (inventory changes, NGLs, measurement
    noise, sanctions-era dark flows). We scale supply to match demand, which keeps
    relative producer shares intact. The LP needs balanced sources/sinks.
    """
    supply_total = sum(d["supply"] for _, d in g.nodes(data=True))
    demand_total = sum(d["demand"] for _, d in g.nodes(data=True))
    if supply_total == 0 or demand_total == 0:
        return g
    scale = demand_total / supply_total
    for _, d in g.nodes(data=True):
        d["supply"] *= scale
    return g


def load_countries(path: Path) -> list[Country]:
    df = pd.read_csv(path)
    return [
        Country(
            iso3=r["iso3"],
            name=r["name"],
            production_mbd=float(r["production_mbd"]),
            consumption_mbd=float(r["consumption_mbd"]),
        )
        for r in df.to_dict(orient="records")
    ]


def load_basins(path: Path) -> list[Basin]:
    df = pd.read_csv(path)
    return [Basin(basin_id=r["basin_id"], name=r["name"]) for r in df.to_dict(orient="records")]


def load_coastlines(path: Path) -> list[Coastline]:
    df = pd.read_csv(path)
    return [
        Coastline(iso3=r["iso3"], basin_id=r["basin_id"])
        for r in df.to_dict(orient="records")
    ]


def load_straits(path: Path) -> list[Strait]:
    df = pd.read_csv(path)
    return [
        Strait(
            strait_id=r["strait_id"],
            name=r["name"],
            basin_a=r["basin_a"],
            basin_b=r["basin_b"],
            kind=r["kind"],
            capacity_mbd=float(r["capacity_mbd"]),
            distance_nm=float(r["distance_nm"]),
            transit_days=float(r["transit_days"]),
        )
        for r in df.to_dict(orient="records")
    ]
