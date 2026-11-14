#!/usr/bin/env python3
"""
Export raw per-pod CPU and memory counters for the last WINDOW from Prometheus, as
socialNetwork/scrape_k8metrics_old.py did for the published datasets (range-vector query of
container_cpu_usage_seconds_total), but for any namespace and output directory.

Usage: scrape_cpu.py <window e.g. 7200s> <out_dir> [--namespace hotelreservation] [--prom URL]
Writes <out_dir>/cpu_usage.json and mem_usage.json.
"""
import argparse
import json
import os

import requests

EXCLUDE = ".*cadvisor.*|.*prometheus.*|.*jaeger.*|.*elasticsearch.*|.*consul.*"


def query(prom, q):
    r = requests.get(f"{prom}/api/v1/query", params={"query": q}, timeout=300)
    r.raise_for_status()
    j = r.json()
    if j.get("status") != "success":
        raise RuntimeError(f"Prometheus error: {j}")
    return j


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("window")
    p.add_argument("out_dir")
    p.add_argument("--namespace", default="hotelreservation")
    p.add_argument("--prom", default="http://localhost:9090")
    a = p.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    sel = f'namespace="{a.namespace}", pod!~"{EXCLUDE}"'
    for metric, fn in (("container_cpu_usage_seconds_total", "cpu_usage.json"),
                       ("container_memory_rss", "mem_usage.json")):
        j = query(a.prom, f"{metric}{{{sel}}}[{a.window}]")
        json.dump(j, open(os.path.join(a.out_dir, fn), "w"))
        print(f"{fn}: {len(j['data']['result'])} series")
