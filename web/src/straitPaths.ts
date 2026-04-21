/**
 * Hand-crafted shipping-lane waypoints for each strait/open-ocean edge.
 * Coordinates are [lon, lat]. Longitudes > 180 wrap the antimeridian cleanly
 * (MapLibre interprets them as continuous — prevents lines wrapping backward
 * across the whole map for trans-Pacific routes).
 *
 * Endpoints are near the relevant basin centroids so strait lines start and
 * end on open water, not inside landmasses.
 */
export const STRAIT_PATHS: Record<string, [number, number][]> = {
  // Persian Gulf <-> Indian Ocean via Strait of Hormuz
  hormuz: [
    [52, 27],
    [54, 27],
    [55.5, 26.8],
    [56.3, 26.5],
    [57, 25.5],
    [58, 24],
    [60, 22],
    [63, 18],
    [67, 10],
    [70, 0],
  ],
  // Red Sea <-> Gulf of Aden via Bab el-Mandeb
  bab_el_mandeb: [
    [38, 21],
    [40, 18],
    [42, 14],
    [43.3, 12.6],
    [44, 12],
    [46, 12.5],
    [48, 13],
  ],
  // Red Sea <-> Mediterranean via Suez Canal
  suez: [
    [38, 21],
    [35, 25],
    [33, 28],
    [32.5, 30],
    [32.3, 31.2],
    [32.3, 32],
    [33, 33],
    [30, 34],
    [25, 35],
    [20, 36],
    [15, 37],
  ],
  // Black Sea <-> Mediterranean via Bosphorus + Dardanelles
  bosphorus: [
    [35, 43],
    [32, 42],
    [29, 41.2],
    [28.5, 40.9],
    [27, 40.4],
    [26, 40],
    [25, 38.5],
    [22, 37.5],
    [18, 37],
    [15, 37],
  ],
  // Baltic <-> North Sea via Danish Straits
  danish_straits: [
    [20, 58],
    [17, 57],
    [14, 56],
    [12, 56.2],
    [10.5, 56.8],
    [8, 57],
    [5, 56.5],
    [3, 56],
  ],
  // Indian Ocean <-> South China Sea via Strait of Malacca
  malacca: [
    [70, 0],
    [85, 3],
    [92, 5],
    [97, 5],
    [99, 3],
    [101, 2],
    [103.5, 1.3],
    [105, 2],
    [108, 6],
    [113, 12],
  ],
  // Caribbean <-> Eastern Pacific via Panama Canal
  panama: [
    [-75, 15],
    [-78, 12],
    [-79.5, 9.3],
    [-79.7, 8.9],
    [-81, 8],
    [-90, 10],
    [-110, 15],
    [-130, 20],
  ],
  // Gulf of Aden <-> Indian Ocean (open Arabian Sea)
  goa_io: [
    [48, 13],
    [55, 10],
    [62, 5],
    [70, 0],
  ],
  // Mediterranean <-> North Atlantic via Gibraltar
  med_natl: [
    [15, 37],
    [5, 36.5],
    [-3, 36],
    [-5.6, 36],
    [-8, 37],
    [-15, 38],
    [-25, 39],
    [-40, 40],
  ],
  // North Atlantic <-> South Atlantic (open ocean)
  natl_satl: [
    [-40, 40],
    [-30, 20],
    [-22, 0],
    [-15, -20],
  ],
  // South Atlantic <-> Indian Ocean via Cape of Good Hope
  satl_io: [
    [-15, -20],
    [0, -30],
    [15, -34],
    [20, -35],
    [25, -35],
    [35, -33],
    [45, -25],
    [55, -15],
    [65, -5],
    [70, 0],
  ],
  // South China Sea <-> Western Pacific
  scs_wpac: [
    [113, 12],
    [120, 18],
    [125, 22],
    [130, 24],
    [135, 25],
    [140, 25],
  ],
  // Western Pacific <-> Eastern Pacific (trans-Pacific, crosses dateline)
  wpac_epac: [
    [140, 25],
    [160, 32],
    [180, 37],
    [200, 35],
    [220, 28],
    [230, 20],
  ],
  // Caribbean <-> North Atlantic (Florida Straits)
  car_natl: [
    [-75, 15],
    [-70, 22],
    [-65, 28],
    [-60, 32],
    [-50, 36],
    [-40, 40],
  ],
  // North Sea <-> North Atlantic
  ns_natl: [
    [3, 56],
    [-3, 58],
    [-10, 58],
    [-18, 55],
    [-28, 48],
    [-40, 40],
  ],
};
