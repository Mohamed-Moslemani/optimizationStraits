"""Calibration runner: solves each historical episode and prints a model-vs-observed report.

Usage:
    python -m calibration.run
"""
from __future__ import annotations

from pathlib import Path

from opencrude import (
    balance_supply_demand,
    build_oil_graph,
    expected_edge_flows,
    load_basins,
    load_bilateral,
    load_coastlines,
    load_countries,
    load_straits,
    solve_market,
)

from .episodes import EPISODES, Episode, ObservedMetric

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load():
    bp = DATA_DIR / "bilateral_flows_2023.csv"
    return (
        load_countries(DATA_DIR / "countries.csv"),
        load_basins(DATA_DIR / "basins.csv"),
        load_coastlines(DATA_DIR / "coastlines.csv"),
        load_straits(DATA_DIR / "straits.csv"),
        load_bilateral(bp) if bp.exists() else [],
    )


def _solve(scenario: dict, base_for_pricing: dict | None = None) -> tuple[object, dict[str, float], dict[str, float]]:
    countries, basins, coastlines, straits, bilateral = _load()
    patched_countries = [
        c.__class__(
            iso3=c.iso3,
            name=c.name,
            production_mbd=scenario.get("country_production_overrides", {}).get(
                c.iso3, c.production_mbd
            ),
            consumption_mbd=scenario.get("country_consumption_overrides", {}).get(
                c.iso3, c.consumption_mbd
            ),
            lat=c.lat,
            lon=c.lon,
        )
        for c in countries
    ]
    closed = set(scenario.get("closed_straits", []))
    cap_over = scenario.get("strait_capacity_overrides", {})
    patched_straits = []
    for s in straits:
        if s.strait_id in closed:
            continue
        patched_straits.append(
            s.__class__(
                strait_id=s.strait_id,
                name=s.name,
                basin_a=s.basin_a,
                basin_b=s.basin_b,
                kind=s.kind,
                capacity_mbd=cap_over.get(s.strait_id, s.capacity_mbd),
                distance_nm=s.distance_nm,
                transit_days=s.transit_days,
            )
        )
    g = build_oil_graph(patched_countries, basins, coastlines, patched_straits)
    balance_supply_demand(g)
    bw = scenario.get("bilateral_anchor_weight", 0.5)
    expected = expected_edge_flows(g, bilateral) if bilateral and bw > 0 else None
    sol = solve_market(
        g,
        elasticity=scenario.get("demand_elasticity", 0.2),
        reference_price=scenario.get("reference_price_usd_per_bbl", 85.0),
        ship_day_cost=scenario.get("ship_day_cost_usd_per_bbl", 1.0),
        expected_flows=expected,
        bilateral_weight=bw,
    )
    # Strait flows: sum each strait_id over basin -> mid edges
    strait_flows: dict[str, float] = {}
    for (u, v), f in sol.flows.items():
        if f < 1e-6:
            continue
        data = g.edges[u, v]
        sid = data.get("strait_id")
        if sid and g.nodes[u].get("kind") == "basin":
            strait_flows[sid] = strait_flows.get(sid, 0.0) + f
    # Demand-weighted global avg price (importers only)
    country_set = {c.iso3 for c in patched_countries}
    cmap = {c.iso3: c for c in patched_countries}
    num = den = 0.0
    for iso3, p in sol.node_prices.items():
        if iso3 not in country_set:
            continue
        c = cmap[iso3]
        rd = sol.realized_demand.get(iso3, 0.0)
        if rd <= 1e-6:
            continue
        if c.consumption_mbd <= c.production_mbd:
            continue
        num += p * rd
        den += rd
    global_avg = num / den if den > 0 else 0.0
    return sol, strait_flows, {"global_avg_price_usd": global_avg}


def _model_metrics(sol_base, flows_base, agg_base, sol, flows, agg):
    """Project the model output to the observed-metric keys we care about."""
    out: dict[str, float] = {}
    out["brent_change_usd"] = agg["global_avg_price_usd"] - agg_base["global_avg_price_usd"]

    # Average freight premium = increase in (shipping cost in USD) per mb/d
    # of volume actually delivered. This is the LP's authentic measure of
    # "how much more does each barrel cost to ship" under the scenario.
    base_vol = sum(sol_base.realized_demand.values())
    scen_vol = sum(sol.realized_demand.values())
    base_avg = sol_base.total_shipping_usd / max(base_vol, 1e-6)
    scen_avg = sol.total_shipping_usd / max(scen_vol, 1e-6)
    out["avg_freight_premium_usd"] = scen_avg - base_avg

    # Cape of Good Hope diverted volume = increase in satl_io flow.
    out["cape_diverted_mbd"] = flows.get("satl_io", 0.0) - flows_base.get("satl_io", 0.0)
    # Total demand response (mb/d) — only non-zero when capacity truly cannot
    # absorb. Our model's own stress signal.
    out["demand_response_mbd"] = sol.total_demand_response_mbd
    # Total shut-in supply (mb/d) — production stranded.
    out["shut_in_mbd"] = sol.total_shut_in_mbd
    return out


