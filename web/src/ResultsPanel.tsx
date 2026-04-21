import type { Solution, World } from "./types";

interface Props {
  world: World;
  solution: Solution | null;
}

export default function ResultsPanel({ world, solution }: Props) {
  if (!solution) {
    return (
      <div className="p-5 text-sm text-slate-400">Waiting for solve…</div>
    );
  }

  const countryMap = Object.fromEntries(
    world.countries.map((c) => [c.iso3, c]),
  );
  const straitMap = Object.fromEntries(
    world.straits.map((s) => [s.strait_id, s]),
  );

  const statusIsOk =
    solution.status === "optimal" || solution.status === "optimal_inaccurate";

  const strictCountryPrices = Object.entries(solution.node_prices).filter(
    ([k]) => countryMap[k],
  );
  const topSources = [...strictCountryPrices]
    .sort((a, b) => a[1] - b[1])
    .slice(0, 5);
  const topSinks = [...strictCountryPrices]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  const straitImportanceSorted = Object.entries(
    solution.strait_importance,
  ).sort((a, b) => {
    const av = a[1] === null ? Infinity : a[1];
    const bv = b[1] === null ? Infinity : b[1];
    return bv - av;
  });

  const topFlows = [...solution.flows]
    .filter((f) => f.kind === "strait")
    .sort((a, b) => b.mbd - a.mbd)
    .slice(0, 8);

  return (
    <div className="flex h-full flex-col overflow-y-auto p-5">
      {!statusIsOk && (
        <div className="mb-3 rounded-md border border-red-200 bg-red-50 p-2.5 text-xs text-red-800">
          <div className="font-semibold">LP status: {solution.status}</div>
          <div className="mt-0.5 text-red-700">
            No feasible shipping plan — at least one demand cannot be met given
            current capacities.
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <Stat
          label="Total cost"
          value={solution.total_cost.toFixed(1)}
          sub="barrel-days"
        />
        <Stat
          label="Supply = demand"
          value={`${solution.total_supply.toFixed(1)}`}
          sub="mb/d"
        />
      </div>

      <Section title="Top strait flows">
        <DataTable>
          {topFlows.map((f) => {
            const s = straitMap[f.strait_id ?? ""];
            return (
              <Row key={`${f.source}-${f.target}`}>
                <span className="truncate">{s?.name ?? f.strait_id}</span>
                <span className="font-mono">{f.mbd.toFixed(2)}</span>
              </Row>
            );
          })}
        </DataTable>
      </Section>

      <Section title="Strait importance">
        <div className="mb-1 text-[10px] text-slate-500">
          Δ shipping cost if the strait closes
        </div>
        <DataTable>
          {straitImportanceSorted.map(([sid, v]) => {
            const s = straitMap[sid];
            return (
              <Row key={sid}>
                <span className="truncate">{s?.name ?? sid}</span>
                <span className="font-mono">
                  {v === null ? (
                    <span className="text-red-600">infeasible</span>
                  ) : (
                    `+${v.toFixed(2)}`
                  )}
                </span>
              </Row>
            );
          })}
        </DataTable>
      </Section>

      <Section title="Cheapest sources">
        <div className="mb-1 text-[10px] text-slate-500">
          Node price (ship-days per mb/d of net supply)
        </div>
        <DataTable>
          {topSources.map(([iso3, p]) => (
            <Row key={iso3}>
              <span className="truncate">
                {countryMap[iso3]?.name ?? iso3}
              </span>
              <span className="font-mono text-teal-700">{p.toFixed(2)}</span>
            </Row>
          ))}
        </DataTable>
      </Section>

      <Section title="Most expensive sinks">
        <DataTable>
          {topSinks.map(([iso3, p]) => (
            <Row key={iso3}>
              <span className="truncate">
                {countryMap[iso3]?.name ?? iso3}
              </span>
              <span className="font-mono text-orange-700">
                {p.toFixed(2)}
              </span>
            </Row>
          ))}
        </DataTable>
      </Section>
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-2.5">
      <div className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div className="mt-0.5 font-mono text-xl font-semibold tabular-nums text-slate-900">
        {value}
      </div>
      {sub && <div className="text-[10px] text-slate-400">{sub}</div>}
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-6">
      <h3 className="border-b border-slate-200 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
        {title}
      </h3>
      <div className="mt-2">{children}</div>
    </section>
  );
}

function DataTable({ children }: { children: React.ReactNode }) {
  return <div className="space-y-0.5 text-xs">{children}</div>;
}

function Row({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2 border-b border-slate-100 py-1 text-slate-700 last:border-b-0">
      {children}
    </div>
  );
}
