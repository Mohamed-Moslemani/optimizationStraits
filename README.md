# OpenCrude

Open-source what-if simulator for the **transport-cost component** of global crude oil prices. Models the world's maritime straits as a network, solves a welfare-maximizing market-clearing LP with elastic demand, and quantifies how chokepoint disruptions, sanctions, or capacity changes shift prices and reroute flows.

This is the open equivalent of closed tools like [oilshock.ai](https://oilshock.ai/#simulator). Per Conlon-Cotter-Eyiah-Donkor (2024)'s "cautionary note" on oil-price forecasting: OpenCrude does **not** claim to forecast Brent. It quantifies the *freight/transport* contribution to delivered prices under specific structural shocks.

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
src/opencrude/   # Python package: graph, market LP, resilience
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
# terminal 1 — backend on http://localhost:7009
.venv/bin/uvicorn api.main:app --reload --port 7009

# terminal 2 — frontend on http://localhost:7010
cd web && npm run dev
```

Open http://localhost:7010. The map lets you:
- **Click a strait** → slider to change capacity or close it entirely
- **Click a country** → sliders to change production and consumption
- **Preset scenarios** → "Red Sea crisis 2024", "Close Hormuz", "Russia sanctions", etc.
- **Right panel** → total cost, top flows, strait importance ranking, node prices
- Model re-solves live (~50 ms per solve)

## Run the CLI demo

```bash
.venv/bin/python -m opencrude.demo
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

## Talking to the API directly with `curl`

Once the backend is running on `:7009`, every UI interaction is also a single
JSON POST. Useful for scripting, sanity-checking, or showing the model to
someone over chat.

**Base case (no perturbations):**
```bash
curl -s -X POST http://localhost:7009/solve \
  -H 'Content-Type: application/json' -d '{}' | python -m json.tool | head -30
```

**Close the Strait of Hormuz:**
```bash
curl -s -X POST http://localhost:7009/solve \
  -H 'Content-Type: application/json' \
  -d '{"closed_straits":["hormuz"]}' \
  | python -c "import json,sys;d=json.load(sys.stdin);print(f\"Brent ${d['global_avg_price_usd']:.2f}/bbl ({d['global_avg_price_delta_usd']:+.2f}); shut-in {d['total_shut_in_mbd']:.1f} mb/d\")"
```

**Red Sea 2024 crisis (Bab-el-Mandeb + Suez at ~30%):**
```bash
curl -s -X POST http://localhost:7009/solve \
  -H 'Content-Type: application/json' \
  -d '{
    "strait_capacity_overrides": {"bab_el_mandeb": 3.0, "suez": 4.5},
    "demand_elasticity": 0.07,
    "ship_day_cost_usd_per_bbl": 2.2
  }' | python -m json.tool | grep -E 'global_avg|delta|cape|shut'
```

**See the world snapshot (countries, basins, straits with coordinates):**
```bash
curl -s http://localhost:7009/world | python -m json.tool | head -40
```

Full request schema is at `http://localhost:7009/docs` (FastAPI Swagger).

## Run the tests

```bash
.venv/bin/python -m pytest tests/ -q
```

## Run the historical calibration

```bash
.venv/bin/python -m calibration.run
```

Compares model output against published market data for three documented
shocks (Ever Given 2021, Russia sanctions 2022, Red Sea 2024). See
[calibration/README.md](calibration/README.md).

## Data sources

See [data/README.md](data/README.md) for detailed sources and caveats. Primary references:
- Energy Institute Statistical Review of World Energy 2024
- EIA International Energy Statistics
- EIA "World Oil Transit Chokepoints" (2023)
