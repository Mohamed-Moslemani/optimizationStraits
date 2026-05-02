# Historical calibration

This package runs three documented historical oil-market shocks through the
straitgraph model and compares model output against published market data.

```bash
.venv/bin/python -m calibration.run
```

## Episodes

### 1. Ever Given Suez blockage — March 2021 (6 days)

**What happened.** The container ship Ever Given grounded sideways in the Suez
Canal on 23 March 2021 and blocked all transits for six days. SUMED pipeline
(~2.5 mb/d) continued flowing.

**Scenario.** Suez capacity dropped from 10 mb/d to 2.5 mb/d.

**Observed.**
- Brent crude rose ~$3-4/bbl over the period (EIA STEO Apr 2021; Reuters)
- VLCC AG-Europe Worldscale rates jumped from WS40 to WS60 (+50%) — about
  $1-2/bbl freight premium (Baltic Exchange TD3, S&P Platts)

### 2. Russia sanctions Q2 2022

**What happened.** Following the Feb 24 invasion, Russian seaborne crude
flows redirected from Europe to India and China. Production fell ~600 kb/d.
Voyages lengthened substantially.

**Scenario.** Russian production reduced from 10.1 to 9.5 mb/d; Danish Straits
capacity reduced from 3.0 to 1.5 mb/d (reflecting halved Baltic transits).

**Observed.**
- Brent rose from ~$90 in mid-Feb to $100-115 sustained through Q2
  (ICE Brent settlements; EIA STEO 2022)
- VLCC dirty-tanker rates rose 50-100% (Baltic Exchange BDTI)
- Urals-Brent discount widened to $20-30/bbl (CREA tracker)

### 3. Red Sea / Bab-el-Mandeb crisis Q1 2024

**What happened.** Houthi missile attacks on Red Sea shipping forced ~50% of
Suez and Bab el-Mandeb tanker traffic to reroute around the Cape of Good Hope,
adding 10-14 days to Asia-Europe voyages.

**Scenario.** Bab-el-Mandeb capacity 9.0 → 3.0; Suez capacity 10.0 → 4.5.

**Observed.**
- Brent rose modestly ~$3-7/bbl (EIA STEO Mar 2024; Bloomberg)
- VLCC AG-Europe rates rose from ~$2 to ~$6/bbl (Baltic Exchange TD3/TD20)
- Cape of Good Hope traffic +1.5-3 mb/d (EIA, Vortexa, Kpler trackers)

## Reading the report

Three rows per episode:
- `brent_change_usd` — model's demand-weighted global avg price change
- `avg_freight_premium_usd` — model's increase in shipping cost per barrel of
  delivered volume
- `cape_diverted_mbd` — model's increase in South Atlantic ↔ Indian Ocean flow

Verdicts: `✓` inside observed range, `≈` within ±30% of midpoint, `✗` outside.

## What the v1 calibration reveals

**The model's routing has more slack than reality.**

When capacity is cut, the LP reroutes around the constraint at a cost that
the LP correctly minimizes — but the substitute routes in our network are
often *cheaper than reality's*. For example, Asian-Gulf to Europe trade in
reality flows mostly via Suez. In the v1 LP it splits between Suez and the
Cape, with the LP picking whichever is cheaper at any given capacity. This
means modest capacity cuts don't bind, and the predicted price impact is
smaller than observed.

**The model captures structural effects directionally** (it reroutes flows,
shifts source-destination pairings) but **underpredicts price magnitudes**.

### Why the model underpredicts

1. **No bilateral flow constraints.** Real markets route oil based on
   long-term contracts, refinery grade preferences, and political
   relationships. The LP doesn't see any of this — it picks the cheapest
   path. Adding a UN Comtrade-derived bilateral flow layer would constrain
   the LP closer to observed routing patterns.

2. **No grade differentials.** Brent ≠ Dubai ≠ Urals. Real shocks like
   Russia 2022 widened grade *spreads* (Urals discount $20-30/bbl) without
   moving the global average much. We can't reproduce that with a single
   crude.

3. **Steady-state assumption.** Markets price expected duration of a
   disruption. Ever Given was known to be temporary, so the futures curve
   moved less than spot. Our model ignores duration entirely.

4. **No inventory buffers.** ~5 billion barrels sit in tanks worldwide.
   Short shocks are absorbed before they reach spot prices.

5. **No insurance / war-risk premium.** A meaningful component of 2024
   Red Sea freight rates was insurance, not freight time. Hard to capture
   in a pure transport model.

### What this means for the project

The calibration gives us:
- A **validation framework** — three documented shocks, configurable
  scenarios, observed-vs-modeled metrics
- A **baseline measurement** of v1 model accuracy
- A **prioritized v2 roadmap**: bilateral flow constraints first (would
  improve all three episodes), grade differentials second (Russia case
  specifically), inventory dynamics third (Suez 2021 specifically)

The framework is also reusable: as we add v2 features, re-running
`calibration.run` will tell us how much the changes improve the model
against fixed historical observations.

## Sources

| Episode | Primary references |
|---|---|
| Ever Given 2021 | EIA STEO April 2021; Reuters reporting Mar 23-29 2021; Baltic Exchange TD3; S&P Global Platts Wire |
| Russia 2022 | EIA STEO 2022; ICE Brent settlements; CREA Russian fossil-fuel tracker; Baltic Exchange BDTI |
| Red Sea 2024 | EIA STEO March 2024; Bloomberg Energy Q1 2024; Baltic Exchange TD3/TD20; Vortexa & Kpler ship-tracking reports; CREA Q1 2024 update |
