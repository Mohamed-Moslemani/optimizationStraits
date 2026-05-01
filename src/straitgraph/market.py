from __future__ import annotations

from dataclasses import dataclass, field

import cvxpy as cp
import networkx as nx
import numpy as np

# Penalty (in cost units) per mb/d of unmet demand or shut-in supply.
# Worst-case real route in our network is ~25 ship-days (USA West Coast to
# GBR via Panama or trans-Pacific). 30 is just above that, so the LP prefers
# any physical route to slack, but slack-bound nodes' duals stay at ±30 — a
# defensible "scarcity premium" of ~$30/bbl at default $1/ship-day pricing.
DEFAULT_UNMET_PENALTY = 30.0


@dataclass
class MarketSolution:
    total_cost: float
    flows: dict[tuple[str, str], float]
    node_prices: dict[str, float]
    capacity_duals: dict[tuple[str, str], float]
    status: str
    # Per-country unmet demand (mb/d) — consumption the network couldn't deliver.
    unmet_demand: dict[str, float] = field(default_factory=dict)
    # Per-country shut-in supply (mb/d) — production the network couldn't move.
    shut_in_supply: dict[str, float] = field(default_factory=dict)
    total_unmet_mbd: float = 0.0
    total_shut_in_mbd: float = 0.0


def solve_market(
    g: nx.DiGraph,
    cost_attr: str = "transit_days",
    unmet_penalty: float = DEFAULT_UNMET_PENALTY,
) -> MarketSolution:
    """Minimum-cost flow on the country graph, with two-sided slack.

    Two-sided slack lets the LP gracefully report capacity-constrained
    scenarios as *partial fulfillment* rather than infeasibility.

    Objective:
        min sum c_uv x_uv  +  P * (sum unmet_u + sum shut_in_u)

    Flow conservation per node:
        sum_v x_uv - sum_v x_vu
            = (supply_u - shut_in_u) - (demand_u - unmet_u)
            = b_u - shut_in_u + unmet_u

    Bounds:
        0 <= x_uv <= capacity_uv
        0 <= unmet_u  <= demand_u
        0 <= shut_in_u <= supply_u

    The high penalty P (>> any plausible transit cost) forces the LP to deliver
    everything it physically can before resorting to slack.
    """
    nodes = list(g.nodes)
    edges = list(g.edges)
    node_idx = {u: i for i, u in enumerate(nodes)}

    n, m = len(nodes), len(edges)
    cap = np.array([g.edges[e]["capacity"] for e in edges])
    cost = np.array([g.edges[e][cost_attr] for e in edges])

    supply = np.array([g.nodes[u].get("supply", 0.0) for u in nodes])
    demand = np.array([g.nodes[u].get("demand", 0.0) for u in nodes])
    b = supply - demand
    if not np.isclose(b.sum(), 0.0, atol=1e-6):
        raise ValueError(
            f"Total supply minus total demand must be zero (got {b.sum():.3f})."
        )

    A = np.zeros((n, m))
    for j, (u, v) in enumerate(edges):
        A[node_idx[u], j] += 1.0
        A[node_idx[v], j] -= 1.0

    x = cp.Variable(m, nonneg=True)
    unmet = cp.Variable(n, nonneg=True)
    shut_in = cp.Variable(n, nonneg=True)

    flow_balance = A @ x == b - shut_in + unmet
    capacity = x <= cap
    unmet_bound = unmet <= demand
    shut_in_bound = shut_in <= supply

    problem = cp.Problem(
        cp.Minimize(
            cost @ x + unmet_penalty * (cp.sum(unmet) + cp.sum(shut_in))
        ),
        [flow_balance, capacity, unmet_bound, shut_in_bound],
    )
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
    unmet_demand = {nodes[i]: float(unmet.value[i]) for i in range(n) if unmet.value[i] > 1e-6}
    shut_in_supply = {nodes[i]: float(shut_in.value[i]) for i in range(n) if shut_in.value[i] > 1e-6}
    total_unmet = float(sum(unmet_demand.values()))
    total_shut_in = float(sum(shut_in_supply.values()))

    # Cost reported excludes the slack penalty (which is artificial); just the
    # transit-time cost of the flows we actually executed.
    transit_cost = float(np.dot(cost, x.value))

    return MarketSolution(
        total_cost=transit_cost,
        flows=flows,
        node_prices=node_prices,
        capacity_duals=capacity_duals,
        status=problem.status,
        unmet_demand=unmet_demand,
        shut_in_supply=shut_in_supply,
        total_unmet_mbd=total_unmet,
        total_shut_in_mbd=total_shut_in,
    )
