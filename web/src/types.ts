export interface Country {
  iso3: string;
  name: string;
  production_mbd: number;
  consumption_mbd: number;
  net_mbd: number;
  lat: number;
  lon: number;
}

export interface Basin {
  basin_id: string;
  name: string;
  lat: number;
  lon: number;
}

export interface Coastline {
  iso3: string;
  basin_id: string;
}

export interface Strait {
  strait_id: string;
  name: string;
  basin_a: string;
  basin_b: string;
  kind: "chokepoint" | "open";
  capacity_mbd: number;
  distance_nm: number;
  transit_days: number;
}

export interface World {
  countries: Country[];
  basins: Basin[];
  coastlines: Coastline[];
  straits: Strait[];
}

export interface Flow {
  source: string;
  target: string;
  mbd: number;
  kind: string;
  strait_id: string | null;
}

export interface Solution {
  status: string;
  total_cost: number;
  total_supply: number;
  total_demand: number;
  flows: Flow[];
  strait_flows: Record<string, number>;
  node_prices: Record<string, number>;
  capacity_duals: Record<string, number>;
  strait_importance: Record<string, number | null>;
  delivered_prices_usd: Record<string, number>;
  price_delta_vs_base_usd: Record<string, number>;
  global_avg_price_usd: number;
  global_avg_price_delta_usd: number;
  unmet_demand_mbd: Record<string, number>;
  total_unmet_mbd: number;
  shut_in_supply_mbd: Record<string, number>;
  total_shut_in_mbd: number;
}

export interface Scenario {
  strait_capacity_overrides: Record<string, number>;
  closed_straits: string[];
  country_production_overrides: Record<string, number>;
  country_consumption_overrides: Record<string, number>;
  reference_price_usd_per_bbl: number;
  ship_day_cost_usd_per_bbl: number;
}

export const DEFAULT_REFERENCE_PRICE = 85;
export const DEFAULT_SHIP_DAY_COST = 1;

export const EMPTY_SCENARIO: Scenario = {
  strait_capacity_overrides: {},
  closed_straits: [],
  country_production_overrides: {},
  country_consumption_overrides: {},
  reference_price_usd_per_bbl: DEFAULT_REFERENCE_PRICE,
  ship_day_cost_usd_per_bbl: DEFAULT_SHIP_DAY_COST,
};
