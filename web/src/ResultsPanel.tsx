import type { Solution, World } from "./types";

interface Props {
  world: World;
  solution: Solution | null;
}

export default function ResultsPanel({ world, solution }: Props) {
  if (!solution) {
    return <div className="p-5 text-sm text-slate-400">Waiting for solve…</div>;
  }

  const countryMap = Object.fromEntries(
    world.countries.map((c) => [c.iso3, c]),
  );
  const straitMap = Object.fromEntries(
    world.straits.map((s) => [s.strait_id, s]),
  );

  const statusIsOk =
    solution.status === "optimal" || solution.status === "optimal_inaccurate";

  // Importers = countries where consumption > production
  const importers = world.countries.filter(
    (c) => c.consumption_mbd > c.production_mbd,
  );

  const byDeltaDesc = [...importers]
    .map((c) => ({
      c,
      delta: solution.price_delta_vs_base_usd[c.iso3] ?? 0,
      price: solution.delivered_prices_usd[c.iso3] ?? 0,
    }))
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
    .slice(0, 8);

  const keyImporters = ["CHN", "IND", "JPN", "KOR", "DEU", "NLD", "ITA", "USA"]
    .map((iso3) => ({
      c: countryMap[iso3],
      price: solution.delivered_prices_usd[iso3] ?? 0,
      delta: solution.price_delta_vs_base_usd[iso3] ?? 0,
    }))
    .filter((x) => x.c);

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
    .slice(0, 6);

  const hasGap =
    solution.total_demand_response_mbd > 0.01 ||
    solution.total_shut_in_mbd > 0.01;

  return (
    <div className="flex h-full flex-col overflow-y-auto p-5">
      {!statusIsOk && (
        <div className="mb-3 rounded-md border border-red-200 bg-red-50 p-2.5 text-xs text-red-800">
          <div className="font-semibold">LP status: {solution.status}</div>
          <div className="mt-0.5 text-red-700">
            No feasible shipping plan even with slack — likely a numerical issue.
          </div>
        </div>
      )}

      <BigPrice
        price={solution.global_avg_price_usd}
        delta={solution.global_avg_price_delta_usd}
      />

      {hasGap && (
        <SupplyGap solution={solution} countryMap={countryMap} />
      )}

      <div className="mt-3 grid grid-cols-2 gap-2">
        <Stat
          label="Freight bill"
          value={`$${(solution.total_shipping_usd / 1000).toFixed(1)}M`}
          sub="USD/day"
        />
        <Stat
          label="Volume"
          value={`${(solution.total_supply - solution.total_shut_in_mbd).toFixed(1)}`}
          sub="mb/d delivered"
        />
      </div>

      <Section title="Biggest price movers">
        <div className="mb-1 text-[10px] text-slate-500">
          Importers sorted by |Δ price vs base case|
        </div>
        <PriceTable rows={byDeltaDesc} />
      </Section>

      <Section title="Key importer delivered prices">
        <PriceTable rows={keyImporters} />
      </Section>

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
          Δ freight cost if closed
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
    </div>
  );
}

function SupplyGap({
  solution,
  countryMap,
}: {
  solution: Solution;
  countryMap: Record<string, { name: string }>;
}) {
  const cuts = Object.entries(solution.demand_cut_mbd)
    .filter(([, v]) => v > 0.01)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
  const shutIn = Object.entries(solution.shut_in_supply_mbd)
    .filter(([, v]) => v > 0.01)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-amber-800">
        Quantity response
      </div>
      <div className="mt-1 grid grid-cols-2 gap-3">
        <div>
          <div className="font-mono text-lg font-semibold text-amber-900">
            {solution.total_demand_response_mbd.toFixed(1)}
            <span className="ml-1 text-[10px] font-normal text-amber-700">
              mb/d
            </span>
          </div>
          <div className="text-[10px] text-amber-700">
            demand cut (high prices)
          </div>
          <ul className="mt-1 text-[11px] text-amber-900">
            {cuts.map(([iso3, v]) => (
              <li key={iso3} className="flex justify-between">
                <span className="truncate">
                  {countryMap[iso3]?.name ?? iso3}
                </span>
                <span className="font-mono">{v.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="font-mono text-lg font-semibold text-amber-900">
            {solution.total_shut_in_mbd.toFixed(1)}
            <span className="ml-1 text-[10px] font-normal text-amber-700">
              mb/d
            </span>
          </div>
          <div className="text-[10px] text-amber-700">shut-in supply</div>
          <ul className="mt-1 text-[11px] text-amber-900">
            {shutIn.map(([iso3, v]) => (
              <li key={iso3} className="flex justify-between">
                <span className="truncate">
                  {countryMap[iso3]?.name ?? iso3}
                </span>
                <span className="font-mono">{v.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function BigPrice({ price, delta }: { price: number; delta: number }) {
  const up = delta > 0.01;
  const down = delta < -0.01;
  const color = up ? "text-red-600" : down ? "text-teal-700" : "text-slate-500";
  const arrow = up ? "▲" : down ? "▼" : "•";
  return (
    <div className="rounded-lg border border-sky-200 bg-gradient-to-br from-sky-50 to-white p-3">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-sky-700">
        Global avg delivered price
      </div>
      <div className="mt-1 flex items-end justify-between gap-2">
        <div className="font-mono text-3xl font-semibold tabular-nums text-slate-900">
          ${price.toFixed(2)}
        </div>
        <div className={`font-mono text-sm ${color}`}>
          {arrow} {delta >= 0 ? "+" : ""}
          ${delta.toFixed(2)}
        </div>
      </div>
      <div className="text-[10px] text-slate-500">
        USD/bbl, demand-weighted · vs. base case
      </div>
    </div>
  );
}

interface PriceRow {
  c: { iso3: string; name: string };
  price: number;
  delta: number;
}

function PriceTable({ rows }: { rows: PriceRow[] }) {
  return (
    <DataTable>
      {rows.map((r) => {
        const up = r.delta > 0.01;
        const down = r.delta < -0.01;
        const color = up
          ? "text-red-600"
          : down
            ? "text-teal-700"
            : "text-slate-500";
        return (
          <Row key={r.c.iso3}>
            <span className="truncate">{r.c.name}</span>
            <span className="flex items-baseline gap-2">
              <span className="font-mono text-slate-800">
                ${r.price.toFixed(2)}
              </span>
              <span className={`font-mono text-[10px] ${color}`}>
                {r.delta >= 0 ? "+" : ""}
                {r.delta.toFixed(2)}
              </span>
            </span>
          </Row>
        );
      })}
    </DataTable>
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
      <div className="mt-0.5 font-mono text-lg font-semibold tabular-nums text-slate-900">
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
