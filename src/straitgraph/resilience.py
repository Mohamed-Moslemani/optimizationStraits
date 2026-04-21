from __future__ import annotations

import networkx as nx

from .market import solve_market


def strait_importance(
    g: nx.DiGraph,
    cost_attr: str = "transit_days",
    only_chokepoints: bool = True,
) -> dict[str, float]:
    """Importance of each strait = increase in optimal market cost when it is removed.

    Iterates over edges with kind='strait', groups by 'strait_id', removes both
    directions, re-solves, and records the cost delta vs. the baseline.
    Infeasible removals are reported as +inf.

    If only_chokepoints is True, open-ocean edges (e.g., Cape of Good Hope,
    trans-Pacific) are skipped — they can't be "closed" in reality.
    """
    base = solve_market(g, cost_attr=cost_attr)
    baseline = base.total_cost

    strait_edges: dict[str, list[tuple[str, str]]] = {}
    for u, v, data in g.edges(data=True):
        if data.get("kind") != "strait":
            continue
        if only_chokepoints and data.get("strait_kind") != "chokepoint":
            continue
        strait_edges.setdefault(data["strait_id"], []).append((u, v))

    result: dict[str, float] = {}
    for sid, edge_list in strait_edges.items():
        h = g.copy()
        h.remove_edges_from(edge_list)
        sol = solve_market(h, cost_attr=cost_attr)
        if sol.status in ("optimal", "optimal_inaccurate"):
            result[sid] = sol.total_cost - baseline
        else:
            result[sid] = float("inf")
    return result
