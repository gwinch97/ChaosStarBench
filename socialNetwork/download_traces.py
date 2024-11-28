import json
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm

# Configuration
ELASTICSEARCH_HOST = "localhost"
ELASTICSEARCH_PORT = 9200 
INDEX_PATTERN = "jaeger-span-*"
OUTPUT_FILE = "jaeger_traces.json"

# Initialize Elasticsearch client
es = Elasticsearch([{'host': ELASTICSEARCH_HOST, 'port': ELASTICSEARCH_PORT, 'scheme': 'http'}])

def export_traces():
    # Initialize the scroll
    scroll = '2m'
    batch_size = 1000

    # Get the current time and 15 seconds ago
    now = datetime.now()
    fifteen_seconds_ago = now - timedelta(seconds=1500)

    # Convert to milliseconds (startTimeMillis is in milliseconds)
    now_ms = int(now.timestamp() * 1000)  # Convert to milliseconds
    fifteen_seconds_ago_ms = int(fifteen_seconds_ago.timestamp() * 1000)  # Convert to milliseconds

    # Initialize the query to match traces based on the startTimeMillis field
    query = {
        "_source": ["traceID", "spanID", "operationName", "startTimeMillis", "duration"],  # Adjust based on your fields
        "query": {
            "range": {
                "startTimeMillis": {  # Field storing the timestamp in milliseconds
                    "gte": fifteen_seconds_ago_ms,  # 15 seconds ago in milliseconds
                    "lte": now_ms  # Current time in milliseconds
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
    with open(OUTPUT_FILE, 'w') as f:
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

    print(f"Export completed. Traces saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    export_traces()

