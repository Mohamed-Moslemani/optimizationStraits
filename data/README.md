# Oil market dataset — v1

Scope: global **crude oil** seaborne trade, approximate 2023. Focused on methodology, not publication-grade numbers.

## Files

| File | Rows | Purpose |
|---|---|---|
| `countries.csv` | 38 | Oil producers and consumers (iso3, name, production_mbd, consumption_mbd) |
| `basins.csv` | 14 | Ocean-region waypoints (Persian Gulf, Indian Ocean, Mediterranean, ...) |
| `coastlines.csv` | 55 | Country ↔ basin adjacency (which basins each country has ports on) |
| `straits.csv` | 18 | Chokepoints (EIA-tracked) plus alternative routes and open-ocean edges |
| `bilateral_flows_2023.csv` | 80 | Top exporter→importer pairs in mb/d (UN Comtrade-style) |

All flow figures are in **million barrels per day (mb/d)**. Costs (transit_days) are in **days**.

## Sources

### Production / consumption
- **Energy Institute Statistical Review of World Energy 2024** (free Excel download) — https://www.energyinst.org/statistical-review
- **EIA International Energy Statistics** (free) — https://www.eia.gov/international/data/world

Figures are rounded to 1 decimal (0.1 mb/d precision). For countries that both produce and consume large amounts of oil, we use **production − consumption** as net seaborne supply/demand. This is a simplification — see Caveats.

### Chokepoint capacities and flows
- **EIA "World Oil Transit Chokepoints"** (2023 update) — https://www.eia.gov/international/analysis/special-topics/World_Oil_Transit_Chokepoints
- **Suez Canal Authority** annual reports — https://www.suezcanal.gov.eg
- **Panama Canal Authority (ACP)** — https://pancanal.com

Capacities are **nominal upper bounds** derived from observed traffic plus physical constraints (draft, lane width). They are not regulatory limits — most straits have no daily cap for oil.

### Distances and transit times
Computed from representative port-to-port sea distances at a VLCC speed of ~14 knots laden. For v2, replace with the `searoute-py` package for reproducible great-circle-plus-chokepoint routing.

### Bilateral trade flows
`bilateral_flows_2023.csv` contains the top ~80 exporter→importer pairs, used as a soft anchor in the LP (penalty on edge flows that deviate from observed-routing-derived expectations). Sources are approximate annualized values from:
- **EIA International Energy Statistics** — https://www.eia.gov/international/data/world (US imports/exports, headline source-destination pairs)
- **CREA Russian fossil-fuel tracker** — https://energyandcleanair.org (Russian post-2022 reroutings)
- **Eurostat Comext** (HS 2709) — https://ec.europa.eu/eurostat (EU imports by partner)

The numbers are rounded to 0.1 mb/d and don't capture month-to-month variation. For a publication-quality dataset, replace with a UN Comtrade HS 2709 bulk download for the target year.

## Caveats (read before citing anything)

1. **Net-trade approximation.** `supply = max(production − consumption, 0)` misses important structure. The US produces ~13 mb/d and consumes ~19 mb/d, but actually **exports** ~4 mb/d of light crude and **imports** ~6 mb/d of heavier crude. The model only sees the net 6 mb/d deficit.

2. **Pipelines are invisible.** Druzhba (RUS → EU), Keystone (CAN → USA), ESPO (RUS → CHN), BTC (AZE → TUR), CPC (KAZ → RUS Black Sea) carry large volumes that bypass straits. Currently we attribute Kazakh exports to the Black Sea basin to reflect CPC; other pipelines are ignored.

3. **Sanctions-era flows.** Post-2022 Russian crude is heavily routed via shadow fleets, STS transfers, and India/UAE re-export. Official trade statistics undercount these. The `capacity_mbd` for Danish Straits and Turkish Straits reflect pre-2022 patterns.

4. **Red Sea disruption.** Bab-el-Mandeb and Suez flows dropped sharply in 2024 as tankers rerouted around the Cape of Good Hope. Our model uses pre-disruption capacity; the resilience/sensitivity analysis is exactly the tool to quantify the rerouting.

5. **Hub re-exports.** Singapore and Rotterdam appear as large importers because they refine and re-export. Treating them as final consumers overstates their oil demand by ~30-50%.

6. **Definition drift.** "Crude oil" vs "crude + condensate" vs "total liquids" differ by ~5-10 mb/d globally. We use crude + condensate where possible. Cite which when writing up.

## Upgrade path

- v1.1 — add `bilateral_flows.csv` from UN Comtrade + CREA
- v1.2 — replace manual transit times with `searoute-py` computed distances
- v1.3 — add refined-product flows (HS 2710) and LNG (HS 2711) as parallel commodities
- v2 — hub-redistribution model for Singapore/Rotterdam; explicit pipeline edges
