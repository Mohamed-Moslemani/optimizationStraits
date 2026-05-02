"""Pull bilateral crude oil (HS 2709) trade flows from UN Comtrade.

Uses Comtrade's free public preview endpoint (no auth required, capped at
500 rows per call). For each reporter we filter to the unique annual-
aggregate row per partner (motCode=0 = all transport modes, partner2Code=0
= no second-partner breakdown), then convert volume from CIF USD value
divided by the year's crude reference price (units are consistent across
reporters; raw `qty` field is reported in mixed units across countries).

Run: python scripts/fetch_comtrade.py [year]   (default 2023)
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"

# Reference Brent prices for converting CIF USD value -> barrels.
# Source: EIA spot price annual averages.
BRENT_USD_PER_BBL = {2021: 70.86, 2022: 100.93, 2023: 82.49, 2024: 80.0}

M49_TO_ISO3: dict[int, str] = {
    12: "DZA", 24: "AGO", 124: "CAN", 156: "CHN", 170: "COL",
    208: "DNK", 218: "ECU", 250: "FRA", 276: "DEU", 356: "IND",
    360: "IDN", 364: "IRN", 368: "IRQ", 380: "ITA", 392: "JPN",
    398: "KAZ", 410: "KOR", 414: "KWT", 434: "LBY", 458: "MYS",
    484: "MEX", 528: "NLD", 566: "NGA", 578: "NOR", 616: "POL",
    634: "QAT", 643: "RUS", 682: "SAU", 702: "SGP", 724: "ESP",
    764: "THA", 784: "ARE", 792: "TUR", 818: "EGY", 826: "GBR",
    842: "USA", 862: "VEN", 887: "YEM",
}

MODEL_ISO3: set[str] = set(M49_TO_ISO3.values())


def fetch_imports(reporter_m49: int, year: int) -> list[dict]:
    url = (
        "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
        f"?freq=A&period={year}&clCode=HS&cmdCode=2709&flowCode=M"
        f"&reporterCode={reporter_m49}"
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                payload = json.loads(r.read())
            return payload.get("data", []) or []
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 4 * (attempt + 1)
                print(f"  ! {reporter_m49} 429, waiting {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"  ! {reporter_m49} HTTP {e.code}: {e}", file=sys.stderr)
            return []
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  ! {reporter_m49} {type(e).__name__}: {e}", file=sys.stderr)
            return []
    return []


def main(year: int = 2023, out_path: Path | None = None) -> None:
    out_path = out_path or DATA / "bilateral_flows_2023.csv"
    brent = BRENT_USD_PER_BBL.get(year, 80.0)
    print(f"Using Brent reference: ${brent}/bbl for year {year}")

    iso3_to_m49 = {iso: m49 for m49, iso in M49_TO_ISO3.items()}
    importers = sorted(MODEL_ISO3)

    pairs: dict[tuple[str, str], float] = defaultdict(float)
    for iso3 in importers:
        m49 = iso3_to_m49.get(iso3)
        if not m49:
            continue
        rows = fetch_imports(m49, year)
        kept = 0
        for r in rows:
            # Annual aggregate row only: all transport modes, no partner2 split.
            if r.get("motCode") != 0 or r.get("partner2Code") != 0:
                continue
            pcode = r.get("partnerCode", 0)
            if pcode in (0, None):
                continue
            partner_iso = M49_TO_ISO3.get(pcode)
            if partner_iso is None or partner_iso == iso3:
                continue

            cif = r.get("cifvalue") or 0
            if cif <= 0:
                # Fall back to primaryValue (which is cif for imports, fob for exports)
                cif = r.get("primaryValue") or 0
            if cif <= 0:
                continue

            bbl_per_year = cif / brent
            mbd = bbl_per_year / 365.0 / 1_000_000.0
            if mbd < 0.01:                  # drop trivial
                continue
            pairs[(partner_iso, iso3)] = mbd  # SINGLE row, not summed
            kept += 1

        print(f"  {iso3} (M49 {m49}): {len(rows)} rows from API, {kept} kept")
        time.sleep(1.2)                       # be very polite

    rows_out = [
        {"exporter": exp, "importer": imp, "mbd": round(mbd, 3),
         "source": f"UN_Comtrade_HS2709_{year}"}
        for (exp, imp), mbd in sorted(pairs.items(), key=lambda kv: -kv[1])
    ]
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["exporter", "importer", "mbd", "source"])
        w.writeheader()
        w.writerows(rows_out)
    total = sum(r["mbd"] for r in rows_out)
    print(f"\nWrote {len(rows_out)} pairs to {out_path}")
    print(f"Total seaborne crude in dataset: {total:.1f} mb/d")


if __name__ == "__main__":
    yr = int(sys.argv[1]) if len(sys.argv) > 1 else 2023
    main(year=yr)
