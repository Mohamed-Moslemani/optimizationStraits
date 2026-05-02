from __future__ import annotations

from dataclasses import dataclass, field

import cvxpy as cp
import networkx as nx
import numpy as np

# Penalty per mb/d of shut-in supply (production stranded by capacity loss).
# In USD/bbl. The LP only uses shut-in slack when supply has literally no path.
DEFAULT_SHUT_IN_PENALTY = 30.0


@dataclass
class MarketSolution:
    """Output of one market-clearing solve.

    Prices are in USD/bbl. Quantities (flows, demand, supply) are in mb/d.
    The LP itself is a welfare-maximizing QP — utility minus shipping cost minus
    a penalty for any production we couldn't move — and its dual variables
    against flow conservation are the equilibrium prices at each node.
    """

    total_cost: float                        # transit days summed across all flows
    total_shipping_usd: float                # USD/day spent on freight (cost * ship_day_cost)
    flows: dict[tuple[str, str], float]      # mb/d on each directed edge
    node_prices: dict[str, float]            # USD/bbl at each node (LP dual)
    capacity_duals: dict[tuple[str, str], float]
    status: str
    realized_demand: dict[str, float] = field(default_factory=dict)
    shut_in_supply: dict[str, float] = field(default_factory=dict)
    total_demand_response_mbd: float = 0.0   # baseline demand minus realized
    total_shut_in_mbd: float = 0.0


