import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import { STRAIT_PATHS } from "./straitPaths";
import type { Scenario, Solution, Strait, World } from "./types";

interface Props {
  world: World;
  solution: Solution | null;
  scenario: Scenario;
  onSelectStrait: (id: string) => void;
  onSelectCountry: (iso3: string) => void;
}

// Free, no-auth light basemap. Ocean is pale blue, land is near-white with
// subtle country borders. Perfect for overlaying our data.
const MAP_STYLE =
  "https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json";

function defaultPath(s: Strait, basinCoord: (id: string) => [number, number]) {
  return [basinCoord(s.basin_a), basinCoord(s.basin_b)];
}

function straitGeoJson(
  world: World,
  solution: Solution | null,
  scenario: Scenario,
) {
  const basinCoord = (id: string): [number, number] => {
    const b = world.basins.find((x) => x.basin_id === id);
    return b ? [b.lon, b.lat] : [0, 0];
  };
  const closed = new Set(scenario.closed_straits);
  const features = world.straits.map((s) => {
    const path = STRAIT_PATHS[s.strait_id] ?? defaultPath(s, basinCoord);
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
        coordinates: path,
      },
    };
  });
  return { type: "FeatureCollection" as const, features };
}

function countryGeoJson(
  world: World,
  solution: Solution | null,
  scenario: Scenario,
) {
  const features = world.countries.map((c) => {
    const prod =
      scenario.country_production_overrides[c.iso3] ?? c.production_mbd;
    const cons =
      scenario.country_consumption_overrides[c.iso3] ?? c.consumption_mbd;
    const net = prod - cons;
    const delivered = solution?.delivered_prices_usd[c.iso3] ?? 0;
    const delta = solution?.price_delta_vs_base_usd[c.iso3] ?? 0;
    const cut = solution?.demand_cut_mbd[c.iso3] ?? 0;
    const shutIn = solution?.shut_in_supply_mbd[c.iso3] ?? 0;
    return {
      type: "Feature" as const,
      properties: {
        iso3: c.iso3,
        name: c.name,
        production_mbd: prod,
        consumption_mbd: cons,
        net,
        delivered,
        delta,
        cut,
        shutIn,
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
      center: [30, 20],
      zoom: 1.9,
      attributionControl: { compact: true },
      maxZoom: 6,
      minZoom: 1.2,
    });
    mapRef.current = map;

    map.on("load", () => {
      map.addSource("straits", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
        lineMetrics: true,
      });
      map.addSource("countries", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      // Strait glow (soft halo underneath) — wider, brighter
      map.addLayer({
        id: "strait-glow",
        type: "line",
        source: "straits",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": [
            "case",
            ["get", "closed"], "#dc2626",
            ["==", ["get", "kind"], "pipeline"], "#92400e",
            ["==", ["get", "kind"], "chokepoint"],
            [
              "interpolate", ["linear"], ["get", "utilisation"],
              0, "#0ea5e9",     // sky-500: low util = ocean blue (peaceful)
              0.5, "#f59e0b",   // amber-500: medium = warming
              1, "#dc2626",     // red-600: at capacity = stress
            ],
            "#0ea5e9",
          ],
          "line-width": [
            "interpolate", ["linear"], ["get", "flow"],
            0, 4, 5, 12, 15, 22, 25, 30,
          ],
          "line-opacity": 0.22,
          "line-blur": 10,
        },
      });

      // Main strait line — bolder, with line-gradient (origin→dest direction read)
      map.addLayer({
        id: "strait-lines",
        type: "line",
        source: "straits",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": [
            "case",
            ["get", "closed"], "#dc2626",
            ["==", ["get", "kind"], "pipeline"], "#b45309",
            ["==", ["get", "kind"], "chokepoint"],
            [
              "interpolate", ["linear"], ["get", "utilisation"],
              0, "#0284c7",   // sky-600: low util
              0.5, "#ea580c", // orange-600: medium
              1, "#b91c1c",   // red-700: critical
            ],
            "#0284c7",
          ],
          "line-width": [
            "interpolate", ["linear"], ["get", "flow"],
            0, 1.5, 5, 3.0, 15, 5.0, 25, 7.0,
          ],
          "line-dasharray": [
            "case",
            ["==", ["get", "kind"], "open"], ["literal", [4, 3]],
            ["==", ["get", "kind"], "pipeline"], ["literal", [1, 2]],
            ["literal", [1, 0]],
          ],
          "line-opacity": 1.0,
        },
      });

      // Direction arrows along high-flow straits
      map.addLayer({
        id: "strait-arrows",
        type: "symbol",
        source: "straits",
        filter: [">", ["get", "flow"], 1.0],
        layout: {
          "symbol-placement": "line",
          "symbol-spacing": 110,
          "text-field": "▶",
          "text-size": 12,
          "text-keep-upright": false,
          "text-rotation-alignment": "map",
          "text-allow-overlap": true,
          "text-ignore-placement": true,
        },
        paint: {
          "text-color": [
            "case",
            ["get", "closed"], "#7f1d1d",
            ["==", ["get", "kind"], "pipeline"], "#78350f",
            "#0c4a6e",
          ],
          "text-halo-color": "#ffffff",
          "text-halo-width": 1.6,
          "text-opacity": 0.85,
        },
      });

      // Country markers — dramatically more visible
      // Outer soft halo (suggests trade volume + draws the eye)
      map.addLayer({
        id: "country-halo",
        type: "circle",
        source: "countries",
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["abs", ["get", "net"]],
            0, 8, 2, 16, 8, 28, 15, 40,
          ],
          "circle-color": [
            "case",
            [">", ["get", "net"], 0.1], "#0f766e",     // teal-700
            ["<", ["get", "net"], -0.1], "#c2410c",    // orange-700
            "#94a3b8",
          ],
          "circle-opacity": 0.18,
          "circle-blur": 0.9,
        },
      });

      // Solid bright disc (the visible marker)
      map.addLayer({
        id: "country-circles",
        type: "circle",
        source: "countries",
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["abs", ["get", "net"]],
            0, 5, 2, 9, 8, 15, 15, 22,
          ],
          "circle-color": [
            "case",
            [">", ["get", "net"], 0.1], "#0d9488",   // teal-600 — deep green-blue
            ["<", ["get", "net"], -0.1], "#ea580c",  // orange-600 — deep orange
            "#94a3b8",
          ],
          "circle-opacity": 1.0,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2.5,
        },
      });

      // Inner highlight ring for a "pin" feel (subtle 3D shading)
      map.addLayer({
        id: "country-highlight",
        type: "circle",
        source: "countries",
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["abs", ["get", "net"]],
            0, 2, 2, 3.5, 8, 6, 15, 9,
          ],
          "circle-color": "#ffffff",
          "circle-opacity": 0.35,
          "circle-translate": [0, -1.5],
        },
      });

      map.addLayer({
        id: "country-labels",
        type: "symbol",
        source: "countries",
        layout: {
          "text-field": ["get", "iso3"],
          "text-size": 11,
          "text-anchor": "top",
          "text-offset": [0, 1.1],
          "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
        },
        paint: {
          "text-color": "#0f172a",
          "text-halo-color": "#ffffff",
          "text-halo-width": 2.0,
          "text-halo-blur": 0.4,
        },
      });

      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        offset: 10,
      });

      map.on("click", "strait-lines", (e) => {
        const f = e.features?.[0];
        if (f) onSelectStrait(f.properties!.strait_id as string);
      });
      map.on("click", "country-circles", (e) => {
        const f = e.features?.[0];
        if (f) onSelectCountry(f.properties!.iso3 as string);
      });

      for (const layer of ["strait-lines", "country-circles"]) {
        map.on("mouseenter", layer, () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", layer, () => {
          map.getCanvas().style.cursor = "";
          popup.remove();
        });
      }

      map.on("mousemove", "strait-lines", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties!;
        popup
          .setLngLat(e.lngLat)
          .setHTML(
            `<div class="popup-title">${p.name}</div>` +
              `<div class="popup-row"><span>flow</span><span>${Number(p.flow).toFixed(2)} mb/d</span></div>` +
              `<div class="popup-row"><span>capacity</span><span>${Number(p.capacity).toFixed(1)} mb/d</span></div>` +
              (p.importanceLabel
                ? `<div class="popup-note">${p.importanceLabel}</div>`
                : ""),
          )
          .addTo(map);
      });
      map.on("mousemove", "country-circles", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties!;
        const netClass = Number(p.net) > 0 ? "exporter" : "importer";
        const delivered = Number(p.delivered);
        const delta = Number(p.delta);
        const deltaSign = delta > 0.01 ? "up" : delta < -0.01 ? "down" : "";
        const cut = Number(p.cut);
        const shutIn = Number(p.shutIn);
        const gapBlock =
          cut > 0.01
            ? `<div class="popup-row"><span>demand cut</span><span class="up">${cut.toFixed(2)} mb/d</span></div>`
            : shutIn > 0.01
              ? `<div class="popup-row"><span>shut-in supply</span><span class="up">${shutIn.toFixed(2)} mb/d</span></div>`
              : "";
        const priceBlock = delivered
          ? `<div class="popup-row popup-price"><span>delivered</span><span>$${delivered.toFixed(2)}/bbl</span></div>` +
            (Math.abs(delta) > 0.005
              ? `<div class="popup-row"><span>vs base</span><span class="${deltaSign}">${delta >= 0 ? "+" : ""}$${delta.toFixed(2)}</span></div>`
              : "") +
            gapBlock
          : "";
        popup
          .setLngLat(e.lngLat)
          .setHTML(
            `<div class="popup-title">${p.name} <span class="popup-iso">${p.iso3}</span></div>` +
              `<div class="popup-row"><span>production</span><span>${Number(p.production_mbd).toFixed(2)} mb/d</span></div>` +
              `<div class="popup-row"><span>consumption</span><span>${Number(p.consumption_mbd).toFixed(2)} mb/d</span></div>` +
              `<div class="popup-row"><span>net</span><span class="${netClass}">${Number(p.net).toFixed(2)} mb/d</span></div>` +
              priceBlock,
          )
          .addTo(map);
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [onSelectStrait, onSelectCountry]);

  useEffect(() => {
    const push = () => {
      const m = mapRef.current;
      if (!m) return;
      const straits = straitGeoJson(world, solution, scenario);
      const countries = countryGeoJson(world, solution, scenario);
      (m.getSource("straits") as maplibregl.GeoJSONSource | undefined)?.setData(
        straits,
      );
      (
        m.getSource("countries") as maplibregl.GeoJSONSource | undefined
      )?.setData(countries);
    };
    const m = mapRef.current;
    if (!m) return;
    if (m.isStyleLoaded()) push();
    else m.once("load", push);
  }, [world, solution, scenario]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      <MapLegend />
    </div>
  );
}

