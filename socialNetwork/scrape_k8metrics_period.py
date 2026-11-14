#!/usr/bin/env python3
import os
import sys
import time
import json
import requests
from dateutil import parser as dateparser

def parse_time(t):
    """
    Parse either an ISO8601 timestamp or plain seconds since epoch.
    Returns a float UNIX timestamp.
    """
    try:
        # try parse as float (epoch seconds)
        return float(t)
    except ValueError:
        # parse ISO8601 string
        dt = dateparser.parse(t)
        return dt.timestamp()

def fetch_and_write(query, start_ts, end_ts, step, out_path):
    url = (
        "http://localhost:9090/api/v1/query_range"
        f"?query={query}"
        f"&start={start_ts}"
        f"&end={end_ts}"
        f"&step={step}"
    )
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        print(f"[ERROR] Request failed for query `{query}`: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON response for `{query}`: {e}", file=sys.stderr)
        sys.exit(1)

    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {out_path}")

def main():
    import argparse
    p = argparse.ArgumentParser(
        description="Fetch CPU & memory usage from Prometheus over a fixed interval."
    )
    p.add_argument("start",
                   help="Start time, ISO8601 (e.g. 2025-06-18T12:00:00Z) or epoch seconds")
    p.add_argument("end",
                   help="End time, ISO8601 or epoch seconds")
    p.add_argument("outdir",
                   help="Directory (under ~/projects/deathstar-data/) to write JSON files into")
    p.add_argument("--step", default="15s",
                   help="Query resolution (e.g. '15s', '1m'). Default: 15s")
    args = p.parse_args()

    start_ts = parse_time(args.start)
    end_ts   = parse_time(args.end)

    if end_ts <= start_ts:
        print("[ERROR] End time must be after start time", file=sys.stderr)
        sys.exit(1)

    base_dir = os.path.expanduser(f"~/projects/deathstar-data/{args.outdir}")
    os.makedirs(base_dir, exist_ok=True)

    # filter out cadvisor/prometheus/jaeger/elasticsearch pods
    filt = (
        'namespace="socialnetwork",'
        'pod!~".*cadvisor.*|.*prometheus.*|.*jaeger.*|.*elasticsearch.*"'
    )

    cpu_query = f'container_cpu_usage_seconds_total{{{filt}}}'
    mem_query = f'container_memory_rss{{{filt}}}'

    fetch_and_write(
        cpu_query,
        start_ts,
        end_ts,
        args.step,
        os.path.join(base_dir, "cpu_usage.json")
    )
    fetch_and_write(
        mem_query,
        start_ts,
        end_ts,
        args.step,
        os.path.join(base_dir, "mem_usage.json")
    )

if __name__ == "__main__":
    main()

