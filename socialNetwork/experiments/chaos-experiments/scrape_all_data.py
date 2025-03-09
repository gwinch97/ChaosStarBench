"""This file scrapes the previous hour of data (traces, latencies, utilisation) for experiments"""

import json
import os
import requests
import time

from datetime import datetime
from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm

# GET DEPLOYMENT IP AND PORTS
IP_ADDRESS = "127.0.0.1"
ELASTICSEARCH_PORT = 9200
JAEGER_PORT = 16686
PROM_PORT = 9090

# QUERY SPECIFIC VARIABLES
PROMETHEUS_URL = f"http://{IP_ADDRESS}:{PROM_PORT}/api/v1/query_range"
CPU_UTILISATION_QUERY = 'rate(container_cpu_usage_seconds_total{namespace=~"socialnetwork", pod=~".*service.*"}[1m])'
CPU_THROTTLING_QUERY = 'rate(container_cpu_cfs_throttled_seconds_total{namespace=~"socialnetwork", pod=~".*service.*"}[1m])'
MEMORY_UTILISATION_QUERY = 'sum(container_memory_usage_bytes{namespace=~"socialnetwork", pod=~".*service.*"}) by (pod)'
INSTANCES_QUERY = 'count by (pod) (kube_pod_info{namespace=~"socialnetwork", pod=~".*service.*"})'
IO_WRITES_QUERY = 'sum(rate(container_fs_writes_bytes_total{namespace=~"socialnetwork"}[1m]))'
END_TIME = int(time.time())
START_TIME = END_TIME - 3600
STEP = "10s" # get prom data every 10s interval
INDEX_PATTERN = "jaeger-span-*"

# IMPORTANT FILES
DIRECTORY = f'.results/{datetime.now()}'
os.makedirs(DIRECTORY, exist_ok=True) # create the directory
JAEGER_FILE = f'{DIRECTORY}/jaeger_traces.json'
PROM_CPU_UTILISATION_FILE = f'{DIRECTORY}/prometheus_cpu_utilisation.json'
PROM_CPU_THROTTLING_FILE = f'{DIRECTORY}/prometheus_cpu_throttling.json'
PROM_MEM_UTILISATION_FILE = f'{DIRECTORY}/prometheus_mem_utilisation.json'
PROM_INSTANCE_FILE = f'{DIRECTORY}/prometheus_instance_count.json'
PROM_IO_WRITES_FILE = f'{DIRECTORY}/prometheus_io_writes.json'

def main():
    # GET PROMETHEUS CPU UTILISATION DATA

    params = {
        "query": CPU_UTILISATION_QUERY,
        "start": START_TIME,
        "end": END_TIME,
        "step": STEP,
    }

    try:
        response = requests.get(url=PROMETHEUS_URL, params=params, timeout=10)
        data = response.json()

        with open(PROM_CPU_UTILISATION_FILE, 'w') as file:
            json.dump(data, file, indent=4)
        
        print(f"CPU utilisation values saved to: {PROM_CPU_UTILISATION_FILE}")
    except Exception as e:
        print("Unable to query Prometheus for CPU utilisation")
        print(e)

    # GET PROMETHEUS CPU THROTTLING DATA

    params = {
        "query": CPU_THROTTLING_QUERY,
        "start": START_TIME,
        "end": END_TIME,
        "step": STEP,
    }

    try:
        response = requests.get(url=PROMETHEUS_URL, params=params, timeout=10)
        data = response.json()

        with open(PROM_CPU_THROTTLING_FILE, 'w') as file:
            json.dump(data, file, indent=4)
        
        print(f"CPU throttling values saved to: {PROM_CPU_THROTTLING_FILE}")
    except Exception as e:
        print("Unable to query Prometheus for CPU throttling")
        print(e)

    # GET PROMETHEUS MEM UTILISATION DATA

    params = {
        "query": MEMORY_UTILISATION_QUERY,
        "start": START_TIME,
        "end": END_TIME,
        "step": STEP,
    }

    try:
        response = requests.get(url=PROMETHEUS_URL, params=params, timeout=10)
        data = response.json()

        with open(PROM_MEM_UTILISATION_FILE, 'w') as file:
            json.dump(data, file, indent=4)
        
        print(f"Memory utilisation values saved to: {PROM_MEM_UTILISATION_FILE}")
    except Exception as e:
        print("Unable to query Prometheus for memory utilisation")
        print(e)

    # GET PROMETHEUS INSTANCE COUNT

    params = {
        "query": INSTANCES_QUERY,
        "start": START_TIME,
        "end": END_TIME,
        "step": STEP,
    }

    try:
        response = requests.get(url=PROMETHEUS_URL, params=params, timeout=10)
        data = response.json()

        with open(PROM_INSTANCE_FILE, 'w') as file:
            json.dump(data, file, indent=4)
        
        print(f"Instance values saved to: {PROM_INSTANCE_FILE}")
    except Exception as e:
        print("Unable to query Prometheus for instances")
        print(e)

    # GET PROMETHEUS IO WRITES

    params = {
        "query": IO_WRITES_QUERY,
        "start": START_TIME,
        "end": END_TIME,
        "step": STEP,
    }

    try:
        response = requests.get(url=PROMETHEUS_URL, params=params, timeout=10)
        data = response.json()

        with open(PROM_IO_WRITES_FILE, 'w') as file:
            json.dump(data, file, indent=4)
        
        print(f"Instance values saved to: {PROM_IO_WRITES_FILE}")
    except Exception as e:
        print("Unable to query Prometheus for IO writes")
        print(e)

    # GET JAEGER TRACES
    
    try:
        # Initialize Elasticsearch client
        es = Elasticsearch([{'host': IP_ADDRESS, 'port': ELASTICSEARCH_PORT, 'scheme': 'http'}])
        # Initialize the scroll
        scroll = '2m'
        batch_size = 1000

        epoch_time_1h_ago = int(time.time() - 3600) * 1000

        query = {
            "query": {
                "range": {
                    "startTimeMillis": {
                        "gte": epoch_time_1h_ago
                    }
                }
            }
        }

        scroll_gen = helpers.scan(
            client=es,
            index=INDEX_PATTERN,
            query=query,
            scroll=scroll,
            size=batch_size,
            preserve_order=False
        )

        # Open the output file
        with open(JAEGER_FILE, 'w') as f:
            f.write('[')
            first = True
            total = es.count(index=INDEX_PATTERN)['count']
            with tqdm(total=total, desc="Exporting Traces") as pbar:
                for doc in scroll_gen:
                    trace = doc['_source']
                    # Could process or filter trace before saving
                    if not first:
                        f.write(',\n')
                    else:
                        first = False
                    json.dump(trace, f)
                    pbar.update(1)
            f.write(']')

        print(f"Export completed. Traces saved to {JAEGER_FILE}")
    except Exception as e:
        print("Unable to query Jaeger traces")
        print(e)


if __name__ == "__main__":
    main()