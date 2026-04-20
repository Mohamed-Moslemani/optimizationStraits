from straitgraph import Country, Strait, build_graph, solve_market, strait_importance


def _toy_graph():
    countries = [
        Country("A", "A", supply=10),
        Country("B", "B"),
        Country("C", "C", demand=10),
    ]
    straits = [
        Strait("AB", ("A", "B"), capacity=20, distance_nm=100, transit_days=1.0),
        Strait("BC", ("B", "C"), capacity=20, distance_nm=100, transit_days=1.0),
        Strait("AC-long", ("A", "C"), capacity=20, distance_nm=500, transit_days=5.0),
    ]
    return build_graph(countries, straits)


def test_market_solves():
    g = _toy_graph()
    sol = solve_market(g)
    assert sol.status == "optimal"
    # cheapest path is A->B->C with cost 2.0 per unit, 10 units delivered
    assert abs(sol.total_cost - 20.0) < 1e-4


def test_strait_importance_removes_bottleneck():
    g = _toy_graph()
    imp = strait_importance(g)
    # Removing AB or BC forces the long route (+3 per unit * 10 = +30)
    assert imp["AB"] > 0
    assert imp["BC"] > 0
    # Removing the long backup route shouldn't change the optimum
    assert abs(imp["AC-long"]) < 1e-4
