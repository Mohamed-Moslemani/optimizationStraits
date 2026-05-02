from __future__ import annotations

from pathlib import Path

from .graph import (
    balance_supply_demand,
    build_oil_graph,
    load_basins,
    load_coastlines,
    load_countries,
    load_straits,
)
from .market import solve_market
from .resilience import strait_importance

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def main() -> None:
    countries = load_countries(DATA_DIR / "countries.csv")
    basins = load_basins(DATA_DIR / "basins.csv")
    coastlines = load_coastlines(DATA_DIR / "coastlines.csv")
    straits = load_straits(DATA_DIR / "straits.csv")

    g = build_oil_graph(countries, basins, coastlines, straits)
    balance_supply_demand(g)

    n_countries = sum(1 for _, d in g.nodes(data=True) if d["kind"] == "country")
    n_basins = sum(1 for _, d in g.nodes(data=True) if d["kind"] == "basin")
    n_straits = sum(
        1
        for _, _, d in g.edges(data=True)
        if d.get("kind") == "strait"
    ) // 2
    print(
        f"Graph: {n_countries} countries, {n_basins} basins, "
        f"{n_straits} strait/lane edges (bidirectional)"
    )
    total_supply = sum(d["supply"] for _, d in g.nodes(data=True))
    total_demand = sum(d["demand"] for _, d in g.nodes(data=True))
    print(f"Total seaborne supply (mb/d): {total_supply:.2f}")
    print(f"Total seaborne demand (mb/d): {total_demand:.2f}")

    sol = solve_market(g)
    print(f"\nMarket status: {sol.status}")
    print(f"Total cost (barrel-days × 10^6): {sol.total_cost:.1f}")

    print("\nTop 10 flows (country <-> basin and basin <-> basin):")
    top = sorted(sol.flows.items(), key=lambda kv: -kv[1])[:10]
    for (u, v), f in top:
        print(f"  {u:>10s} -> {v:<10s}: {f:6.2f} mb/d")

    print("\nNet country prices (shadow prices, ship-days per mb/d of net supply):")
    country_prices = {
        n: sol.node_prices[n]
        for n, d in g.nodes(data=True)
        if d["kind"] == "country"
    }
    for u, p in sorted(country_prices.items(), key=lambda kv: kv[1])[:8]:
        print(f"  {u}: {p:+.3f}  (cheap source)")
    print("  ...")
    for u, p in sorted(country_prices.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  {u}: {p:+.3f}  (expensive sink)")

    print("\nStrait importance (cost increase if closed, chokepoints only):")
    imp = strait_importance(g)
    for sid, delta in sorted(imp.items(), key=lambda kv: -kv[1]):
        label = f"+{delta:.1f}" if delta != float("inf") else "INFEASIBLE"
        print(f"  {sid:20s}: {label}")


if __name__ == "__main__":
    main()
