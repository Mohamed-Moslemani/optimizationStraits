import type { Country, Scenario, Strait, World } from "./types";
import {
  DEFAULT_ELASTICITY,
  DEFAULT_REFERENCE_PRICE,
  DEFAULT_SHIP_DAY_COST,
  EMPTY_SCENARIO,
} from "./types";
import { PRESETS } from "./scenarios";

interface Props {
  world: World;
  scenario: Scenario;
  setScenario: (s: Scenario) => void;
  selectedStrait: Strait | null;
  selectedCountry: Country | null;
  onDeselect: () => void;
}

export default function ScenarioPanel({
  world,
  scenario,
  setScenario,
  selectedStrait,
  selectedCountry,
  onDeselect,
}: Props) {
  return (
    <div className="flex h-full flex-col overflow-y-auto p-5">
      <SectionHeader title="Scenario">
        <button
          onClick={() => setScenario({ ...EMPTY_SCENARIO })}
          className="text-xs text-slate-500 hover:text-sky-600"
        >
          reset all
        </button>
      </SectionHeader>
      <p className="mt-1 text-xs text-slate-500">
        Click a strait or country on the map to edit it. The model re-solves
        live.
      </p>

      <SectionHeader title="Presets" className="mt-6" />
      <div className="mt-2 flex flex-col gap-1.5">
        {PRESETS.map((p) => (
          <button
            key={p.id}
            onClick={() =>
              setScenario({
                ...p.build(),
                reference_price_usd_per_bbl: scenario.reference_price_usd_per_bbl,
                ship_day_cost_usd_per_bbl: scenario.ship_day_cost_usd_per_bbl,
                demand_elasticity: scenario.demand_elasticity,
              })
            }
            className="rounded-md border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-700 transition hover:border-sky-300 hover:bg-sky-50 hover:text-sky-900"
            title={p.description}
          >
            {p.label}
          </button>
        ))}
      </div>

      <PriceAnchors scenario={scenario} setScenario={setScenario} />

      {selectedStrait && (
        <StraitEditor
          strait={selectedStrait}
          scenario={scenario}
          setScenario={setScenario}
          onClose={onDeselect}
        />
      )}

      {selectedCountry && (
        <CountryEditor
          country={selectedCountry}
          scenario={scenario}
          setScenario={setScenario}
          onClose={onDeselect}
        />
      )}

      <ActiveEditsSummary
        world={world}
        scenario={scenario}
        setScenario={setScenario}
      />
    </div>
  );
}

function PriceAnchors({
  scenario,
  setScenario,
}: {
  scenario: Scenario;
  setScenario: (s: Scenario) => void;
}) {
  const refPrice = scenario.reference_price_usd_per_bbl;
  const shipCost = scenario.ship_day_cost_usd_per_bbl;
  const elast = scenario.demand_elasticity;
  const isCustom =
    refPrice !== DEFAULT_REFERENCE_PRICE ||
    shipCost !== DEFAULT_SHIP_DAY_COST ||
    elast !== DEFAULT_ELASTICITY;
  return (
    <section className="mt-6">
      <SectionHeader title="Market parameters">
        {isCustom && (
          <button
            onClick={() =>
              setScenario({
                ...scenario,
                reference_price_usd_per_bbl: DEFAULT_REFERENCE_PRICE,
                ship_day_cost_usd_per_bbl: DEFAULT_SHIP_DAY_COST,
                demand_elasticity: DEFAULT_ELASTICITY,
              })
            }
            className="text-xs text-slate-500 hover:text-sky-600"
          >
            defaults
          </button>
        )}
      </SectionHeader>
      <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3">
        <label className="block text-xs text-slate-600">
          Reference Brent:{" "}
          <span className="font-mono text-slate-900">
            ${refPrice.toFixed(0)}/bbl
          </span>
        </label>
        <input
          type="range"
          min={40}
          max={140}
          step={1}
          value={refPrice}
          onChange={(e) =>
            setScenario({
              ...scenario,
              reference_price_usd_per_bbl: parseFloat(e.target.value),
            })
          }
          className="mt-1 w-full"
        />
        <label className="mt-3 block text-xs text-slate-600">
          Freight:{" "}
          <span className="font-mono text-slate-900">
            ${shipCost.toFixed(2)}/bbl per ship-day
          </span>
        </label>
        <input
          type="range"
          min={0.25}
          max={4}
          step={0.05}
          value={shipCost}
          onChange={(e) =>
            setScenario({
              ...scenario,
              ship_day_cost_usd_per_bbl: parseFloat(e.target.value),
            })
          }
          className="mt-1 w-full"
        />
        <label className="mt-3 block text-xs text-slate-600">
          Demand elasticity:{" "}
          <span className="font-mono text-slate-900">{elast.toFixed(2)}</span>
        </label>
        <input
          type="range"
          min={0.05}
          max={1.0}
          step={0.05}
          value={elast}
          onChange={(e) =>
            setScenario({
              ...scenario,
              demand_elasticity: parseFloat(e.target.value),
            })
          }
          className="mt-1 w-full"
        />
        <p className="mt-2 text-[10px] leading-snug text-slate-500">
          Short-run oil ε ≈ 0.05 (rigid), 1y ε ≈ 0.2-0.3, multi-year ε ≈ 0.5+.
          Lower elasticity → bigger price spikes for the same shock; higher →
          demand response cushions prices.
        </p>
      </div>
    </section>
  );
}

