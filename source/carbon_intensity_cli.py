#!/usr/bin/env python3

"""
Carbon Intensity API – Command Line Interface

Usage examples:

  # Current national intensity
  python carbon_intensity_cli.py intensity current

  # Intensity for a range
  python carbon_intensity_cli.py intensity range --start "2025-08-08T12:00Z" --end "2025-08-08T18:00Z"

  # Intensity on a calendar date (UTC)
  python carbon_intensity_cli.py intensity date --date 2025-08-08

  # Forward 48h forecast from now (UTC)
  python carbon_intensity_cli.py intensity forecast

  # Stats over a period, grouped by day
  python carbon_intensity_cli.py intensity stats --start 2025-08-01 --end 2025-08-08 --group-by day

  # Emissions factors
  python carbon_intensity_cli.py intensity factors

  # Current generation mix
  python carbon_intensity_cli.py generation current

  # Generation mix for a range
  python carbon_intensity_cli.py generation range --start 2025-08-08T12:00Z --end 2025-08-08T18:00Z

  # Regional snapshot (all regions)
  python carbon_intensity_cli.py regional snapshot

  # Regional snapshot for a specific region id
  python carbon_intensity_cli.py regional snapshot --region-id 13

  # Regional intensity range for all regions
  python carbon_intensity_cli.py regional range --start 2025-08-08 --end 2025-08-09

  # Regional intensity range for a specific region id
  python carbon_intensity_cli.py regional range --start 2025-08-08 --end 2025-08-09 --region-id 13


"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from typing import Any, Dict, Iterable, List, Optional

import carbon_intensity_api_functions as ci


############################################################
# Utilities
############################################################

def _parse_dateish(s: str) -> str:
    """Return the input string unchanged, but validate it's plausibly ISO-like.
    The library can accept strings directly and will normalize.
    We keep this intentionally permissive.
    """
    if not isinstance(s, str) or not s:
        raise argparse.ArgumentTypeError("expected a non-empty string for date/time")
    return s


def _parse_group_by(s: str) -> str:
    s = s.strip().lower()
    if s not in {"day", "month", "year"}:
        raise argparse.ArgumentTypeError("group-by must be one of: day, month, year")
    return s


def _json_dump(data: Any, pretty: bool) -> str:
    if pretty:
        return json.dumps(data, indent=2, ensure_ascii=False)
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def _flatten_for_csv(rows: Any) -> List[Dict[str, Any]]:
    """Best-effort flattener for common Carbon Intensity list payloads.
    Handles typical shapes for intensity, forecast, generation mix, and regional time series.
    Unknown shapes are passed through if already list[dict].
    """
    flat: List[Dict[str, Any]] = []
    if isinstance(rows, list):
        for r in rows:
            if not isinstance(r, dict):
                flat.append({"value": r})
                continue
            d: Dict[str, Any] = {}
            # Common top-level keys
            for k in ("from", "to", "intensity", "generationmix", "regionid", "shortname", "dnoregion", "forecast", "actual", "index"):
                if k in r and not isinstance(r[k], (list, dict)):
                    d[k] = r[k]
            # Intensity object
            if isinstance(r.get("intensity"), dict):
                for ik, iv in r["intensity"].items():
                    d[f"intensity_{ik}"] = iv
            # Generation mix list
            if isinstance(r.get("generationmix"), list):
                # spread by fuel name -> %
                for gm in r["generationmix"]:
                    fuel = gm.get("fuel")
                    perc = gm.get("perc")
                    if fuel is not None:
                        d[f"mix_{fuel}"] = perc
            # Regional sub-objects
            if isinstance(r.get("region"), dict):
                region = r["region"]
                d["region_id"] = region.get("regionid")
                d["region_name"] = region.get("shortname") or region.get("dnoregion")
            flat.append(d)
    return flat


def _write_csv(path: str, rows: Any) -> None:
    import csv
    flat = _flatten_for_csv(rows)
    if not flat:
        # Write an empty CSV with no headers
        with open(path, "w", newline="", encoding="utf-8") as f:
            pass
        return
    headers: List[str] = sorted({k for row in flat for k in row.keys()})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for row in flat:
            w.writerow(row)

############################################################
# Command implementations
############################################################

def cmd_intensity(args: argparse.Namespace) -> Any:
    if args.which == "current":
        return ci.get_current_intensity()
    if args.which == "range":
        return ci.get_intensity_range(args.start, args.end)
    if args.which == "date":
        return ci.get_intensity_on_date(args.date)
    if args.which == "forecast":
        return ci.get_forecast_fw48h(args.start)
    if args.which == "stats":
        return ci.get_intensity_stats(args.start, args.end, group_by=args.group_by)
    if args.which == "factors":
        return ci.get_factors()
    raise AssertionError("unknown intensity subcommand")


def cmd_generation(args: argparse.Namespace) -> Any:
    if args.which == "current":
        return ci.get_generation_mix_current()
    if args.which == "range":
        return ci.get_generation_mix_range(args.start, args.end)
    raise AssertionError("unknown generation subcommand")


def cmd_regional(args: argparse.Namespace) -> Any:
    if args.which == "snapshot":
        if args.region_id is None:
            return ci.get_regional_snapshot()
        return ci.get_regional_snapshot_by_id(args.region_id)
    if args.which == "range":
        return ci.get_regional_intensity_range(args.start, args.end, region_id=args.region_id)
    raise AssertionError("unknown regional subcommand")

############################################################
# Argument parser
############################################################

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="carbon-intensity", description="CLI for the UK Carbon Intensity API")
    p.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    p.add_argument("--csv", metavar="PATH", help="optional CSV output path for time-series endpoints")

    sub = p.add_subparsers(dest="cmd", required=True)

    # intensity
    pi = sub.add_parser("intensity", help="national intensity endpoints")
    si = pi.add_subparsers(dest="which", required=True)

    si.add_parser("current", help="current national intensity")

    pir = si.add_parser("range", help="intensity for a time range [start,end]")
    pir.add_argument("--start", type=_parse_dateish, required=True)
    pir.add_argument("--end", type=_parse_dateish, required=True)

    pid = si.add_parser("date", help="intensity for a calendar date (UTC)")
    pid.add_argument("--date", type=_parse_dateish, required=True)

    pif = si.add_parser("forecast", help="forward 48h forecast from start (or now)")
    pif.add_argument("--start", type=_parse_dateish)

    pis = si.add_parser("stats", help="summary stats for a period")
    pis.add_argument("--start", type=_parse_dateish, required=True)
    pis.add_argument("--end", type=_parse_dateish, required=True)
    pis.add_argument("--group-by", type=_parse_group_by, help="day | month | year")

    si.add_parser("factors", help="emissions factors (gCO2/kWh) by fuel")

    # generation
    pg = sub.add_parser("generation", help="generation mix endpoints")
    sg = pg.add_subparsers(dest="which", required=True)

    sg.add_parser("current", help="current generation mix")

    pgr = sg.add_parser("range", help="generation mix for a time range")
    pgr.add_argument("--start", type=_parse_dateish, required=True)
    pgr.add_argument("--end", type=_parse_dateish, required=True)

    # regional
    pr = sub.add_parser("regional", help="regional endpoints")
    sr = pr.add_subparsers(dest="which", required=True)

    prs = sr.add_parser("snapshot", help="current snapshot for all regions or a single region")
    prs.add_argument("--region-id", help="optional region id (e.g., 13)")

    prr = sr.add_parser("range", help="regional intensity time series for a range")
    prr.add_argument("--start", type=_parse_dateish, required=True)
    prr.add_argument("--end", type=_parse_dateish, required=True)
    prr.add_argument("--region-id", help="optional region id (e.g., 13)")

    return p


############################################################
# Main
############################################################

def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.cmd == "intensity":
            data = cmd_intensity(args)
        elif args.cmd == "generation":
            data = cmd_generation(args)
        elif args.cmd == "regional":
            data = cmd_regional(args)
        else:
            parser.error("unknown command")
            return 2
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    # Optionally write CSV for series-like outputs
    if args.csv:
        try:
            _write_csv(args.csv, data)
        except Exception as e:  # pragma: no cover
            print(f"Failed to write CSV: {e}", file=sys.stderr)
            return 1

    # Always print JSON to stdout
    print(_json_dump(data, pretty=args.pretty))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
