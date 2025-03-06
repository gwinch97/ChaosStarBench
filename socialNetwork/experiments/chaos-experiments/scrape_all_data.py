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
UTILISATION_QUERY = 'rate(container_cpu_usage_seconds_total{namespace=~"socialnetwork", pod=~".*service.*"}[1m])'
THROTTLING_QUERY = 'rate(container_cpu_cfs_throttled_seconds_total{namespace=~"socialnetwork", pod=~".*service.*"}[1m])'
END_TIME = int(time.time())
START_TIME = END_TIME - 3600
STEP = "10s" # get prom data every 10s interval

# IMPORTANT FILES
DIRECTORY = f'.results/{datetime.now()}'
os.makedirs(DIRECTORY, exist_ok=True) # create the directory
JAEGER_FILE = f'{DIRECTORY}/jaeger_traces.json'
PROM_CPU_USAGE_FILE = f'{DIRECTORY}/prometheus_cpu_usage.json'
PROM_CPU_THROTTLING_FILE = f'{DIRECTORY}/prometheus_cpu_throttling.json'

def main():
    # Initialize Elasticsearch
    es = Elasticsearch([{'host': IP_ADDRESS, 'port': ELASTICSEARCH_PORT, 'scheme': 'http'}])
    index_pattern = "jaeger-span-*"
    scroll = '2m'
    batch_size = 500

    # GET JAEGER TRACE LATENCY
    # Get epoch time 1 hour ago (in milliseconds)
    epoch_time_1h_ago = int(time.time() - 3600) * 1000

    # Initialize the query to match traces based on the startTimeMillis field
    query = {"_source": ["process.serviceName", "duration"],
                "query": {"range": {"startTimeMillis": {"gte": epoch_time_1h_ago}}}}

    try:
        total = es.count(index=index_pattern, body={"query": query['query']})['count']

        if es.count(index=index_pattern, body={"query": query['query']})['count'] != 0:
            scroll_gen = helpers.scan(client=es, index=index_pattern, query=query, scroll=scroll, size=batch_size,
                                        preserve_order=False)
            with open(JAEGER_FILE, 'w') as f:
                f.write('[')
                first = True
                with tqdm(total=total, desc="Exporting Traces") as pbar:
                    for doc in scroll_gen:
                        trace = doc['_source']
                        if not first:
                            f.write(',\n')
                        else:
                            first = False
                        json.dump(trace, f)
                        pbar.update(1)
                f.write(']')

            print('--------------------')
            print(f"Traces saved to: {JAEGER_FILE}")
            print('--------------------')
        else:
            print("No traces found!")
    except Exception as e:
        print("Unable to query Jaeger response time")
        print(e)
    
    # GET PROMETHEUS DATA

    params = {
        "query": UTILISATION_QUERY,
        "start": START_TIME,
        "end": END_TIME,
        "step": STEP,
    }

    try:
        response = requests.get(url=PROMETHEUS_URL, params=params, timeout=10)
        data = response.json()

        with open(PROM_CPU_USAGE_FILE, 'w') as file:
            json.dump(data, file, indent=4)
        
        print('--------------------')
        print(f"CPU utilisation values saved to: {PROM_CPU_USAGE_FILE}")
        print('--------------------')
    except Exception as e:
        print("Unable to query Prometheus CPU utilisation")
        print(e)

    params = {
        "query": THROTTLING_QUERY,
        "start": START_TIME,
        "end": END_TIME,
        "step": STEP,
    }

    try:
        response = requests.get(url=PROMETHEUS_URL, params=params, timeout=10)
        data = response.json()

        with open(PROM_CPU_THROTTLING_FILE, 'w') as file:
            json.dump(data, file, indent=4)
        
        print('--------------------')
        print(f"CPU throttling values saved to: {PROM_CPU_THROTTLING_FILE}")
        print('--------------------')
    except Exception as e:
        print("Unable to query Prometheus CPU throttling")
        print(e)


if __name__ == "__main__":
    main()