def _verdict(observed: ObservedMetric, modeled: float) -> str:
    """Classify match quality."""
    lo, hi = observed.low, observed.high
    if lo <= modeled <= hi:
        return "✓ within observed range"
    # Distance from nearest edge of range
    dist = abs(modeled - hi) if modeled > hi else abs(lo - modeled)
    rel = dist / max(abs(observed.mid), 1e-6)
    if rel < 0.3:
        return "≈ within ±30%"
    if rel < 1.0:
        return "✗ off by < 1× midpoint"
    return "✗✗ off by >= 1× midpoint"


def run() -> None:
    print("=" * 78)
    print(f"{'OPENCRUDE HISTORICAL CALIBRATION':^78}")
    print("=" * 78)

    for ep in EPISODES:
        # Each episode's "base" must use the same elasticity and ship-day cost
        # as the scenario itself, otherwise we'd attribute parameter changes
        # to the scenario perturbation. Strip out the strait/country edits.
        base_scenario = {
            k: v
            for k, v in ep.scenario.items()
            if k in ("demand_elasticity", "ship_day_cost_usd_per_bbl",
                     "reference_price_usd_per_bbl")
        }
        base_sol, base_flows, base_agg = _solve(base_scenario)
        sol, flows, agg = _solve(ep.scenario)
        modeled = _model_metrics(base_sol, base_flows, base_agg, sol, flows, agg)

        print()
        print("-" * 78)
        print(f"{ep.name}  ({ep.date})")
        print("-" * 78)
        print(f"  Scenario: {ep.scenario}")
        print(f"  Base parameters: {base_scenario}")
        print(f"  Notes:    {ep.description}")
        print(f"  Base avg price: ${base_agg['global_avg_price_usd']:.2f}/bbl   "
              f"Base Cape flow: {base_flows.get('satl_io', 0):.2f} mb/d")
        print()
        print(f"  {'metric':<28} {'observed':<22} {'modeled':<14} {'verdict':<24}")
        print(f"  {'-'*28} {'-'*22} {'-'*14} {'-'*24}")
        for key, obs in ep.observed.items():
            if key not in modeled:
                continue
            mv = modeled[key]
            obs_str = (
                f"{obs.low:+.2f} to {obs.high:+.2f} {obs.unit}"
                if isinstance(obs.value, tuple)
                else f"{obs.value:+.2f} {obs.unit}"
            )
            verdict = _verdict(obs, mv)
            print(f"  {key:<28} {obs_str:<22} {mv:+.2f}{'':<8} {verdict}")
        # Always also show the model's structural diagnostics, regardless of
        # whether observed counterparts are listed.
        print()
        print(f"  Model diagnostics:")
        print(f"    avg freight premium:    {modeled['avg_freight_premium_usd']:+.2f} USD/bbl")
        print(f"    Cape of Good Hope Δ:    {modeled['cape_diverted_mbd']:+.2f} mb/d")
        print(f"    demand response:        {modeled['demand_response_mbd']:+.2f} mb/d cut")
        print(f"    shut-in supply:         {modeled['shut_in_mbd']:+.2f} mb/d stranded")
        print(f"\n  Caveats: {ep.notes}")

    print()
    print("=" * 78)
    print("Reading the report:")
    print("  ✓  model number lands inside observed range")
    print("  ≈  within ±30% of observed midpoint")
    print("  ✗  outside that band")
    print()
    print("Limitations of v1 (these explain large modeled-vs-observed gaps):")
    print("  - no bilateral flow constraints: LP routes optimally vs reality's")
    print("    contract-driven flows (e.g., AG→Europe defaults to Cape in our")
    print("    model, defaults to Suez in reality)")
    print("  - no grade differentials (Brent vs Dubai vs Urals spreads)")
    print("  - steady-state: ignores expected duration of disruption")
    print("  - no inventories / SPR releases buffering short shocks")
    print("  - insurance / war-risk premia not modeled separately from freight")
    print("=" * 78)


if __name__ == "__main__":
    run()
