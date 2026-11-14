import sys, time, requests, os
import pandas as pd
import math
from tqdm import trange

import sys, time, requests, os, math
import pandas as pd

BASE_DIR = "/home/gw240/projects/deathstar-data"

# your queries & step size, up here so chunked_main can see them
cpu_q = (
    'rate(container_cpu_usage_seconds_total{'
    'namespace="socialnetwork", pod!~".*cadvisor.*|.*prometheus.*|.*jaeger.*|.*elasticsearch.*"}'
    '[15s])'
)
mem_q = (
    'container_memory_rss{'
    'namespace="socialnetwork", pod!~".*cadvisor.*|.*prometheus.*|.*jaeger.*"}'
)
step = "5s"

def fetch(query, start, end, step):
    resp = requests.get("http://localhost:9090/api/v1/query_range", params={
        "query": query, "start": start, "end": end, "step": step
    })
    resp.raise_for_status()
    return resp.json()["data"]["result"]

def to_df(series, value_key):
    rows = []
    for s in series:
        pod = s["metric"].get("pod", s["metric"].get("instance", "unknown"))
        for ts, val in s["values"]:
            rows.append((pd.to_datetime(float(ts), unit='s'), pod, float(val)))
    df = pd.DataFrame(rows, columns=["time","pod",value_key])
    return df.pivot(index="time", columns="pod", values=value_key)

def chunked_main(total_hours, chunk_hours, name):
    now = int(time.time())
    start = now - total_hours * 3600
    chunks = math.ceil(total_hours / chunk_hours)
    outdir = os.path.join(BASE_DIR, name)
    os.makedirs(outdir, exist_ok=True)

    all_cpu, all_mem = [], []
    for i in trange(chunks):
        chunk_start = start + i * chunk_hours * 3600
        chunk_end   = min(now, chunk_start + chunk_hours * 3600)

        cpu = fetch(cpu_q, chunk_start, chunk_end, step)
        mem = fetch(mem_q, chunk_start, chunk_end, step)

        cpu_df = to_df(cpu, "cpu_rate")
        mem_df = to_df(mem, "mem_rss")

        # append to lists for a final full-file export
        all_cpu.append(cpu_df)
        all_mem.append(mem_df)

        # write each chunk out immediately
        cpu_df.to_csv(f"{outdir}/cpu_{i}.csv")
        mem_df.to_csv(f"{outdir}/mem_{i}.csv")

    # optional: stitch chunks into a single file
    pd.concat(all_cpu).sort_index().to_csv(f"{outdir}/cpu_full.csv")
    pd.concat(all_mem).sort_index().to_csv(f"{outdir}/mem_full.csv")

if __name__ == "__main__":
    if len(sys.argv)!=4:
        print("Usage: scrape_range.py <interval[s|m|h]> <window> <output_name>"); sys.exit(1)
    
    #chunked_main(sys.argv[1], sys.argv[2], sys.argv[3])
	
    total_h   = int(sys.argv[1])
    chunk_h   = int(sys.argv[2])
    run_name  = sys.argv[3]

    chunked_main(total_h, chunk_h, run_name)
	
