import { useEffect, useMemo, useRef, useState } from "react";
import { fetchWorld, solveScenario } from "./api";
import WorldMap from "./Map";
import ResultsPanel from "./ResultsPanel";
import ScenarioPanel from "./ScenarioPanel";
import type { Scenario, Solution, World } from "./types";
import { EMPTY_SCENARIO } from "./types";

const SOLVE_DEBOUNCE_MS = 150;

export default function App() {
  const [world, setWorld] = useState<World | null>(null);
  const [scenario, setScenario] = useState<Scenario>(EMPTY_SCENARIO);
  const [solution, setSolution] = useState<Solution | null>(null);
  const [solving, setSolving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedStrait, setSelectedStrait] = useState<string | null>(null);
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const reqSeq = useRef(0);

  useEffect(() => {
    fetchWorld()
      .then(setWorld)
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!world) return;
    const seq = ++reqSeq.current;
    setSolving(true);
    const t = setTimeout(() => {
      solveScenario(scenario)
        .then((s) => {
          if (seq === reqSeq.current) {
            setSolution(s);
            setError(null);
          }
        })
        .catch((e) => {
          if (seq === reqSeq.current) setError(String(e));
        })
        .finally(() => {
          if (seq === reqSeq.current) setSolving(false);
        });
    }, SOLVE_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [scenario, world]);

  const selectedStraitObj = useMemo(
    () => world?.straits.find((s) => s.strait_id === selectedStrait) ?? null,
    [world, selectedStrait],
  );

  const selectedCountryObj = useMemo(
    () => world?.countries.find((c) => c.iso3 === selectedCountry) ?? null,
    [world, selectedCountry],
  );

  if (error && !world) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="max-w-md text-center">
          <div className="mb-2 text-red-400">Failed to reach the API.</div>
          <div className="text-sm text-slate-400">{error}</div>
          <div className="mt-4 text-xs text-slate-500">
            Make sure the backend is running:
            <br />
            <code className="text-slate-300">
              .venv/bin/uvicorn api.main:app --reload --port 8005
            </code>
          </div>
        </div>
      </div>
    );
  }

  if (!world) {
    return (
      <div className="flex h-full items-center justify-center text-slate-400">
        Loading world...
      </div>
    );
  }

  return (
    <div className="grid h-full grid-cols-[340px_1fr_340px]">
      <aside className="flex flex-col overflow-hidden border-r border-slate-800">
        <ScenarioPanel
          world={world}
          scenario={scenario}
          setScenario={setScenario}
          selectedStrait={selectedStraitObj}
          selectedCountry={selectedCountryObj}
          onDeselect={() => {
            setSelectedStrait(null);
            setSelectedCountry(null);
          }}
        />
      </aside>

      <main className="relative">
        <WorldMap
          world={world}
          solution={solution}
          scenario={scenario}
          onSelectStrait={(id) => {
            setSelectedStrait(id);
            setSelectedCountry(null);
          }}
          onSelectCountry={(iso3) => {
            setSelectedCountry(iso3);
            setSelectedStrait(null);
          }}
        />
        {solving && (
          <div className="absolute right-4 top-4 rounded bg-slate-900/80 px-3 py-1 text-xs text-slate-300">
            solving...
          </div>
        )}
      </main>

      <aside className="overflow-hidden border-l border-slate-800">
        <ResultsPanel world={world} solution={solution} />
      </aside>
    </div>
  );
}
