import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import type { Basin, Scenario, Solution, Strait, World } from "./types";

interface Props {
  world: World;
  solution: Solution | null;
  scenario: Scenario;
  onSelectStrait: (id: string) => void;
  onSelectCountry: (iso3: string) => void;
}

const MAP_STYLE = "https://demotiles.maplibre.org/style.json";

function basinLookup(basins: Basin[]): Record<string, Basin> {
  return Object.fromEntries(basins.map((b) => [b.basin_id, b]));
}

function straitGeoJson(
  straits: Strait[],
  basins: Record<string, Basin>,
  solution: Solution | null,
  scenario: Scenario,
) {
  const closed = new Set(scenario.closed_straits);
  const features = straits.map((s) => {
    const a = basins[s.basin_a];
    const b = basins[s.basin_b];
    const flow = solution?.strait_flows[s.strait_id] ?? 0;
    const capacity =
      scenario.strait_capacity_overrides[s.strait_id] ?? s.capacity_mbd;
    const utilisation = capacity > 0 ? Math.min(flow / capacity, 1) : 0;
    const importance = solution?.strait_importance[s.strait_id];
    const importanceLabel =
      importance === null
        ? "infeasible if closed"
        : importance !== undefined
          ? `+${importance.toFixed(2)} ship-days if closed`
          : "";
    return {
      type: "Feature" as const,
      properties: {
        strait_id: s.strait_id,
        name: s.name,
        kind: s.kind,
        flow,
        capacity,
        utilisation,
        closed: closed.has(s.strait_id),
        importanceLabel,
      },
      geometry: {
        type: "LineString" as const,
        coordinates: [
          [a.lon, a.lat],
          [b.lon, b.lat],
        ],
      },
    };
  });
  return {
    type: "FeatureCollection" as const,
    features,
  };
}

function countryGeoJson(world: World, solution: Solution | null, scenario: Scenario) {
  const features = world.countries.map((c) => {
    const prod =
      scenario.country_production_overrides[c.iso3] ?? c.production_mbd;
    const cons =
      scenario.country_consumption_overrides[c.iso3] ?? c.consumption_mbd;
    const net = prod - cons;
    const price = solution?.node_prices[c.iso3] ?? 0;
    return {
      type: "Feature" as const,
      properties: {
        iso3: c.iso3,
        name: c.name,
        production_mbd: prod,
        consumption_mbd: cons,
        net,
        price,
      },
      geometry: { type: "Point" as const, coordinates: [c.lon, c.lat] },
    };
  });
  return { type: "FeatureCollection" as const, features };
}

export default function WorldMap({
  world,
  solution,
  scenario,
  onSelectStrait,
  onSelectCountry,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: [30, 25],
      zoom: 1.6,
      attributionControl: { compact: true },
    });
    mapRef.current = map;

    map.on("load", () => {
      map.addSource("straits", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addSource("countries", { type: "geojson", data: { type: "FeatureCollection", features: [] } });

      map.addLayer({
        id: "strait-lines",
        type: "line",
        source: "straits",
        paint: {
          "line-color": [
            "case",
            ["get", "closed"], "#ef4444",
            ["==", ["get", "kind"], "chokepoint"],
            [
              "interpolate", ["linear"], ["get", "utilisation"],
              0, "#475569",
              0.5, "#f59e0b",
              1, "#ef4444",
            ],
            "#334155",
          ],
          "line-width": [
            "interpolate",
            ["linear"],
            ["get", "flow"],
            0, 1.2,
            5, 2.5,
            15, 5,
            25, 7.5,
          ],
          "line-opacity": 0.9,
        },
      });

      map.addLayer({
        id: "country-circles",
        type: "circle",
        source: "countries",
        paint: {
          "circle-radius": [
            "interpolate", ["linear"],
            ["abs", ["get", "net"]],
            0, 3,
            2, 6,
            8, 11,
            15, 16,
          ],
          "circle-color": [
            "case",
            [">", ["get", "net"], 0.1], "#22c55e",
            ["<", ["get", "net"], -0.1], "#3b82f6",
            "#64748b",
          ],
          "circle-opacity": 0.85,
          "circle-stroke-color": "#0f172a",
          "circle-stroke-width": 1,
        },
      });

      map.addLayer({
        id: "country-labels",
        type: "symbol",
        source: "countries",
        layout: {
          "text-field": ["get", "iso3"],
          "text-size": 10,
          "text-anchor": "top",
          "text-offset": [0, 0.8],
        },
        paint: {
          "text-color": "#cbd5e1",
          "text-halo-color": "#020617",
          "text-halo-width": 1.2,
        },
      });

      map.on("click", "strait-lines", (e) => {
        const f = e.features?.[0];
        if (f) onSelectStrait(f.properties!.strait_id as string);
      });
      map.on("click", "country-circles", (e) => {
        const f = e.features?.[0];
        if (f) onSelectCountry(f.properties!.iso3 as string);
      });
      map.on("mouseenter", "strait-lines", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "strait-lines", () => (map.getCanvas().style.cursor = ""));
      map.on("mouseenter", "country-circles", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "country-circles", () => (map.getCanvas().style.cursor = ""));

      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
      map.on("mousemove", "strait-lines", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties!;
        popup
          .setLngLat(e.lngLat)
          .setHTML(
            `<div class="font-semibold">${p.name}</div>` +
              `<div>flow: ${Number(p.flow).toFixed(2)} mb/d</div>` +
              `<div>capacity: ${Number(p.capacity).toFixed(1)} mb/d</div>` +
              (p.importanceLabel ? `<div class=\"text-xs text-slate-400\">${p.importanceLabel}</div>` : ""),
          )
          .addTo(map);
      });
      map.on("mouseleave", "strait-lines", () => popup.remove());
      map.on("mousemove", "country-circles", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties!;
        popup
          .setLngLat(e.lngLat)
          .setHTML(
            `<div class="font-semibold">${p.name} (${p.iso3})</div>` +
              `<div>production: ${Number(p.production_mbd).toFixed(2)} mb/d</div>` +
              `<div>consumption: ${Number(p.consumption_mbd).toFixed(2)} mb/d</div>` +
              `<div>net: ${Number(p.net).toFixed(2)} mb/d</div>` +
              (p.price ? `<div>price: ${Number(p.price).toFixed(2)}</div>` : ""),
          )
          .addTo(map);
      });
      map.on("mouseleave", "country-circles", () => popup.remove());
    });
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [onSelectStrait, onSelectCountry]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) {
      // wait for load
      const handler = () => pushData();
      map?.once("load", handler);
      return;
    }
    pushData();

    function pushData() {
      const m = mapRef.current;
      if (!m) return;
      const basins = basinLookup(world.basins);
      const straits = straitGeoJson(world.straits, basins, solution, scenario);
      const countries = countryGeoJson(world, solution, scenario);
      (m.getSource("straits") as maplibregl.GeoJSONSource | undefined)?.setData(straits);
      (m.getSource("countries") as maplibregl.GeoJSONSource | undefined)?.setData(countries);
    }
  }, [world, solution, scenario]);

  return <div ref={containerRef} className="h-full w-full" />;
}
