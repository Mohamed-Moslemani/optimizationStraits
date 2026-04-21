import type { Country, Scenario, Strait, World } from "./types";
import { EMPTY_SCENARIO } from "./types";
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
    <div className="flex h-full flex-col overflow-y-auto p-4">
      <h1 className="text-lg font-semibold">Oil market scenario</h1>
      <p className="mt-1 text-xs text-slate-400">
        Click a strait or country on the map to edit it. The model re-solves
        live.
      </p>

      <section className="mt-5">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Preset scenarios
          </h2>
          <button
            onClick={() => setScenario({ ...EMPTY_SCENARIO })}
            className="text-xs text-slate-400 hover:text-slate-200"
          >
            reset
          </button>
        </div>
        <div className="flex flex-col gap-1.5">
          {PRESETS.map((p) => (
            <button
              key={p.id}
              onClick={() => setScenario(p.build())}
              className="rounded border border-slate-800 bg-slate-900 px-3 py-2 text-left text-sm hover:border-slate-600 hover:bg-slate-800"
              title={p.description}
            >
              {p.label}
            </button>
          ))}
        </div>
      </section>

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

      <ActiveEditsSummary world={world} scenario={scenario} setScenario={setScenario} />
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
    if (Math.abs(v - strait.capacity_mbd) < 0.01) delete overrides[strait.strait_id];
    else overrides[strait.strait_id] = v;
    setScenario({
      ...scenario,
      strait_capacity_overrides: overrides,
      closed_straits: scenario.closed_straits.filter((s) => s !== strait.strait_id),
    });
  };

  const toggleClose = () => {
    if (isClosed) {
      setScenario({
        ...scenario,
        closed_straits: scenario.closed_straits.filter((s) => s !== strait.strait_id),
      });
    } else {
      setScenario({
        ...scenario,
        closed_straits: [...scenario.closed_straits, strait.strait_id],
      });
    }
  };

  return (
    <section className="mt-6 rounded border border-slate-700 bg-slate-900 p-3">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">{strait.name}</h3>
          <div className="text-xs text-slate-400">
            {strait.kind} · {strait.transit_days.toFixed(1)} days
          </div>
        </div>
        <button onClick={onClose} className="text-xs text-slate-500 hover:text-slate-300">
          close
        </button>
      </div>
      <label className="block text-xs text-slate-400">
        Capacity: {isClosed ? "closed" : `${current.toFixed(1)} mb/d`}
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
      <div className="mt-2 flex gap-2">
        <button
          onClick={toggleClose}
          className={`rounded px-2 py-1 text-xs ${
            isClosed
              ? "bg-red-900 text-red-200 hover:bg-red-800"
              : "bg-slate-800 text-slate-300 hover:bg-slate-700"
          }`}
        >
          {isClosed ? "reopen" : "close strait"}
        </button>
        {override !== undefined && (
          <button
            onClick={() => setCap(strait.capacity_mbd)}
            className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700"
          >
            reset capacity
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
    scenario.country_production_overrides[country.iso3] ?? country.production_mbd;
  const cons =
    scenario.country_consumption_overrides[country.iso3] ?? country.consumption_mbd;

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

  return (
    <section className="mt-6 rounded border border-slate-700 bg-slate-900 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold">
          {country.name} ({country.iso3})
        </h3>
        <button onClick={onClose} className="text-xs text-slate-500 hover:text-slate-300">
          close
        </button>
      </div>
      <label className="block text-xs text-slate-400">
        Production: {prod.toFixed(2)} mb/d
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
      <label className="mt-2 block text-xs text-slate-400">
        Consumption: {cons.toFixed(2)} mb/d
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
      <div className="mt-2 text-xs text-slate-400">
        net: {(prod - cons).toFixed(2)} mb/d ({prod > cons ? "exporter" : "importer"})
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
  const straitMap = Object.fromEntries(world.straits.map((s) => [s.strait_id, s]));
  const countryMap = Object.fromEntries(world.countries.map((c) => [c.iso3, c]));
  const hasEdits =
    scenario.closed_straits.length > 0 ||
    Object.keys(scenario.strait_capacity_overrides).length > 0 ||
    Object.keys(scenario.country_production_overrides).length > 0 ||
    Object.keys(scenario.country_consumption_overrides).length > 0;
  if (!hasEdits) return null;

  return (
    <section className="mt-6">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
        Active edits
      </h2>
      <ul className="space-y-1 text-xs">
        {scenario.closed_straits.map((sid) => (
          <li key={`closed-${sid}`} className="flex items-center justify-between">
            <span className="text-red-300">{straitMap[sid]?.name ?? sid}: closed</span>
            <button
              onClick={() =>
                setScenario({
                  ...scenario,
                  closed_straits: scenario.closed_straits.filter((s) => s !== sid),
                })
              }
              className="text-slate-500 hover:text-slate-300"
            >
              ✕
            </button>
          </li>
        ))}
        {Object.entries(scenario.strait_capacity_overrides).map(([sid, v]) => (
          <li key={`cap-${sid}`} className="flex items-center justify-between">
            <span>
              {straitMap[sid]?.name ?? sid}: {v.toFixed(1)} mb/d
            </span>
            <button
              onClick={() => {
                const o = { ...scenario.strait_capacity_overrides };
                delete o[sid];
                setScenario({ ...scenario, strait_capacity_overrides: o });
              }}
              className="text-slate-500 hover:text-slate-300"
            >
              ✕
            </button>
          </li>
        ))}
        {Object.entries(scenario.country_production_overrides).map(([iso3, v]) => (
          <li key={`prod-${iso3}`} className="flex items-center justify-between">
            <span>
              {countryMap[iso3]?.name ?? iso3} production: {v.toFixed(2)} mb/d
            </span>
            <button
              onClick={() => {
                const o = { ...scenario.country_production_overrides };
                delete o[iso3];
                setScenario({ ...scenario, country_production_overrides: o });
              }}
              className="text-slate-500 hover:text-slate-300"
            >
              ✕
            </button>
          </li>
        ))}
        {Object.entries(scenario.country_consumption_overrides).map(([iso3, v]) => (
          <li key={`cons-${iso3}`} className="flex items-center justify-between">
            <span>
              {countryMap[iso3]?.name ?? iso3} consumption: {v.toFixed(2)} mb/d
            </span>
            <button
              onClick={() => {
                const o = { ...scenario.country_consumption_overrides };
                delete o[iso3];
                setScenario({ ...scenario, country_consumption_overrides: o });
              }}
              className="text-slate-500 hover:text-slate-300"
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
