#!/usr/bin/env python3
"""
Convert a raw Prometheus export (cpu_usage.json from scrape_cpu.py) into the FC-ADL dataset
format: cpu_usage.csv (CPU-seconds used per 5 s interval, one column per pod) and
fault_inject.txt (index of the first 5 s sample at or after the fault was applied).

Same steps as the Fig. 2 notebooks (the script that produced the published Social Network CSVs
was not found; this matches them closely but not exactly): cumulative counter per pod -> increments
between scrapes -> fill dropped scrapes (sub_sample_zeros) -> value at each 5 s grid point from
that pod's first sample (align_data). Column names: pod name without the two
Kubernetes hash suffixes; replicated services become <service>-1, -2, ... in name order.

Usage: make_dataset.py RUN_DIR [--duration 7200] [--step 5]
RUN_DIR must contain cpu_usage.json, and fault_time.txt (UNIX time the fault was applied,
written by the run script) to produce fault_inject.txt.
"""
import argparse
import json
import os
from collections import Counter, defaultdict

import numpy as np
import pandas as pd


def sub_sample_zeros(x):
    """Linearly fill runs of zero increments (dropped scrapes); as dsbcorr.sub_sample_zeros."""
    x = x.copy()
    zeros = list(np.where(x == 0)[0][1:])
    i = 0
    while i < len(zeros):
        run = [zeros[i]]
        i += 1
        while i < len(zeros) and zeros[i] == run[-1] + 1:
            run.append(zeros[i])
            i += 1
        if run[-1] + 1 < len(x):
            a, b = x[run[0] - 1], x[run[-1] + 1]
            stepv = (b - a) / (len(run) + 1)
            for k in run:
                x[k] = x[k - 1] + stepv
    return x


def align(values, step, duration):
    """Value of the sample within step/2 of each grid point (grid relative to the series' first
    timestamp), 0 if none; as dsbcorr.align_data."""
    grid = np.arange(0, duration, step)
    rel = values[:, 0] - values[0, 0]
    out = np.zeros(grid.size)
    for k, g in enumerate(grid):
        hit = np.where((rel >= g - step / 2) & (rel <= g + step / 2))[0]
        if len(hit):
            out[k] = values[hit[0], 1]
    return out


def convert(run_dir, duration=7200, step=5):
    res = json.load(open(os.path.join(run_dir, "cpu_usage.json")))["data"]["result"]
    series = {}
    for r in res:
        m = r["metric"]
        pod = m.get("pod")
        if not pod or m.get("id", "") == "/" or m.get("container") == "POD":
            continue
        v = np.array([[float(t), float(x)] for t, x in r["values"]])
        if pod in series:          # several containers in one pod: sum the counters
            n = min(len(series[pod]), len(v))
            series[pod] = series[pod][:n] + np.c_[np.zeros(n), v[:n, 1]]
        else:
            series[pod] = v
    t0 = min(v[0, 0] for v in series.values())
    cols = {}
    for pod in sorted(series):
        v = series[pod].copy()
        inc = np.r_[0, np.diff(v[:, 1])]      # CPU-seconds since the previous scrape
        inc[inc < 0] = 0                      # counter reset (container restart)
        v[:, 1] = sub_sample_zeros(inc)
        cols[pod] = align(v, step, duration)  # CPU-seconds per 5 s sample
    base = {p: "-".join(p.split("-")[:-2]) for p in cols}
    counts = Counter(base.values())
    seen = defaultdict(int)
    names = {}
    for p in sorted(cols):
        b = base[p]
        if counts[b] > 1:
            seen[b] += 1
            names[p] = f"{b}-{seen[b]}"
        else:
            names[p] = b
    df = pd.DataFrame({names[p]: cols[p] for p in cols})
    df.to_csv(os.path.join(run_dir, "cpu_usage.csv"), index=False)
    ft = os.path.join(run_dir, "fault_time.txt")
    if os.path.exists(ft):
        idx = int(np.ceil((float(open(ft).read().strip()) - t0) / step))
        open(os.path.join(run_dir, "fault_inject.txt"), "w").write(str(idx))
    return df, t0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("run_dir")
    p.add_argument("--duration", type=int, default=7200)
    p.add_argument("--step", type=int, default=5)
    a = p.parse_args()
    df, t0 = convert(a.run_dir, a.duration, a.step)
    print(f"{a.run_dir}: {df.shape[1]} pods x {df.shape[0]} samples, first timestamp {t0}")
