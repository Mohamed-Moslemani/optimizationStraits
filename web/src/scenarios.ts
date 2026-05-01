import type { Scenario } from "./types";
import { EMPTY_SCENARIO } from "./types";

export interface Preset {
  id: string;
  label: string;
  description: string;
  build: () => Scenario;
}

export const PRESETS: Preset[] = [
  {
    id: "base",
    label: "Base case",
    description: "Unperturbed 2023 oil market.",
    build: () => ({ ...EMPTY_SCENARIO }),  // keep current pricing anchors
  },
  {
    id: "red_sea_crisis",
    label: "Red Sea crisis (2024)",
    description:
      "Bab el-Mandeb and Suez effectively closed — tankers reroute around the Cape of Good Hope.",
    build: () => ({
      ...EMPTY_SCENARIO,
      strait_capacity_overrides: { bab_el_mandeb: 0.5, suez: 0.5 },
    }),
  },
  {
    id: "close_hormuz",
    label: "Close Strait of Hormuz",
    description:
      "Iran blockades Hormuz. Expect infeasibility: ~15 mb/d of Persian Gulf exports have no alternative in the current graph.",
    build: () => ({ ...EMPTY_SCENARIO, closed_straits: ["hormuz"] }),
  },
  {
    id: "close_malacca",
    label: "Close Strait of Malacca",
    description:
      "Incident at the Phillips Channel. No Lombok/Sunda alternative is modeled yet.",
    build: () => ({ ...EMPTY_SCENARIO, closed_straits: ["malacca"] }),
  },
  {
    id: "suez_50",
    label: "Suez at 50% capacity",
    description: "Evergreen-style partial blockage of the Suez Canal.",
    build: () => ({
      ...EMPTY_SCENARIO,
      strait_capacity_overrides: { suez: 5.0 },
    }),
  },
  {
    id: "russia_sanctions",
    label: "Russia sanctions (hard)",
    description:
      "Russian production falls to 3 mb/d; Danish and Turkish Straits see no Russian transit.",
    build: () => ({
      ...EMPTY_SCENARIO,
      country_production_overrides: { RUS: 3.0 },
      strait_capacity_overrides: { danish_straits: 0.5 },
    }),
  },
];
