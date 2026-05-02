# Project name — proposals

The package is currently `straitgraph`. Now that the project is more than a
toy graph (it's an open-source crude-oil shock simulator with elastic
demand, real Comtrade data, historical calibration, and an interactive UI),
it deserves a proper name. Comparable closed-source product:
[oilshock.ai](https://oilshock.ai/#simulator).

## Shortlist

| Name | Why | Concerns |
|---|---|---|
| **Fairway** | Maritime word for a navigable shipping channel. Unused in this niche, evocative, friendly. | Some unrelated golf SaaS use it. |
| **Sextant** | Historical navigation instrument. Suggests precision, research, maritime. | Existing `sextant.ai` (logging) — different domain. |
| **OpenShock** | Direct competitive positioning vs oilshock.ai (closed) → ours is open. Self-explanatory. | Ties branding to the closed competitor. |
| **OilStrait** | Descriptive, googleable, unambiguous. | Less memorable. |
| **Hormuz** | Single chokepoint name carries the whole maritime/oil story; instantly recognized by traders. | Locks the brand to one strait; geopolitically loaded. |
| **Beacon** | Lighthouse / navigation aid. Bright, minimal. | Generic — many products use it. |
| **Anchor** | Maritime, "anchor your scenarios". | Very generic. |
| **Wakeflow** | Wake of a ship + flow. | Made-up word; needs explanation. |
| **straitgraph** (keep) | Honest about the technology (graph theory + straits). | Less marketable to a trader audience. |

## My ranking

1. **Fairway** — best balance of evocative, available, and clean
2. **OpenShock** — cleanest competitive narrative
3. **Sextant** — most prestigious / academic feel
4. **straitgraph** (keep) — honest, technical, lowest-effort

## Renaming impact

Renaming touches:
- `pyproject.toml` package name
- `src/straitgraph/` directory and all imports (api, calibration, tests)
- `web/package.json` name
- `README.md`, `data/README.md`, `calibration/README.md`
- API title in `api/main.py`
- Any deployed URLs

Estimate: 30 minutes for a clean rename, then a single commit.

## Decision needed

When you pick one, I'll do the rename in one sweep and commit as
`rename: straitgraph -> <name>`.
