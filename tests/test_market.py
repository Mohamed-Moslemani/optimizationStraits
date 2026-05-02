from opencrude import (
    Basin,
    Coastline,
    Country,
    Strait,
    build_oil_graph,
    solve_market,
    strait_importance,
)


def _toy_graph():
    # A (producer) ---[X]--cheap--[Y]--link--[Z]--- C (consumer)
    #                     \_______detour_______/
    countries = [
        Country("A", "A", production_mbd=10, consumption_mbd=0),
        Country("C", "C", production_mbd=0, consumption_mbd=10),
    ]
    basins = [Basin("X", "X"), Basin("Y", "Y"), Basin("Z", "Z")]
    coastlines = [Coastline("A", "X"), Coastline("C", "Z")]
    straits = [
        Strait("cheap", "Cheap", "X", "Y", "chokepoint", 20, 100, 1.0),
        Strait("link", "Link", "Y", "Z", "chokepoint", 20, 100, 1.0),
        Strait("detour", "Detour", "X", "Z", "chokepoint", 20, 500, 5.0),
    ]
    return build_oil_graph(countries, basins, coastlines, straits)


def test_market_solves():
    g = _toy_graph()
    sol = solve_market(g)
    assert sol.status == "optimal"
    # cheapest: A -> X (0.25) -> Y (1) -> Z (1) -> C (0.25) = 2.5 per unit, 10 units = 25
    assert abs(sol.total_cost - 25.0) < 1e-3


def test_strait_importance_finds_bottleneck():
    g = _toy_graph()
    imp = strait_importance(g)
    # Removing 'cheap' forces detour: cost becomes 10*(0.25+5+0.25)=55, delta=30
    assert abs(imp["cheap"] - 30.0) < 1e-3
    assert abs(imp["link"] - 30.0) < 1e-3
    # Detour is unused at optimum
    assert abs(imp["detour"]) < 1e-3
