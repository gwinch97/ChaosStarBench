import json
import os
import sys
from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm

# Configuration
ELASTICSEARCH_HOST = "localhost"
ELASTICSEARCH_PORT = 9200
INDEX_PATTERN = "jaeger-span-*"
BATCH_SIZE = 1_000_000  # Save every 1 million traces to a new file

# Initialize Elasticsearch client
es = Elasticsearch([{'host': ELASTICSEARCH_HOST, 'port': ELASTICSEARCH_PORT, 'scheme': 'http'}])


def export_traces(output_directory):
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Initialize the scroll
    scroll = '2m'
    batch_size = 1000

    # Initialize the query (match all - maybe change to only match the root of the trace?)
    query = {
        "query": {
            "match_all": {}
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

    total = es.count(index=INDEX_PATTERN)['count']
    file_index = 0
    trace_count = 0
    file_path = os.path.join(output_directory, f"jaeger_traces_{file_index}.json")
    file = open(file_path, 'w')
    file.write('[')
    first = True

    print(f"Total traces: {total}")
    with tqdm(total=total, desc="Exporting Traces") as pbar:
        for doc in scroll_gen:
            trace = doc['_source']
            if not first:
                file.write(',\n')
            else:
                first = False
            json.dump(trace, file)
            trace_count += 1
            pbar.update(1)

            # If reached batch size, start a new file
            if trace_count >= BATCH_SIZE:
                file.write(']')
                file.close()
                print(f"Saved {BATCH_SIZE} traces to {file_path}")
                file_index += 1
                trace_count = 0
                first = True
                file_path = os.path.join(output_directory, f"jaeger_traces_{file_index}.json")
                file = open(file_path, 'w')
                file.write('[')

    # Close the last file
    file.write(']')
    file.close()
    print(f"Export completed. Traces saved to {output_directory}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <output_directory>")
        sys.exit(1)

    output_dir = sys.argv[1]
    export_traces(output_dir)