def solve_market(
    g: nx.DiGraph,
    cost_attr: str = "transit_days",
    elasticity: float = 0.2,
    reference_price: float = 85.0,
    ship_day_cost: float = 1.0,
    shut_in_penalty: float = DEFAULT_SHUT_IN_PENALTY,
) -> MarketSolution:
    """Welfare-maximizing market clearing with elastic demand.

    Per-country demand curve (linear, calibrated to elasticity ε at baseline):
        p_j(d_j) = a_j - b_j * d_j
    with
        b_j = reference_price / (ε * d_j_baseline)
        a_j = reference_price + b_j * d_j_baseline
    so p_j(d_j_baseline) = reference_price and (dD/dp)(p/D) = ε at baseline.

    Optimization (variables: flows x, realized demand d, shut-in s):
        max  Σ_j (a_j d_j - 0.5 b_j d_j²)
            - C * Σ_uv c_uv x_uv
            - P * Σ_u s_u
        s.t. A x = supply - s - d
             0 ≤ x ≤ capacity
             0 ≤ d ≤ d_baseline
             0 ≤ s ≤ supply
    where C = ship_day_cost (USD/bbl per ship-day), P = shut-in penalty.

    The dual of flow conservation gives the equilibrium price at each node,
    directly in USD/bbl. The capacity duals give strait economic importance.
    """
    nodes = list(g.nodes)
    edges = list(g.edges)
    n, m = len(nodes), len(edges)
    node_idx = {u: i for i, u in enumerate(nodes)}

    cap = np.array([g.edges[e]["capacity"] for e in edges])
    transit = np.array([g.edges[e][cost_attr] for e in edges])

    supply = np.array([g.nodes[u].get("supply", 0.0) for u in nodes])
    demand_max = np.array([g.nodes[u].get("demand", 0.0) for u in nodes])

    # Linear demand parameters per node (zeros where there is no demand).
    eps = max(elasticity, 1e-6)
    safe_d = np.where(demand_max > 0, demand_max, 1.0)
    b = np.where(demand_max > 0, reference_price / (eps * safe_d), 0.0)
    a = np.where(demand_max > 0, reference_price + b * demand_max, 0.0)

    A = np.zeros((n, m))
    for j, (u, v) in enumerate(edges):
        A[node_idx[u], j] += 1.0
        A[node_idx[v], j] -= 1.0

    x = cp.Variable(m, nonneg=True)
    d = cp.Variable(n, nonneg=True)
    s = cp.Variable(n, nonneg=True)

    flow_balance = A @ x == supply - s - d
    capacity = x <= cap
    demand_bound = d <= demand_max
    shut_in_bound = s <= supply

    utility = a @ d - 0.5 * cp.sum(cp.multiply(b, cp.square(d)))
    shipping = ship_day_cost * (transit @ x)
    objective = cp.Maximize(
        utility - shipping - shut_in_penalty * cp.sum(s)
    )

    problem = cp.Problem(
        objective,
        [flow_balance, capacity, demand_bound, shut_in_bound],
    )
    # CLARABEL is more robust for these QPs than OSQP at certain elasticities;
    # OSQP hit iteration limits at ε≈0.3-0.5 for our network.
    try:
        problem.solve(solver=cp.CLARABEL)
    except (cp.error.SolverError, Exception):
        problem.solve()

    if problem.status not in ("optimal", "optimal_inaccurate"):
        return MarketSolution(
            total_cost=float("nan"),
            total_shipping_usd=float("nan"),
            flows={},
            node_prices={},
            capacity_duals={},
            status=problem.status,
        )

    x_v = np.asarray(x.value).flatten()
    d_v = np.asarray(d.value).flatten()
    s_v = np.asarray(s.value).flatten()

    flows = {edges[j]: float(x_v[j]) for j in range(m)}

    # Equilibrium price at each consumer = their demand-curve WTP at the
    # realized consumption level: p_j = a_j - b_j * d_j. This is the market-
    # clearing price by construction (consumer's marginal WTP equals the
    # market price at equilibrium). We compute this directly rather than
    # extracting it from the LP dual, which avoids CVXPY sign-convention
    # subtleties around mixed equality/inequality + bounded variables.
    #
    # For producers (no demand curve), we derive a "gate price" as the highest
    # delivered price they reach minus shipping: gate_u = max over served j of
    # (p_j - ship_day_cost * transit(u→j)). We compute this approximately by
    # propagating consumer prices backwards through the LP-chosen flow paths.
    consumer_prices = {
        nodes[i]: float(a[i] - b[i] * d_v[i])
        for i in range(n)
        if demand_max[i] > 0
    }
    node_prices = dict(consumer_prices)

    # Backward-propagate prices from consumers to all upstream nodes via the
    # LP's flow solution: if a node ships to a downstream node, its price =
    # downstream price - per-unit shipping cost on that edge (the cheapest
    # downstream is the binding one). Iterates a few times to settle the chain.
    edge_cost_per_unit = ship_day_cost * transit
    for _ in range(20):
        changed = False
        for j, (u, v) in enumerate(edges):
            if x_v[j] < 1e-6:
                continue
            if v not in node_prices:
                continue
            implied = node_prices[v] - edge_cost_per_unit[j]
            if u not in node_prices or implied > node_prices[u]:
                node_prices[u] = implied
                changed = True
        if not changed:
            break

    capacity_duals = {edges[j]: float(np.asarray(capacity.dual_value).flatten()[j]) for j in range(m)}

    realized_demand = {
        nodes[i]: float(d_v[i]) for i in range(n) if demand_max[i] > 0
    }
    shut_in_supply = {
        nodes[i]: float(s_v[i]) for i in range(n) if s_v[i] > 1e-6
    }
    total_demand_response = float(np.sum(demand_max - d_v))
    total_shut_in = float(np.sum(s_v))
    transit_cost = float(np.dot(transit, x_v))
    shipping_usd = float(ship_day_cost * transit_cost)

    return MarketSolution(
        total_cost=transit_cost,
        total_shipping_usd=shipping_usd,
        flows=flows,
        node_prices=node_prices,
        capacity_duals=capacity_duals,
        status=problem.status,
        realized_demand=realized_demand,
        shut_in_supply=shut_in_supply,
        total_demand_response_mbd=total_demand_response,
        total_shut_in_mbd=total_shut_in,
    )
