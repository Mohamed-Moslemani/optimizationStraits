import type { Scenario, Solution, World } from "./types";

const API_BASE = "http://localhost:8005";

export async function fetchWorld(): Promise<World> {
  const r = await fetch(`${API_BASE}/world`);
  if (!r.ok) throw new Error(`GET /world failed: ${r.status}`);
  return r.json();
}

export async function solveScenario(s: Scenario): Promise<Solution> {
  const r = await fetch(`${API_BASE}/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(s),
  });
  if (!r.ok) throw new Error(`POST /solve failed: ${r.status}`);
  return r.json();
}
