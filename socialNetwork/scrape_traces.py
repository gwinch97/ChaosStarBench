import json
from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm
import sys
import os
import time
import math

# Configuration
ELASTICSEARCH_HOST = "localhost"
ELASTICSEARCH_PORT = 9200
INDEX_PATTERN = "jaeger-span-*"
#OUTPUT_FILE = "/home/gw240/projects/deathstar-data/real_workload_test_1/jaeger_traces.json"
BASE_DIR = "/home/gw240/projects/deathstar-data"

# Initialize Elasticsearch client
es = Elasticsearch([{'host': ELASTICSEARCH_HOST, 'port': ELASTICSEARCH_PORT, 'scheme': 'http'}])

def export_traces(total_hours, chunk_hours, name):
    now_us = int(time.time() * 1e6)
    start_us = now_us - total_hours*3600*1_000_000
    chunks = math.ceil(total_hours / chunk_hours)
    outdir = os.path.join(BASE_DIR, name)
    os.makedirs(outdir, exist_ok=True)

    for i in range(chunks):
        cs = start_us + i*chunk_hours*3600*1_000_000
        ce = min(now_us, cs + chunk_hours*3600*1_000_000)
        filename = f"{outdir}/traces_{i}.json"
        query = {
            "query": {
                "range": {
                    "startTime": { "gte": cs, "lte": ce }
                }
            }
        }
        scroll="5m"  # short scroll lifetime, since each window is small
        scroll_gen = helpers.scan(
            client=es, index=INDEX_PATTERN, query=query,
            scroll=scroll, size=500, preserve_order=False
        )
        with open(filename, 'w') as f:
            f.write('[\n')
            first = True
            for doc in scroll_gen:
                if not first:
                    f.write(',\n')
                first = False
                json.dump(doc['_source'], f)
            f.write('\n]')

if __name__ == "__main__":
    
    total_h   = int(sys.argv[1])
    chunk_h   = int(sys.argv[2])
    run_name  = sys.argv[3]
	
    export_traces(total_h, chunk_h, run_name)
