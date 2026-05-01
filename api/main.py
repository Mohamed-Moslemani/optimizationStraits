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
    allow_origins=["http://localhost:7010", "http://127.0.0.1:7010"],
    # (API itself runs on :7009 — see README)
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
    # Pricing model. LP dual prices lambda_j are in ship-days per mb/d and only
    # unique up to an additive constant. We anchor the demand-weighted global
    # average delivered price at `reference_price_usd_per_bbl` (Brent spot
    # proxy), so individual delivered prices deviate above/below that mean:
    #   lambda_bar = sum(lambda_j * demand_j) / sum(demand_j)
    #   delivered_j = reference_price + (lambda_j - lambda_bar) * ship_day_cost
    # Under a shock the mean stays fixed at the anchor while suppliers go down
    # and importers go up (or vice versa), matching trader intuition.
    reference_price_usd_per_bbl: float = 85.0      # Brent spot proxy
    ship_day_cost_usd_per_bbl: float = 1.0         # VLCC charter+fuel amortized


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
    # Delivered price (USD/bbl) at each country, anchored by reference_country + reference_price
    delivered_prices_usd: dict[str, float]
    # Delta ($/bbl) vs. the unperturbed base case for the same pricing anchors.
    # Positive = scenario is more expensive for that importer.
    price_delta_vs_base_usd: dict[str, float]
    # Summary aggregates
    global_avg_price_usd: float         # demand-weighted delivered price across net importers
    global_avg_price_delta_usd: float   # vs base
    # Unmet demand per country (mb/d) when capacity cannot deliver full demand.
    unmet_demand_mbd: dict[str, float]
    total_unmet_mbd: float
    # Shut-in supply per country (mb/d) — production stranded by capacity loss.
    shut_in_supply_mbd: dict[str, float]
    total_shut_in_mbd: float


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


def _solve_one(scenario: Scenario, with_importance: bool = True):
    """Solve the LP for a given scenario; return the solution object + graph."""
    countries, basins, coastlines, straits = _raw_data()

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
    sol = solve_market(g)
    imp: dict[str, float | None] = {}
    if with_importance and sol.status == "optimal":
        for k, v in strait_importance(g).items():
            imp[k] = None if v == float("inf") else v
    return g, patched_countries, sol, imp


def _lambda_bar(sol, countries) -> float:
    """Demand-weighted average LP dual price across importers.

    Used as the anchor: in the base case, delivered avg = reference_price.
    """
    if sol.status not in ("optimal", "optimal_inaccurate") or not sol.node_prices:
        return 0.0
    country_set = {c.iso3 for c in countries}
    demand_by = {
        c.iso3: max(c.consumption_mbd - c.production_mbd, 0.0) for c in countries
    }
    num = 0.0
    den = 0.0
    for iso3, lam in sol.node_prices.items():
        if iso3 not in country_set:
            continue
        d = demand_by.get(iso3, 0.0)
        num += lam * d
        den += d
    return num / den if den > 0 else 0.0


def _delivered_prices(
    sol,
    lambda_bar: float,
    reference_price: float,
    ship_day_cost: float,
) -> dict[str, float]:
    """Convert LP dual prices to USD/bbl, given a fixed lambda_bar anchor.

    Using a *fixed* (base-case) lambda_bar across all scenarios lets the global
    average price move under shocks, rather than hiding that movement behind a
    re-centered anchor.
    """
    if sol.status not in ("optimal", "optimal_inaccurate") or not sol.node_prices:
        return {}
    return {
        u: reference_price + (lam - lambda_bar) * ship_day_cost
        for u, lam in sol.node_prices.items()
    }


@app.post("/solve", response_model=SolutionDTO)
def solve(scenario: Scenario) -> SolutionDTO:
    g, patched_countries, sol, imp = _solve_one(scenario)

    total_supply = sum(d["supply"] for _, d in g.nodes(data=True))
    total_demand = sum(d["demand"] for _, d in g.nodes(data=True))

    flows: list[FlowDTO] = []
    strait_flows: dict[str, float] = {}
    if sol.flows:
        for (u, v), f in sol.flows.items():
            if f < 1e-6:
                continue
            data = g.edges[u, v]
            flows.append(
                FlowDTO(
                    source=u,
                    target=v,
                    mbd=f,
                    kind=data.get("kind", "unknown"),
                    strait_id=data.get("strait_id"),
                )
            )
            # Each strait now has 4 edges (basin_a<->mid<->basin_b). To avoid
            # double-counting we sum only the basin->mid (entering) edges:
            # one per direction, capturing total gross flow through the strait.
            sid = data.get("strait_id")
            if sid and g.nodes[u].get("kind") == "basin":
                strait_flows[sid] = strait_flows.get(sid, 0.0) + f

    # Solve the base case first to fix the pricing anchor — this way the global
    # average delivered price is free to move under shocks.
    base_scenario = Scenario(
        reference_price_usd_per_bbl=scenario.reference_price_usd_per_bbl,
        ship_day_cost_usd_per_bbl=scenario.ship_day_cost_usd_per_bbl,
    )
    _, base_countries, base_sol, _ = _solve_one(base_scenario, with_importance=False)
    lambda_bar_base = _lambda_bar(base_sol, base_countries)

    delivered = _delivered_prices(
        sol,
        lambda_bar_base,
        scenario.reference_price_usd_per_bbl,
        scenario.ship_day_cost_usd_per_bbl,
    )
    base_delivered = _delivered_prices(
        base_sol,
        lambda_bar_base,
        base_scenario.reference_price_usd_per_bbl,
        base_scenario.ship_day_cost_usd_per_bbl,
    )
    delta = {
        u: delivered[u] - base_delivered[u]
        for u in delivered
        if u in base_delivered
    }

    # Demand-weighted global avg delivered price across net importers (consumers).
    # Exclude countries with significant unmet demand — their LP dual reflects
    # the scarcity-penalty constant, not a market-clearing transport cost. The
    # global avg should describe the price of barrels that actually changed hands.
    country_map = {c.iso3: c for c in patched_countries}
    UNMET_FRAC_THRESHOLD = 0.05  # if >5% of demand is unmet, treat as scarcity
    num = 0.0
    den = 0.0
    base_num = 0.0
    base_den = 0.0
    for iso3, p in delivered.items():
        c = country_map.get(iso3)
        if not c:
            continue
        net_demand = max(c.consumption_mbd - c.production_mbd, 0.0)
        if net_demand <= 0:
            continue
        unmet_here = sol.unmet_demand.get(iso3, 0.0)
        if unmet_here / max(net_demand, 1e-6) > UNMET_FRAC_THRESHOLD:
            continue
        num += p * net_demand
        den += net_demand
        if iso3 in base_delivered:
            base_num += base_delivered[iso3] * net_demand
            base_den += net_demand
    global_avg = num / den if den > 0 else 0.0
    global_avg_base = base_num / base_den if base_den > 0 else 0.0

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
        delivered_prices_usd=delivered,
        price_delta_vs_base_usd=delta,
        global_avg_price_usd=global_avg,
        global_avg_price_delta_usd=global_avg - global_avg_base,
        unmet_demand_mbd={k: v for k, v in sol.unmet_demand.items() if k in country_map},
        total_unmet_mbd=sol.total_unmet_mbd,
        shut_in_supply_mbd={k: v for k, v in sol.shut_in_supply.items() if k in country_map},
        total_shut_in_mbd=sol.total_shut_in_mbd,
    )
