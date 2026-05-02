# Crude grade differentiation — design and deferral

**Status:** Deferred to v0.4. Documented here to explain what's involved and
why it's not in v0.3.

## Why this matters

Real oil markets distinguish at least three grade families:

| Grade family | Examples | API gravity | Sulfur | Refinery preference |
|---|---|---|---|---|
| Light sweet | Brent, WTI, Bonny Light | > 32° | < 0.5% | Gasoline-heavy refineries (US, EU) |
| Medium sour | Dubai, Oman, Urals | 26-32° | 0.5-2% | Asian / Mediterranean refineries |
| Heavy sour | Maya (Mexican), Vasconia, some Middle East | < 26° | > 2% | Coking-equipped refineries (US Gulf) |

Refineries are physically configured for specific grade slates. They can
substitute somewhat (paying a refining-margin penalty) but not freely. Real
market shocks **show up most loudly as widening grade spreads**, not in
the global Brent average:

- **Russia 2022:** Urals (medium sour) discount to Brent widened from ~$0
  to $20-30/bbl as European refineries rejected it. Brent itself rose modestly.
- **2019 Saudi Abqaiq strike:** brief shutdown of Arab Light supply caused
  the Light-Heavy spread to *narrow*, even though Brent spiked.
- **OPEC+ cuts 2017-2018:** sour crude tightened relative to sweet because
  OPEC mostly cuts medium-sour grades.

OpenCrude v0.3 models crude as a single fungible commodity. The Russia
2022 calibration episode therefore cannot reproduce its central price story
(the Urals spread).

## What a grade-aware model needs

### Data layer
- **Per-country production split** by grade. Sources:
  - EIA crude characteristics database (free, by-field API/sulfur)
  - OPEC ASB grade tables
  - Energy Institute Statistical Review (less granular, country-level)
- **Per-country refinery throughput by grade**. Sources:
  - JODI Oil refinery feed data (some granularity)
  - National regulators (US EIA refinery utilization, Eurostat)
  - Trade associations (CONCAWE for EU)

Approximate effort: ~2 days of clean data work.

### Modeling layer
- LP becomes **multi-commodity flow** with K commodities (K=3 grades).
- Variables: `x_{uv,k}` — flow of grade k on edge (u,v).
- Capacity constraints aggregate across grades: `sum_k x_{uv,k} <= cap_uv`.
- Refinery substitution: each demand node has K substitution coefficients
  expressing "if my preferred grade is unavailable, I'll take % of grade
  X at penalty Y". Implemented as a quadratic penalty on grade-mismatch.
- Per-grade reference prices anchored to Brent/Dubai/Maya respectively,
  with cross-grade spreads emerging from supply/demand by grade.

Approximate effort: ~1 day of LP rewriting + 1 day of testing.

### UI layer
- Strait flows and country pies need to break out by grade (3-color
  stacked bars instead of single colors).
- Scenario editor needs grade-specific production/consumption sliders
  (3× the current widget count).
- Calibration report adds grade-spread metrics.

Approximate effort: ~1 day.

## Total effort estimate

~5 days of focused work for a clean v0.4 grade-aware model. Half data,
half modeling/UI.

## Why deferred

1. **Diminishing return for our scope.** OpenCrude is a transport-cost
   simulator. Most of the *transport-component* analysis works correctly
   without grades — closing Hormuz physically constrains all crude grades
   the same. Grades matter mainly for the *supply-shock* category, which
   is one of three episode types in our calibration.
2. **Data quality bottleneck.** Per-country production-by-grade data is
   noisier than the simple production totals we use today. Calibration
   gains from grades may be partially eaten by data noise.
3. **Architectural prerequisite.** The current consumer pricing (anchored
   at WTP at d=d_max) limits how much a freight or supply shock can
   propagate to delivered prices. Adding grades on top of this limit
   doesn't help. Better to first **rewrite consumer pricing to be
   freight-pass-through** (~1 day), then add grades on the cleaner base.

## Recommended path forward

1. **First (next):** Rewrite consumer pricing so freight passes through.
   Anchor at supplier gate prices, propagate downstream with shipping
   added. The current `node_prices` back-prop almost does this — just
   needs to start from suppliers, not consumers. ~1 day. Will lift Red
   Sea / Russia 2022 calibration meaningfully.
2. **Second:** Add 3-grade differentiation per this doc. ~5 days.

After both, the calibration report should move from "0/9 in range" to
~"6+/9 in range", with the residual being inventory dynamics and
expectations (out of scope for a structural model).
