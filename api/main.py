"""FastAPI backend for the straitgraph interactive UI.

Endpoints:
  GET  /world     - static snapshot of countries, basins, straits with coordinates
  POST /solve     - accept a scenario (capacity overrides, supply/demand overrides,
                    strait closures) and return the LP solution with flows, duals,
                    and strait-importance ranking
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from straitgraph import (
    balance_supply_demand,
    build_oil_graph,
    load_basins,
    load_coastlines,
    load_countries,
    load_straits,
    solve_market,
    strait_importance,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@lru_cache(maxsize=1)
def _raw_data():
    return (
        load_countries(DATA_DIR / "countries.csv"),
        load_basins(DATA_DIR / "basins.csv"),
        load_coastlines(DATA_DIR / "coastlines.csv"),
        load_straits(DATA_DIR / "straits.csv"),
    )


app = FastAPI(title="straitgraph API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    # (API itself runs on :8005 — see README)
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Scenario(BaseModel):
    """Edits applied on top of the base dataset before solving."""

    strait_capacity_overrides: dict[str, float] = Field(default_factory=dict)
    closed_straits: list[str] = Field(default_factory=list)
    country_production_overrides: dict[str, float] = Field(default_factory=dict)
    country_consumption_overrides: dict[str, float] = Field(default_factory=dict)


class FlowDTO(BaseModel):
    source: str
    target: str
    mbd: float
    kind: str
    strait_id: str | None = None


class SolutionDTO(BaseModel):
    status: str
    total_cost: float
    total_supply: float
    total_demand: float
    flows: list[FlowDTO]
    strait_flows: dict[str, float]
    node_prices: dict[str, float]
    capacity_duals: dict[str, float]
    strait_importance: dict[str, float | None]


class CountryDTO(BaseModel):
    iso3: str
    name: str
    production_mbd: float
    consumption_mbd: float
    net_mbd: float
    lat: float
    lon: float


class BasinDTO(BaseModel):
    basin_id: str
    name: str
    lat: float
    lon: float


class StraitDTO(BaseModel):
    strait_id: str
    name: str
    basin_a: str
    basin_b: str
    kind: str
    capacity_mbd: float
    distance_nm: float
    transit_days: float


class CoastlineDTO(BaseModel):
    iso3: str
    basin_id: str


class WorldDTO(BaseModel):
    countries: list[CountryDTO]
    basins: list[BasinDTO]
    coastlines: list[CoastlineDTO]
    straits: list[StraitDTO]


@app.get("/world", response_model=WorldDTO)
def get_world() -> WorldDTO:
    countries, basins, coastlines, straits = _raw_data()
    return WorldDTO(
        countries=[
            CountryDTO(
                iso3=c.iso3,
                name=c.name,
                production_mbd=c.production_mbd,
                consumption_mbd=c.consumption_mbd,
                net_mbd=c.production_mbd - c.consumption_mbd,
                lat=c.lat,
                lon=c.lon,
            )
            for c in countries
        ],
        basins=[
            BasinDTO(basin_id=b.basin_id, name=b.name, lat=b.lat, lon=b.lon)
            for b in basins
        ],
        coastlines=[
            CoastlineDTO(iso3=cl.iso3, basin_id=cl.basin_id) for cl in coastlines
        ],
        straits=[
            StraitDTO(
                strait_id=s.strait_id,
                name=s.name,
                basin_a=s.basin_a,
                basin_b=s.basin_b,
                kind=s.kind,
                capacity_mbd=s.capacity_mbd,
                distance_nm=s.distance_nm,
                transit_days=s.transit_days,
            )
            for s in straits
        ],
    )


@app.post("/solve", response_model=SolutionDTO)
def solve(scenario: Scenario) -> SolutionDTO:
    countries, basins, coastlines, straits = _raw_data()

    # Apply country production/consumption overrides
    patched_countries = [
        c.__class__(
            iso3=c.iso3,
            name=c.name,
            production_mbd=scenario.country_production_overrides.get(
                c.iso3, c.production_mbd
            ),
            consumption_mbd=scenario.country_consumption_overrides.get(
                c.iso3, c.consumption_mbd
            ),
            lat=c.lat,
            lon=c.lon,
        )
        for c in countries
    ]

    # Apply strait capacity overrides and closures
    closed = set(scenario.closed_straits)
    patched_straits = []
    for s in straits:
        if s.strait_id in closed:
            continue
        cap = scenario.strait_capacity_overrides.get(s.strait_id, s.capacity_mbd)
        patched_straits.append(
            s.__class__(
                strait_id=s.strait_id,
                name=s.name,
                basin_a=s.basin_a,
                basin_b=s.basin_b,
                kind=s.kind,
                capacity_mbd=cap,
                distance_nm=s.distance_nm,
                transit_days=s.transit_days,
            )
        )

    g = build_oil_graph(patched_countries, basins, coastlines, patched_straits)
    balance_supply_demand(g)

    total_supply = sum(d["supply"] for _, d in g.nodes(data=True))
    total_demand = sum(d["demand"] for _, d in g.nodes(data=True))

    sol = solve_market(g)

    flows: list[FlowDTO] = []
    strait_flows: dict[str, float] = {}
    if sol.flows:
        for (u, v), f in sol.flows.items():
            if f < 1e-6:
                continue
            data = g.edges[u, v]
            flow = FlowDTO(
                source=u,
                target=v,
                mbd=f,
                kind=data.get("kind", "unknown"),
                strait_id=data.get("strait_id"),
            )
            flows.append(flow)
            sid = data.get("strait_id")
            if sid:
                strait_flows[sid] = strait_flows.get(sid, 0.0) + f

    imp_raw = strait_importance(g) if sol.status == "optimal" else {}
    imp: dict[str, float | None] = {}
    for k, v in imp_raw.items():
        imp[k] = None if v == float("inf") else v

    return SolutionDTO(
        status=sol.status,
        total_cost=sol.total_cost if sol.total_cost == sol.total_cost else 0.0,
        total_supply=total_supply,
        total_demand=total_demand,
        flows=flows,
        strait_flows=strait_flows,
        node_prices=sol.node_prices,
        capacity_duals={
            (g.edges[u, v].get("strait_id") or f"{u}->{v}"): d
            for (u, v), d in sol.capacity_duals.items()
            if g.edges[u, v].get("kind") == "strait" and abs(d) > 1e-6
        },
        strait_importance=imp,
    )
