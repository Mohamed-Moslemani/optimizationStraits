from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import pandas as pd


@dataclass(frozen=True)
class Country:
    code: str
    name: str
    supply: float = 0.0
    demand: float = 0.0


@dataclass(frozen=True)
class Strait:
    name: str
    endpoints: tuple[str, str]
    capacity: float
    distance_nm: float
    transit_days: float


def build_graph(
    countries: list[Country], straits: list[Strait]
) -> nx.DiGraph:
    g = nx.DiGraph()
    for c in countries:
        g.add_node(c.code, name=c.name, supply=c.supply, demand=c.demand)
    for s in straits:
        u, v = s.endpoints
        attrs = dict(
            name=s.name,
            capacity=s.capacity,
            distance_nm=s.distance_nm,
            transit_days=s.transit_days,
        )
        g.add_edge(u, v, **attrs)
        g.add_edge(v, u, **attrs)
    return g


def load_countries(path: Path) -> list[Country]:
    df = pd.read_csv(path)
    return [Country(**row) for row in df.to_dict(orient="records")]


def load_straits(path: Path) -> list[Strait]:
    df = pd.read_csv(path)
    return [
        Strait(
            name=r["name"],
            endpoints=(r["endpoint_a"], r["endpoint_b"]),
            capacity=r["capacity"],
            distance_nm=r["distance_nm"],
            transit_days=r["transit_days"],
        )
        for r in df.to_dict(orient="records")
    ]
