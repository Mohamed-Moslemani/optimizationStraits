# Project name — proposals

The package is currently `straitgraph`. Comparable closed-source product:
[oilshock.ai](https://oilshock.ai/#simulator). Our project is the open
equivalent, with elastic demand, real Comtrade data, historical calibration,
and an interactive UI.

The name should be: short (≤ 10 letters), evocative of maritime / oil /
network analysis, available as a Python package + npm + .com / .ai if
possible, and not embarrassing in a research paper title.

## Categories + picks

### 1. Maritime navigation (instruments, terms)

| Name | Vibe | Notes |
|---|---|---|
| **Sextant** | Precision, history, science | `sextant.ai` taken (logging) but different domain |
| **Plumbline** | Depth-measuring rope; "the plumbline of the market" | Unique, slightly poetic |
| **Soundings** | Plural — sailors take soundings to measure depth | Researchy, evocative |
| **Compass** | Direction, orientation | Generic; many products |
| **Knot** | Nautical speed unit; also = connection | Punchy, short |
| **Heading** | Direction of travel | Clean but generic word |
| **Beacon** | Lighthouse, signaling | Many products use it |
| **Wakeflow** | Wake of a ship + flow analysis | Made-up; explains itself |

### 2. Maritime infrastructure

| Name | Vibe | Notes |
|---|---|---|
| **Fairway** | Navigable shipping channel | Clean, friendly, unused in this niche |
| **Jetty** | Pier; quick + small | Catchy |
| **Quay** | Loading dock (pronounced "key") | Short, distinctive, slightly cryptic |
| **Harbor** | Safe port | Warm, generic |
| **Lighthouse** | Guides ships | Already used (e.g. Google's Lighthouse) |
| **Anchor** | Holds in place | Many products use it |
| **Bunker** | Ship fuel; loaded with bunker fuel | Industry term |

### 3. Oil / energy / pipeline

| Name | Vibe | Notes |
|---|---|---|
| **Crudeflow** | Direct compound | Descriptive, slightly heavy |
| **Slickline** | Wireline tool used in oil wells | Industry term; sounds tech-y |
| **Wellhead** | Top of an oil well; data-source metaphor | Industry term |
| **Pipeline** | Generic but fits | Massively overused in tech |
| **Brent** | The benchmark itself | Locks brand to one crude grade |
| **Gusher** | When oil gushes from a well | Loud but evocative |

### 4. Chokepoint / network

| Name | Vibe | Notes |
|---|---|---|
| **Strait** | Single word, on the nose | Risk: too generic word |
| **Hormuz** | Most iconic strait globally | Locks brand to one place |
| **Bottleneck** | Literal | Negative connotation |
| **Pinch** | Pinch point | Feels small |
| **Throughput** | Engineering term | Generic |
| **Isthmus** | Narrow land = land version of strait | Obscure but distinctive |
| **Cape** | As in Cape of Good Hope | Suggests routing |

### 5. Open-source / positioning

| Name | Vibe | Notes |
|---|---|---|
| **OpenShock** | Direct vs oilshock.ai | Brand riding on competitor name |
| **OpenStrait** | Open + theme | Compound word |
| **OpenCrude** | Open + commodity | Cleanest open-positioning |
| **CrudeAtlas** | Atlas + crude | Cartographic + analytical |
| **OilAtlas** | Same | Plain |
| **PetroGraph** | Greek-rooted scholarly feel | Echoes our graph theory |

### 6. Researchy / academic

| Name | Vibe | Notes |
|---|---|---|
| **Cartograph** | Map-maker | Long word |
| **Mercator** | Famous map projection | Distinctive, historical |
| **Astrolabe** | Pre-sextant navigation | Romantic, ancient |
| **Lateen** | Triangular sail | Obscure but unique |
| **Convoy** | Group of ships | Punchy |

### 7. Modern tech-style (Stripe / Linear / Vercel-feel)

| Name | Vibe | Notes |
|---|---|---|
| **Tankr** | Dropped-vowel style | Cute but trendy |
| **Slick** | Oil slick + slick UX | Ambiguous |
| **Drift** | Floating-on-water + analysis | Generic |
| **Ferry** | Ferry across straits | Friendly, unique in this niche |
| **Buoy** | Floating marker | Short, distinctive |
| **Reef** | Underwater hazard | Distinctive |

## My top 5 (ranked, with rationale)

1. **Fairway** — best balance of evocative + available + brandable + maritime. Sounds professional in a paper title and a pitch deck.
2. **Sextant** — strong "research-grade scientific instrument" vibe. Pairs naturally with the duality / shadow-prices angle.
3. **Mercator** — historical map projection; visually evocative for an interactive map tool. Good for thesis ("a Mercator-style projection of global oil flow").
4. **OpenCrude** — clearest open-source positioning. "OpenCrude is the open-source crude-oil shock simulator" is a self-explanatory tagline.
5. **Quay** — short, distinctive, maritime, loaded ("dock for loading oil"). Pronounced "key" so memorable.

## Wildcard

If you want pure punch: **Choke**. Single syllable, exactly what the project is about (chokepoints), unforgettable. Risk: a bit aggressive.

## Renaming impact

Renaming touches:
- `pyproject.toml` package name
- `src/straitgraph/` directory and all imports
- `web/package.json` name
- `README.md`, `data/README.md`, `calibration/README.md`
- API title in `api/main.py`
- Docs / external references

Estimate: 30-45 minutes for a clean rename. Single commit `rename: straitgraph -> <chosen>`.

## What the supervisor's paper recommendation tells us

Conlon, Cotter, Eyiah-Donkor (2024) *"Forecasting the price of oil: A
cautionary note"* (Journal of Commodity Markets) is a warning paper: many
oil-price forecasting models fail out-of-sample and look better than they
are. **Useful framing for us**: our project does NOT claim to forecast
oil prices. It quantifies the *transport-cost component* of prices under
specific structural shocks (chokepoint closures, sanctions, capacity
changes). That's a much narrower and more defensible scope.

In any pitch / paper, lead with: "this is a what-if simulator for the
freight component of oil prices, not a price predictor." That respects
the cautionary-note literature while staking out our actual contribution.
