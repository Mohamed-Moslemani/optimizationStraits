import type { Scenario } from "./types";
import { EMPTY_SCENARIO } from "./types";

export type PresetCategory = "what_if" | "historical";

export interface Preset {
  id: string;
  label: string;
  description: string;
  category: PresetCategory;
  build: () => Scenario;
  /** Optional period (YYYY-MM) for historical presets — shown in the UI. */
  period?: string;
  /** Period-accurate Brent — shown next to the label. */
  brent_usd?: number;
}

export const PRESETS: Preset[] = [
  // ─── Base case ───────────────────────────────────────────────────────
  {
    id: "base",
    category: "what_if",
    label: "Base case",
    description: "Unperturbed 2023 oil market.",
    build: () => ({ ...EMPTY_SCENARIO }),
  },

  // ─── Historical episodes (matched to calibration/episodes.py) ────────
  {
    id: "ever_given_2021",
    category: "historical",
    label: "Ever Given (Mar 2021)",
    period: "2021-03",
    brent_usd: 65.41,
    description:
      "Container ship blocks Suez Canal for 6 days. SUMED pipeline keeps running at ~2.5 mb/d. Period-accurate Brent + freight cost calibrated to the disruption.",
    build: () => ({
      ...EMPTY_SCENARIO,
      strait_capacity_overrides: { suez: 2.5 },
      demand_elasticity: 0.05,
      ship_day_cost_usd_per_bbl: 1.3,
      reference_price_usd_per_bbl: 65.41,
    }),
  },
  {
    id: "russia_2022",
    category: "historical",
    label: "Russia sanctions (May 2022)",
    period: "2022-05",
    brent_usd: 113.34,
    description:
      "Post-invasion Russian production falls ~600 kb/d; Danish Straits transits halve as flows redirect to India and China. Brent had already hit $113.",
    build: () => ({
      ...EMPTY_SCENARIO,
      country_production_overrides: { RUS: 9.5 },
      strait_capacity_overrides: { danish_straits: 1.5 },
      demand_elasticity: 0.08,
      ship_day_cost_usd_per_bbl: 1.7,
      reference_price_usd_per_bbl: 113.34,
    }),
  },
  {
    id: "red_sea_2024",
    category: "historical",
    label: "Red Sea crisis (Feb 2024)",
    period: "2024-02",
    brent_usd: 83.48,
    description:
      "Houthi attacks force ~50% of Suez and Bab el-Mandeb tanker traffic around the Cape, adding 10-14 days to Asia-Europe voyages. VLCC rates roughly tripled.",
    build: () => ({
      ...EMPTY_SCENARIO,
      strait_capacity_overrides: { bab_el_mandeb: 3.0, suez: 4.5 },
      demand_elasticity: 0.07,
      ship_day_cost_usd_per_bbl: 2.2,
      reference_price_usd_per_bbl: 83.48,
    }),
  },

  // ─── What-if scenarios (synthetic stress tests) ──────────────────────
  {
    id: "red_sea_severe",
    category: "what_if",
    label: "Red Sea — full closure",
    description:
      "Suez + Bab el-Mandeb fully closed. Model's honest verdict: minimal global Brent impact (Saudi reroutes to Asia via Hormuz; Atlantic suppliers cover Europe directly). The visible move is a spread — Atlantic crudes drop, European delivery via Cape gets more expensive.",
    build: () => ({
      ...EMPTY_SCENARIO,
      strait_capacity_overrides: { bab_el_mandeb: 0.1, suez: 0.1 },
      demand_elasticity: 0.05,
      ship_day_cost_usd_per_bbl: 2.5,
    }),
  },
  {
    id: "close_hormuz",
    category: "what_if",
    label: "Close Strait of Hormuz",
    description:
      "Iran blockades Hormuz. Persian Gulf exports stranded above the East-West Pipeline's 5 mb/d limit. Rigid demand + war-risk freight to surface the price impact.",
    build: () => ({
      ...EMPTY_SCENARIO,
      closed_straits: ["hormuz"],
      demand_elasticity: 0.05,
      ship_day_cost_usd_per_bbl: 2.5,
    }),
  },
  {
    id: "close_malacca",
    category: "what_if",
    label: "Close Strait of Malacca",
    description:
      "Incident at the Phillips Channel. Lombok/Sunda absorbs only 3 mb/d of the 13+ mb/d that normally transits Malacca. Rigid demand + war-risk freight to surface the price impact.",
    build: () => ({
      ...EMPTY_SCENARIO,
      closed_straits: ["malacca"],
      demand_elasticity: 0.05,
      ship_day_cost_usd_per_bbl: 2.5,
    }),
  },
  {
    id: "russia_hard",
    category: "what_if",
    label: "Russia — extreme cut",
    description:
      "Russian production collapses to 3 mb/d; Danish Straits transits drop to a trickle. Rigid demand + war-risk freight to surface the price impact.",
    build: () => ({
      ...EMPTY_SCENARIO,
      country_production_overrides: { RUS: 3.0 },
      strait_capacity_overrides: { danish_straits: 0.5 },
      demand_elasticity: 0.05,
      ship_day_cost_usd_per_bbl: 2.5,
    }),
  },
];