function MapLegend() {
  return (
    <div className="pointer-events-none absolute bottom-4 left-4 rounded-md border border-slate-200 bg-white/95 p-3 text-xs text-slate-700 shadow-sm backdrop-blur">
      <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        Legend
      </div>
      <div className="flex items-center gap-2">
        <span className="inline-block h-3 w-3 rounded-full bg-teal-600 ring-2 ring-white shadow-sm" />
        <span>exporter (net supply)</span>
      </div>
      <div className="mt-1.5 flex items-center gap-2">
        <span className="inline-block h-3 w-3 rounded-full bg-orange-600 ring-2 ring-white shadow-sm" />
        <span>importer (net demand)</span>
      </div>
      <div className="mt-3 mb-0.5 text-[9px] font-semibold uppercase tracking-wider text-slate-500">
        Strait flow / utilisation
      </div>
      <div className="flex items-center gap-2">
        <span className="inline-block h-1 w-7 bg-sky-600" />
        <span>flowing freely</span>
      </div>
      <div className="mt-1 flex items-center gap-2">
        <span className="inline-block h-1.5 w-7 bg-orange-600" />
        <span>medium pressure</span>
      </div>
      <div className="mt-1 flex items-center gap-2">
        <span className="inline-block h-2 w-7 bg-red-700" />
        <span>near capacity</span>
      </div>
      <div className="mt-1.5 flex items-center gap-2">
        <span className="inline-block h-0.5 w-7 border-t border-dashed border-sky-600" />
        <span>open ocean</span>
      </div>
      <div className="mt-1 flex items-center gap-2">
        <span className="inline-block h-0.5 w-7 border-t-2 border-dotted border-amber-700" />
        <span>pipeline</span>
      </div>
    </div>
  );
}
