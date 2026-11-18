"""Turn the challenge's four big JSON files into one drop per route date.

The source is a single snapshot covering ~2 months. The real system I'm modelling
gets a drop every day, so this replays history as daily folders:

    data/drops/dt=2018-07-27/routes.jsonl
                             packages.jsonl
                             sequences.jsonl
                             travel_times.jsonl

Two things about the source worth knowing:
  * it contains bare NaN tokens (package time windows), which isn't valid JSON
  * travel_times.json is 1.8 GB, so it's streamed with ijson instead of json.load
"""
import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

import ijson

log = logging.getLogger(__name__)


class NaNToNull:
    """File wrapper that rewrites the bare NaN token to null while streaming."""

    def __init__(self, f):
        self.f = f
        self.tail = b""

    def read(self, n=-1):
        if n == 0:  # ijson calls read(0) to check the stream type
            return b""
        while True:
            chunk = self.f.read(n)
            if not chunk:
                out, self.tail = self.tail, b""
                return out
            data = (self.tail + chunk).replace(b"NaN", b"null")
            # a read can end in the middle of a NaN, so hold back a trailing "N" or "Na"
            # (replace first, otherwise a complete NaN at the end gets split by us)
            cut = len(data) - (2 if data.endswith(b"Na") else 1 if data.endswith(b"N") else 0)
            out, self.tail = data[:cut], data[cut:]
            if out:  # an empty return would look like EOF to ijson
                return out

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.f.close()


def open_source(path: Path):
    return NaNToNull(open(path, "rb"))


def load_route_dates(path: Path) -> dict[str, str]:
    dates = {}
    with open_source(path) as f:
        for route_id, route in ijson.kvitems(f, "", use_float=True):
            dates[route_id] = route["date_YYYY_MM_DD"]
    return dates


class DropWriter:
    """Keeps one open file per (date, table) so we write in a single pass."""

    def __init__(self, out_dir: Path, table: str):
        self.out_dir = out_dir
        self.table = table
        self.handles = {}
        self.counts = defaultdict(int)

    def write(self, dt: str, record: dict):
        fh = self.handles.get(dt)
        if fh is None:
            folder = self.out_dir / f"dt={dt}"
            folder.mkdir(parents=True, exist_ok=True)
            fh = self.handles[dt] = open(folder / f"{self.table}.jsonl", "w")
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")
        self.counts[dt] += 1

    def close(self):
        for fh in self.handles.values():
            fh.close()


def split_routes(src: Path, out: Path, keep: set[str]):
    w = DropWriter(out, "routes")
    with open_source(src) as f:
        for route_id, r in ijson.kvitems(f, "", use_float=True):
            if route_id not in keep:
                continue
            stops = [{"stop_id": sid, **s} for sid, s in r.pop("stops").items()]
            w.write(r["date_YYYY_MM_DD"], {"route_id": route_id, **r, "stops": stops})
    w.close()
    return w.counts


def split_packages(src: Path, out: Path, dates: dict[str, str]):
    w = DropWriter(out, "packages")
    with open_source(src) as f:
        for route_id, stops in ijson.kvitems(f, "", use_float=True):
            dt = dates.get(route_id)
            if dt is None:
                continue
            for stop_id, pkgs in stops.items():
                for package_id, p in pkgs.items():
                    tw = p.get("time_window") or {}
                    dims = p.get("dimensions") or {}
                    w.write(dt, {
                        "route_id": route_id,
                        "stop_id": stop_id,
                        "package_id": package_id,
                        "scan_status": p.get("scan_status"),
                        "tw_start_utc": tw.get("start_time_utc"),
                        "tw_end_utc": tw.get("end_time_utc"),
                        "planned_service_time_seconds": p.get("planned_service_time_seconds"),
                        "depth_cm": dims.get("depth_cm"),
                        "height_cm": dims.get("height_cm"),
                        "width_cm": dims.get("width_cm"),
                    })
    w.close()
    return w.counts


def split_sequences(src: Path, out: Path, dates: dict[str, str]):
    w = DropWriter(out, "sequences")
    with open_source(src) as f:
        for route_id, body in ijson.kvitems(f, "", use_float=True):
            dt = dates.get(route_id)
            if dt is None:
                continue
            for stop_id, seq in body["actual"].items():
                w.write(dt, {"route_id": route_id, "stop_id": stop_id, "seq": int(seq)})
    w.close()
    return w.counts


def split_travel_times(src: Path, out: Path, dates: dict[str, str]):
    w = DropWriter(out, "travel_times")
    with open_source(src) as f:
        for route_id, matrix in ijson.kvitems(f, "", use_float=True):
            dt = dates.get(route_id)
            if dt is None:
                continue
            w.write(dt, {"route_id": route_id, "matrix": matrix})
    w.close()
    return w.counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="data/source")
    ap.add_argument("--out", default="data/drops")
    ap.add_argument("--start", help="first route date to keep, YYYY-MM-DD")
    ap.add_argument("--end", help="last route date to keep, YYYY-MM-DD")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    src, out = Path(args.source), Path(args.out)
    dates = load_route_dates(src / "route_data.json")
    if args.start:
        dates = {k: v for k, v in dates.items() if v >= args.start}
    if args.end:
        dates = {k: v for k, v in dates.items() if v <= args.end}
    log.info("%d routes across %d days", len(dates), len(set(dates.values())))

    split_routes(src / "route_data.json", out, set(dates))
    split_sequences(src / "actual_sequences.json", out, dates)
    split_packages(src / "package_data.json", out, dates)
    split_travel_times(src / "travel_times.json", out, dates)
    log.info("drops written to %s", out)


if __name__ == "__main__":
    main()