function SectionHeader({
  title,
  children,
  className = "",
}: {
  title: string;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex items-center justify-between border-b border-slate-200 pb-1.5 ${className}`}
    >
      <h2 className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
        {title}
      </h2>
      {children}
    </div>
  );
}

function StraitEditor({
  strait,
  scenario,
  setScenario,
  onClose,
}: {
  strait: Strait;
  scenario: Scenario;
  setScenario: (s: Scenario) => void;
  onClose: () => void;
}) {
  const override = scenario.strait_capacity_overrides[strait.strait_id];
  const current = override ?? strait.capacity_mbd;
  const isClosed = scenario.closed_straits.includes(strait.strait_id);
  const max = Math.max(strait.capacity_mbd * 1.5, 5);

  const setCap = (v: number) => {
    const overrides = { ...scenario.strait_capacity_overrides };
    if (Math.abs(v - strait.capacity_mbd) < 0.01)
      delete overrides[strait.strait_id];
    else overrides[strait.strait_id] = v;
    setScenario({
      ...scenario,
      strait_capacity_overrides: overrides,
      closed_straits: scenario.closed_straits.filter(
        (s) => s !== strait.strait_id,
      ),
    });
  };

  const toggleClose = () => {
    if (isClosed) {
      setScenario({
        ...scenario,
        closed_straits: scenario.closed_straits.filter(
          (s) => s !== strait.strait_id,
        ),
      });
    } else {
      setScenario({
        ...scenario,
        closed_straits: [...scenario.closed_straits, strait.strait_id],
      });
    }
  };

  return (
    <section className="mt-6 rounded-lg border border-sky-200 bg-white p-3 shadow-sm">
      <div className="mb-2 flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            {strait.name}
          </h3>
          <div className="text-[10px] uppercase tracking-wider text-slate-500">
            {strait.kind} · {strait.transit_days.toFixed(1)} days
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-700"
          aria-label="close"
        >
          ✕
        </button>
      </div>
      <label className="block text-xs text-slate-600">
        Capacity:{" "}
        <span className="font-mono text-slate-900">
          {isClosed ? "closed" : `${current.toFixed(1)} mb/d`}
        </span>
      </label>
      <input
        type="range"
        min={0}
        max={max}
        step={0.1}
        value={isClosed ? 0 : current}
        disabled={isClosed}
        onChange={(e) => setCap(parseFloat(e.target.value))}
        className="mt-1 w-full"
      />
      <div className="mt-3 flex gap-2">
        <button
          onClick={toggleClose}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
            isClosed
              ? "bg-red-100 text-red-700 hover:bg-red-200"
              : "bg-slate-100 text-slate-700 hover:bg-slate-200"
          }`}
        >
          {isClosed ? "reopen" : "close strait"}
        </button>
        {override !== undefined && (
          <button
            onClick={() => setCap(strait.capacity_mbd)}
            className="rounded-md bg-slate-100 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-200"
          >
            reset
          </button>
        )}
      </div>
    </section>
  );
}

