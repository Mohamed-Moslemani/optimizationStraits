# Oil market dataset — v1

Scope: global **crude oil** seaborne trade, approximate 2023. Focused on methodology, not publication-grade numbers.

## Files

| File | Rows | Purpose |
|---|---|---|
| `countries.csv` | 38 | Oil producers and consumers (iso3, name, production_mbd, consumption_mbd) |
| `basins.csv` | 14 | Ocean-region waypoints (Persian Gulf, Indian Ocean, Mediterranean, ...) |
| `coastlines.csv` | 55 | Country ↔ basin adjacency (which basins each country has ports on) |
| `straits.csv` | 18 | Chokepoints (EIA-tracked) plus alternative routes and open-ocean edges |
| `bilateral_flows_2023.csv` | 137 | Top exporter→importer pairs in mb/d (UN Comtrade HS 2709) |
| `brent_monthly_usd.csv` | 467 | EIA monthly Brent spot price 1987–2026 (USD/bbl) |

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
`bilateral_flows_2023.csv` contains ~137 exporter→importer pairs derived from **UN Comtrade HS 2709** (crude petroleum oils) imports for 2023. Used as a soft anchor in the LP (penalty on edge flows that deviate from observed-routing-derived expectations).

**How to refresh.** Run `python scripts/fetch_comtrade.py 2023` from the repo root. The script:
- Hits Comtrade's free public preview endpoint (no auth required, capped at 500 rows per call)
- Iterates over the 38 reporters in our model, fetches their HS 2709 imports
- Filters to the unique annual aggregate row (`motCode=0`, `partner2Code=0`)
- Converts CIF USD value ÷ Brent annual avg ($82.49/bbl in 2023) → barrels/year → mb/d
- Writes the new CSV in place

Coverage: ~28 mb/d total (vs real seaborne crude ~40 mb/d). Gaps are countries that didn't report or hit API rate limits during the run; re-running may capture more. Top pairs match reality within 10-20% (RUS→CHN 2.02, SAU→CHN 1.79, IRQ→CHN 1.17, MEX→USA 0.68, etc.).

**Caveats.** Using CIF/Brent for volume averages over grade differentials (Urals, Dubai, WTI all priced differently). For grade-specific accuracy, use the raw `qty` field — but be aware reporters use mixed units (kg vs kt) for the same `qtyUnitCode=8` field. The fetcher chooses USD-derived volume for cross-country consistency.

### Historical Brent monthly prices
`brent_monthly_usd.csv` contains EIA's [Europe Brent Spot Price FOB (RBRTE) monthly series](https://www.eia.gov/dnav/pet/hist/rbrteM.htm) from May 1987 to the present. Used by the calibration runner to pin the LP's reference price to the actual monthly Brent at each historical episode's date (instead of the default $85). This honors the data-hygiene point of Conlon, Cotter & Eyiah-Donkor (2024) "Forecasting the price of oil: A cautionary note", J. Commodity Markets — they show that *which* oil price series you use materially changes results.

To refresh: `curl -o /tmp/brent.xls https://www.eia.gov/dnav/pet/hist_xls/RBRTEm.xls && python -c "import pandas as pd; df = pd.read_excel('/tmp/brent.xls', sheet_name='Data 1', skiprows=2); df.columns = ['date','price_usd_per_bbl']; df = df.dropna(); df['period'] = df['date'].dt.strftime('%Y-%m'); df['price_usd_per_bbl'] = df['price_usd_per_bbl'].round(2); df[['period','price_usd_per_bbl']].to_csv('data/brent_monthly_usd.csv', index=False)"`.

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
