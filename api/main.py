"""FastAPI backend for the straitgraph interactive UI.

Endpoints:
  GET  /world  - static snapshot of countries, basins, straits with coordinates
  POST /solve  - accept a scenario and return the LP solution: flows, prices,
                 strait importance, demand response, shut-in supply
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


app = FastAPI(title="straitgraph API", version="0.2.0")

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
    # Pricing model. The LP solves a welfare-maximizing QP with elastic demand:
    #   p_j(d_j) = a_j - b_j d_j  with elasticity ε at baseline (ref_price, d_max).
    # node_prices come out directly in USD/bbl as the dual of flow conservation.
    reference_price_usd_per_bbl: float = 85.0      # Brent spot proxy
    ship_day_cost_usd_per_bbl: float = 1.0         # VLCC charter+fuel amortized
    demand_elasticity: float = 0.2                 # short-run oil price elasticity


class FlowDTO(BaseModel):
    source: str
    target: str
    mbd: float
    kind: str
    strait_id: str | None = None


class SolutionDTO(BaseModel):
    status: str
    total_cost: float
    total_shipping_usd: float
    total_supply: float
    total_baseline_demand: float
    flows: list[FlowDTO]
    strait_flows: dict[str, float]
    capacity_duals: dict[str, float]
    strait_importance: dict[str, float | None]
    # Equilibrium prices in USD/bbl per country (LP dual).
    delivered_prices_usd: dict[str, float]
    price_delta_vs_base_usd: dict[str, float]
    global_avg_price_usd: float
    global_avg_price_delta_usd: float
    # Demand-response: how much consumption was reduced under high prices.
    realized_demand_mbd: dict[str, float]
    demand_cut_mbd: dict[str, float]               # baseline minus realized, per country
    total_demand_response_mbd: float
    # Shut-in supply: production stranded with no path.
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
    # Pre-balance so total net supply == total net demand_max. Real-world data
    # nets to a small global mismatch (inventories absorb the rest); without
    # this, the LP would price the gap as a structural shortage.
    balance_supply_demand(g)
    sol = solve_market(
        g,
        elasticity=scenario.demand_elasticity,
        reference_price=scenario.reference_price_usd_per_bbl,
        ship_day_cost=scenario.ship_day_cost_usd_per_bbl,
    )
    imp: dict[str, float | None] = {}
    if with_importance and sol.status in ("optimal", "optimal_inaccurate"):
        # Strait importance under the same pricing/elasticity assumptions.
        for k, v in _strait_importance_with_pricing(g, scenario).items():
            imp[k] = None if v == float("inf") else v
    return g, patched_countries, sol, imp


def _strait_importance_with_pricing(g, scenario):
    """Inline importance calc that re-solves with the scenario's pricing knobs.

    Importance = increase in (shipping cost + demand-response welfare loss + shut-in
    cost) when the strait is removed. Combining all three captures both
    "freight gets more expensive" and "less demand cleared" effects.
    """
    base = solve_market(
        g,
        elasticity=scenario.demand_elasticity,
        reference_price=scenario.reference_price_usd_per_bbl,
        ship_day_cost=scenario.ship_day_cost_usd_per_bbl,
    )

    def welfare_loss(sol):
        # Sum of (transit cost in $) + scarcity cost (= price * unmet demand
        # mass), so closing a critical strait shows a big number even when
        # rerouted cost stays low (because demand was cut instead).
        return sol.total_shipping_usd + 30.0 * sol.total_demand_response_mbd

    baseline = welfare_loss(base)

    strait_edges: dict[str, list[tuple[str, str]]] = {}
    for u, v, data in g.edges(data=True):
        if data.get("kind") != "strait":
            continue
        if data.get("strait_kind") not in ("chokepoint", "pipeline"):
            continue
        strait_edges.setdefault(data["strait_id"], []).append((u, v))

    result: dict[str, float] = {}
    for sid, edge_list in strait_edges.items():
        h = g.copy()
        h.remove_edges_from(edge_list)
        sol = solve_market(
            h,
            elasticity=scenario.demand_elasticity,
            reference_price=scenario.reference_price_usd_per_bbl,
            ship_day_cost=scenario.ship_day_cost_usd_per_bbl,
        )
        if sol.status in ("optimal", "optimal_inaccurate"):
            result[sid] = welfare_loss(sol) - baseline
        else:
            result[sid] = float("inf")
    return result


@app.post("/solve", response_model=SolutionDTO)
def solve(scenario: Scenario) -> SolutionDTO:
    g, patched_countries, sol, imp = _solve_one(scenario)
    country_map = {c.iso3: c for c in patched_countries}

    total_supply = sum(c.production_mbd for c in patched_countries)
    total_baseline_demand = sum(c.consumption_mbd for c in patched_countries)

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
            sid = data.get("strait_id")
            if sid and g.nodes[u].get("kind") == "basin":
                strait_flows[sid] = strait_flows.get(sid, 0.0) + f

    delivered = {k: v for k, v in sol.node_prices.items() if k in country_map}

    # Baseline (unperturbed) solve for delta-vs-base, with the same pricing knobs.
    base_scenario = Scenario(
        reference_price_usd_per_bbl=scenario.reference_price_usd_per_bbl,
        ship_day_cost_usd_per_bbl=scenario.ship_day_cost_usd_per_bbl,
        demand_elasticity=scenario.demand_elasticity,
    )
    _, base_countries, base_sol, _ = _solve_one(base_scenario, with_importance=False)
    base_country_map = {c.iso3: c for c in base_countries}
    base_delivered = {
        k: v for k, v in base_sol.node_prices.items() if k in base_country_map
    }

    delta = {
        u: delivered[u] - base_delivered[u]
        for u in delivered
        if u in base_delivered
    }

    # Demand-weighted global average. With elastic demand the realized weights
    # ARE the new equilibrium consumption, so this is the volume-weighted price
    # of barrels actually traded.
    num = den = 0.0
    base_num = base_den = 0.0
    for iso3, p in delivered.items():
        c = country_map.get(iso3)
        if not c:
            continue
        realized = sol.realized_demand.get(iso3, 0.0)
        if realized <= 1e-6:
            continue
        num += p * realized
        den += realized
        base_realized = base_sol.realized_demand.get(iso3, 0.0)
        if iso3 in base_delivered and base_realized > 1e-6:
            base_num += base_delivered[iso3] * base_realized
            base_den += base_realized
    global_avg = num / den if den > 0 else 0.0
    global_avg_base = base_num / base_den if base_den > 0 else 0.0

    realized_demand_mbd = {
        k: v for k, v in sol.realized_demand.items() if k in country_map
    }
    # Demand cut = baseline net demand - realized net demand (for net importers).
    # Using net rather than gross consumption avoids spurious "cuts" for
    # countries that produce all their own oil (e.g., Saudi gross consumption).
    demand_cut_mbd: dict[str, float] = {}
    for c in patched_countries:
        baseline_d = max(c.consumption_mbd - c.production_mbd, 0.0)
        if baseline_d <= 0:
            continue
        realized = realized_demand_mbd.get(c.iso3, 0.0)
        cut = baseline_d - realized
        if cut > 0.001:
            demand_cut_mbd[c.iso3] = cut

    return SolutionDTO(
        status=sol.status,
        total_cost=sol.total_cost if sol.total_cost == sol.total_cost else 0.0,
        total_shipping_usd=sol.total_shipping_usd
        if sol.total_shipping_usd == sol.total_shipping_usd
        else 0.0,
        total_supply=total_supply,
        total_baseline_demand=total_baseline_demand,
        flows=flows,
        strait_flows=strait_flows,
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
        realized_demand_mbd=realized_demand_mbd,
        demand_cut_mbd=demand_cut_mbd,
        total_demand_response_mbd=sol.total_demand_response_mbd,
        shut_in_supply_mbd={k: v for k, v in sol.shut_in_supply.items() if k in country_map},
        total_shut_in_mbd=sol.total_shut_in_mbd,
    )