function CountryEditor({
  country,
  scenario,
  setScenario,
  onClose,
}: {
  country: Country;
  scenario: Scenario;
  setScenario: (s: Scenario) => void;
  onClose: () => void;
}) {
  const prod =
    scenario.country_production_overrides[country.iso3] ??
    country.production_mbd;
  const cons =
    scenario.country_consumption_overrides[country.iso3] ??
    country.consumption_mbd;

  const setProd = (v: number) => {
    const o = { ...scenario.country_production_overrides };
    if (Math.abs(v - country.production_mbd) < 0.01) delete o[country.iso3];
    else o[country.iso3] = v;
    setScenario({ ...scenario, country_production_overrides: o });
  };
  const setCons = (v: number) => {
    const o = { ...scenario.country_consumption_overrides };
    if (Math.abs(v - country.consumption_mbd) < 0.01) delete o[country.iso3];
    else o[country.iso3] = v;
    setScenario({ ...scenario, country_consumption_overrides: o });
  };

  const prodMax = Math.max(country.production_mbd * 2, 5);
  const consMax = Math.max(country.consumption_mbd * 2, 5);
  const net = prod - cons;

  return (
    <section className="mt-6 rounded-lg border border-sky-200 bg-white p-3 shadow-sm">
      <div className="mb-2 flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            {country.name}
          </h3>
          <div className="text-[10px] uppercase tracking-wider text-slate-500">
            {country.iso3}
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-700"
          aria-label="close"
        >
          ✕
        </button>
      </div>

      <label className="block text-xs text-slate-600">
        Production:{" "}
        <span className="font-mono text-slate-900">{prod.toFixed(2)} mb/d</span>
      </label>
      <input
        type="range"
        min={0}
        max={prodMax}
        step={0.05}
        value={prod}
        onChange={(e) => setProd(parseFloat(e.target.value))}
        className="mt-1 w-full"
      />

      <label className="mt-3 block text-xs text-slate-600">
        Consumption:{" "}
        <span className="font-mono text-slate-900">{cons.toFixed(2)} mb/d</span>
      </label>
      <input
        type="range"
        min={0}
        max={consMax}
        step={0.05}
        value={cons}
        onChange={(e) => setCons(parseFloat(e.target.value))}
        className="mt-1 w-full"
      />

      <div
        className={`mt-3 text-xs ${
          net > 0 ? "text-teal-700" : net < 0 ? "text-orange-700" : "text-slate-500"
        }`}
      >
        net: {net.toFixed(2)} mb/d ({net > 0 ? "exporter" : "importer"})
      </div>
    </section>
  );
}

function ActiveEditsSummary({
  world,
  scenario,
  setScenario,
}: {
  world: World;
  scenario: Scenario;
  setScenario: (s: Scenario) => void;
}) {
  const straitMap = Object.fromEntries(
    world.straits.map((s) => [s.strait_id, s]),
  );
  const countryMap = Object.fromEntries(
    world.countries.map((c) => [c.iso3, c]),
  );
  const hasEdits =
    scenario.closed_straits.length > 0 ||
    Object.keys(scenario.strait_capacity_overrides).length > 0 ||
    Object.keys(scenario.country_production_overrides).length > 0 ||
    Object.keys(scenario.country_consumption_overrides).length > 0;
  if (!hasEdits) return null;

  return (
    <section className="mt-6">
      <SectionHeader title="Active edits" />
      <ul className="mt-2 space-y-1 text-xs">
        {scenario.closed_straits.map((sid) => (
          <li
            key={`closed-${sid}`}
            className="flex items-center justify-between rounded bg-red-50 px-2 py-1 text-red-700"
          >
            <span>{straitMap[sid]?.name ?? sid}: closed</span>
            <button
              onClick={() =>
                setScenario({
                  ...scenario,
                  closed_straits: scenario.closed_straits.filter(
                    (s) => s !== sid,
                  ),
                })
              }
              className="text-red-400 hover:text-red-700"
            >
              ✕
            </button>
          </li>
        ))}
        {Object.entries(scenario.strait_capacity_overrides).map(([sid, v]) => (
          <li
            key={`cap-${sid}`}
            className="flex items-center justify-between rounded bg-sky-50 px-2 py-1 text-sky-800"
          >
            <span>
              {straitMap[sid]?.name ?? sid}: {v.toFixed(1)} mb/d
            </span>
            <button
              onClick={() => {
                const o = { ...scenario.strait_capacity_overrides };
                delete o[sid];
                setScenario({ ...scenario, strait_capacity_overrides: o });
              }}
              className="text-sky-400 hover:text-sky-700"
            >
              ✕
            </button>
          </li>
        ))}
        {Object.entries(scenario.country_production_overrides).map(
          ([iso3, v]) => (
            <li
              key={`prod-${iso3}`}
              className="flex items-center justify-between rounded bg-sky-50 px-2 py-1 text-sky-800"
            >
              <span>
                {countryMap[iso3]?.name ?? iso3} production: {v.toFixed(2)} mb/d
              </span>
              <button
                onClick={() => {
                  const o = { ...scenario.country_production_overrides };
                  delete o[iso3];
                  setScenario({ ...scenario, country_production_overrides: o });
                }}
                className="text-sky-400 hover:text-sky-700"
              >
                ✕
              </button>
            </li>
          ),
        )}
        {Object.entries(scenario.country_consumption_overrides).map(
          ([iso3, v]) => (
            <li
              key={`cons-${iso3}`}
              className="flex items-center justify-between rounded bg-sky-50 px-2 py-1 text-sky-800"
            >
              <span>
                {countryMap[iso3]?.name ?? iso3} consumption: {v.toFixed(2)} mb/d
              </span>
              <button
                onClick={() => {
                  const o = { ...scenario.country_consumption_overrides };
                  delete o[iso3];
                  setScenario({
                    ...scenario,
                    country_consumption_overrides: o,
                  });
                }}
                className="text-sky-400 hover:text-sky-700"
              >
                ✕
              </button>
            </li>
          ),
        )}
      </ul>
    </section>
  );
}
