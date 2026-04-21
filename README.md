# straitgraph

Graph-theoretic analysis of the world's maritime straits and the global **crude oil** market that flows through them — with an interactive web UI for exploring what-if scenarios.

## Model

- **Country nodes** with supply = max(production − consumption, 0) and demand = max(consumption − production, 0), in million barrels per day (mb/d)
- **Ocean-basin nodes** (Persian Gulf, Indian Ocean, Mediterranean, ...) as transshipment waypoints
- **Coastal edges** connect countries to the basins they have ports on (directional by role: exporters push outbound, importers pull inbound — prevents ghost land-bridges)
- **Strait edges** connect basin to basin, carrying `capacity_mbd` and `transit_days`
- **Problem:** minimum-cost flow / market clearing
  $$\min \sum c_{uv} x_{uv} \quad \text{s.t.} \quad Ax = b, \quad 0 \le x \le \text{cap}$$
- **Analysis:** the dual variables of the capacity constraints are the *shadow prices of each strait* — a natural definition of strait importance. Resilience is computed by removing a strait and re-solving.

## Layout

```
src/straitgraph/   # Python package: graph, market LP, resilience
api/               # FastAPI backend exposing /world and /solve
web/               # Vite + React + TypeScript + Tailwind + MapLibre UI
data/              # oil dataset (countries, basins, coastlines, straits)
notebooks/         # exploratory analysis
tests/             # unit tests
```

## Setup

```bash
# backend (python)
python -m venv .venv
.venv/bin/pip install -e ".[dev,api]"

# frontend (node)
cd web && npm install
```

## Run the interactive UI

Two terminals:

```bash
# terminal 1 — backend on http://localhost:8005
.venv/bin/uvicorn api.main:app --reload --port 8005

# terminal 2 — frontend on http://localhost:5173
cd web && npm run dev
```

Open http://localhost:5173. The map lets you:
- **Click a strait** → slider to change capacity or close it entirely
- **Click a country** → sliders to change production and consumption
- **Preset scenarios** → "Red Sea crisis 2024", "Close Hormuz", "Russia sanctions", etc.
- **Right panel** → total cost, top flows, strait importance ranking, node prices
- Model re-solves live (~50 ms per solve)

## Run the CLI demo

```bash
.venv/bin/python -m straitgraph.demo
```

### Sample output

```
Graph: 38 countries, 14 basins, 15 strait/lane edges (bidirectional)
Total seaborne supply (mb/d): 41.49
Total seaborne demand (mb/d): 41.49

Market status: optimal
Total cost (barrel-days × 10^6): 107.6

Top 10 flows (country <-> basin and basin <-> basin):
        b:PG -> b:IO      :  15.43 mb/d     # Hormuz
        b:IO -> b:SCS     :  13.50 mb/d     # Malacca
       b:SCS -> CHN       :  12.10 mb/d
         RUS -> b:WPAC    :   6.20 mb/d     # ESPO-terminus attribution
        b:IO -> IND       :   4.60 mb/d
         IRQ -> b:PG      :   4.37 mb/d
         SAU -> b:RS      :   4.10 mb/d     # Red Sea egress
        b:RS -> b:MED     :   3.95 mb/d     # Suez
      b:SATL -> b:IO      :   3.64 mb/d     # Cape of Good Hope
      b:WPAC -> JPN       :   3.30 mb/d

Node prices (shadow prices, ship-days per mb/d):
  BRA / NGA / AGO: -13.73   (cheap sources — they sit on expensive Cape route)
  SAU / IRQ / ARE / KWT / IRN: -0.23  (Persian Gulf producers, near optimal)
  JPN / KOR / CHN / NLD / DEU / SGP / POL / DNK: +2.47  (expensive sinks)

Strait importance (Δ cost if closed, chokepoints only):
  hormuz              : INFEASIBLE  (no alternative in current graph)
  malacca             : INFEASIBLE  (no Lombok/Sunda modeled)
  bosphorus           : INFEASIBLE  (no pipeline alternative modeled)
  suez                : +1.6        (Cape of Good Hope absorbs the flow)
  bab_el_mandeb       : +0.2
  danish_straits      : ~0
  panama              : ~0
```

The three `INFEASIBLE` labels are a feature of the v1 graph, not a claim that global oil trade actually collapses if Hormuz closes — they tell you the current model has no redundancy there. Adding Lombok/Sunda (for Malacca), East-West pipelines (for Hormuz), and Druzhba/BTC (for Bosphorus) converts these to finite but large numbers.

Suez showing only `+1.6` matches the real 2024 experience: tankers rerouted around the Cape of Good Hope at measurable but manageable cost.

## Run the tests

```bash
.venv/bin/python -m pytest tests/ -q
```

## Data sources

See [data/README.md](data/README.md) for detailed sources and caveats. Primary references:
- Energy Institute Statistical Review of World Energy 2024
- EIA International Energy Statistics
- EIA "World Oil Transit Chokepoints" (2023)
