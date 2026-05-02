"""Bilateral trade-flow constraints for the LP.

We don't have an exporter→importer flow variable in the basin graph; the LP
operates on edge flows. To anchor base-case routing to observed bilateral
patterns (UN Comtrade-style), we:

  1. For each (origin, destination) pair with observed mb/d, compute the
     transit-time shortest path through the country+basin graph.
  2. Attribute the bilateral flow to every edge on that path.
  3. Sum across all bilateral records to produce `expected_flow_per_edge`.
  4. The LP gets a quadratic penalty `mu * (x_e - expected_e)^2` summed over
     edges, which biases base routing toward observed patterns while still
     allowing deviation under capacity shocks.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import pandas as pd


@dataclass(frozen=True)
class BilateralFlow:
    exporter: str
    importer: str
    mbd: float
    source: str = ""


def load_bilateral(path: Path) -> list[BilateralFlow]:
    df = pd.read_csv(path)
    return [
        BilateralFlow(
            exporter=r["exporter"],
            importer=r["importer"],
            mbd=float(r["mbd"]),
            source=str(r.get("source", "")),
        )
        for r in df.to_dict(orient="records")
    ]


def expected_edge_flows(
    g: nx.DiGraph, bilateral: list[BilateralFlow]
) -> dict[tuple[str, str], float]:
    """Per-edge expected mb/d derived from bilateral flows + shortest paths.

    Uses transit_days as the edge weight. Walks each (exporter, importer)
    pair's shortest path and credits the bilateral mb/d to every traversed
    edge. Edges not on any path get expected_flow = 0.

    Pairs that fail to route (graph disconnected — e.g., a country mentioned
    in bilateral.csv that isn't in the current scenario's graph) are skipped.
    """
    expected: dict[tuple[str, str], float] = {}
    for bf in bilateral:
        if bf.exporter not in g or bf.importer not in g:
            continue
        try:
            path = nx.shortest_path(
                g, source=bf.exporter, target=bf.importer, weight="transit_days"
            )
        except nx.NetworkXNoPath:
            continue
        for i in range(len(path) - 1):
            e = (path[i], path[i + 1])
            expected[e] = expected.get(e, 0.0) + bf.mbd
    return expected
