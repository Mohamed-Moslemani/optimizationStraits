from __future__ import annotations

from dataclasses import dataclass

import cvxpy as cp
import networkx as nx
import numpy as np


@dataclass
class MarketSolution:
    total_cost: float
    flows: dict[tuple[str, str], float]
    node_prices: dict[str, float]          # dual of flow conservation (shadow price at node)
    capacity_duals: dict[tuple[str, str], float]  # dual of capacity constraint (strait importance)
    status: str


def solve_market(
    g: nx.DiGraph,
    cost_attr: str = "transit_days",
) -> MarketSolution:
    """Minimum-cost flow on the country graph.

    Objective: minimize sum_{(u,v)} cost_uv * x_uv
    s.t.       sum_v x_uv - sum_v x_vu = supply_u - demand_u   (flow conservation)
               0 <= x_uv <= capacity_uv                         (capacity)

    Duals:
      - node_prices (lambda_u): marginal cost of an extra unit of net supply at u
      - capacity_duals (mu_uv): marginal benefit of adding capacity to edge (u,v)
        → a natural measure of strait importance.
    """
    nodes = list(g.nodes)
    edges = list(g.edges)
    node_idx = {u: i for i, u in enumerate(nodes)}

    n, m = len(nodes), len(edges)
    cap = np.array([g.edges[e]["capacity"] for e in edges])
    cost = np.array([g.edges[e][cost_attr] for e in edges])

    b = np.array(
        [g.nodes[u].get("supply", 0.0) - g.nodes[u].get("demand", 0.0) for u in nodes]
    )
    if not np.isclose(b.sum(), 0.0):
        raise ValueError(
            f"Total supply minus total demand must be zero (got {b.sum():.3f})."
        )

    A = np.zeros((n, m))
    for j, (u, v) in enumerate(edges):
        A[node_idx[u], j] += 1.0
        A[node_idx[v], j] -= 1.0

    x = cp.Variable(m, nonneg=True)
    flow_balance = A @ x == b
    capacity = x <= cap

    problem = cp.Problem(cp.Minimize(cost @ x), [flow_balance, capacity])
    problem.solve()

    if problem.status not in ("optimal", "optimal_inaccurate"):
        return MarketSolution(
            total_cost=float("nan"),
            flows={},
            node_prices={},
            capacity_duals={},
            status=problem.status,
        )

    flows = {edges[j]: float(x.value[j]) for j in range(m)}
    node_prices = {nodes[i]: float(flow_balance.dual_value[i]) for i in range(n)}
    capacity_duals = {edges[j]: float(capacity.dual_value[j]) for j in range(m)}

    return MarketSolution(
        total_cost=float(problem.value),
        flows=flows,
        node_prices=node_prices,
        capacity_duals=capacity_duals,
        status=problem.status,
    )
