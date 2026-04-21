import type { Solution, World } from "./types";

interface Props {
  world: World;
  solution: Solution | null;
}

export default function ResultsPanel({ world, solution }: Props) {
  if (!solution) {
    return (
      <div className="p-4 text-sm text-slate-400">Waiting for solve...</div>
    );
  }

  const countryMap = Object.fromEntries(world.countries.map((c) => [c.iso3, c]));
  const straitMap = Object.fromEntries(world.straits.map((s) => [s.strait_id, s]));

  const statusIsOk = solution.status === "optimal" || solution.status === "optimal_inaccurate";

  const strictCountryPrices = Object.entries(solution.node_prices).filter(
    ([k]) => countryMap[k],
  );
  const topSources = [...strictCountryPrices]
    .sort((a, b) => a[1] - b[1])
    .slice(0, 5);
  const topSinks = [...strictCountryPrices]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  const straitImportanceSorted = Object.entries(solution.strait_importance).sort(
    (a, b) => {
      const av = a[1] === null ? Infinity : a[1];
      const bv = b[1] === null ? Infinity : b[1];
      return bv - av;
    },
  );

  const topFlows = [...solution.flows]
    .filter((f) => f.kind === "strait")
    .sort((a, b) => b.mbd - a.mbd)
    .slice(0, 8);

  return (
    <div className="flex h-full flex-col overflow-y-auto p-4">
      <h2 className="text-lg font-semibold">Market outcome</h2>

      {!statusIsOk && (
        <div className="mt-3 rounded border border-red-800 bg-red-950 p-2 text-xs text-red-200">
          LP status: {solution.status}. The scenario has no feasible shipping
          plan — at least one demand cannot be met given the current capacities.
        </div>
      )}

      <div className="mt-3 grid grid-cols-2 gap-2">
        <Stat label="Total cost" value={`${solution.total_cost.toFixed(1)}`} sub="barrel-days" />
        <Stat label="Supply = Demand" value={`${solution.total_supply.toFixed(1)} mb/d`} sub="balanced" />
      </div>

      <Section title="Top strait flows (mb/d)">
        <table className="w-full text-xs">
          <tbody>
            {topFlows.map((f) => {
              const s = straitMap[f.strait_id ?? ""];
              return (
                <tr key={`${f.source}-${f.target}`} className="border-b border-slate-800">
                  <td className="py-1 text-slate-300">{s?.name ?? f.strait_id}</td>
                  <td className="py-1 text-right font-mono">{f.mbd.toFixed(2)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Section>

      <Section title="Strait importance (Δ cost if closed)">
        <table className="w-full text-xs">
          <tbody>
            {straitImportanceSorted.map(([sid, v]) => {
              const s = straitMap[sid];
              return (
                <tr key={sid} className="border-b border-slate-800">
                  <td className="py-1 text-slate-300">{s?.name ?? sid}</td>
                  <td className="py-1 text-right font-mono">
                    {v === null ? (
                      <span className="text-red-300">infeasible</span>
                    ) : (
                      `+${v.toFixed(2)}`
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Section>

      <Section title="Cheapest sources (node price)">
        <table className="w-full text-xs">
          <tbody>
            {topSources.map(([iso3, p]) => (
              <tr key={iso3} className="border-b border-slate-800">
                <td className="py-1 text-slate-300">
                  {countryMap[iso3]?.name ?? iso3}
                </td>
                <td className="py-1 text-right font-mono">{p.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="Most expensive sinks (node price)">
        <table className="w-full text-xs">
          <tbody>
            {topSinks.map(([iso3, p]) => (
              <tr key={iso3} className="border-b border-slate-800">
                <td className="py-1 text-slate-300">
                  {countryMap[iso3]?.name ?? iso3}
                </td>
                <td className="py-1 text-right font-mono">{p.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded border border-slate-800 bg-slate-900 p-2">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="font-mono text-lg">{value}</div>
      {sub && <div className="text-[10px] text-slate-500">{sub}</div>}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-5">
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
        {title}
      </h3>
      {children}
    </section>
  );
}
