import requests
import json
import sys
import time
import os

def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <time_interval> <filename>")
        sys.exit(1)

    t = sys.argv[1]
    fn = sys.argv[2]
    fn = fn + ".json"
    
    # Check if directory exists
    dir_path = f"/home/gw240/projects/deathstar-data/{sys.argv[2]}"
    print(dir_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    # Convert to seconds
    unit = t[-1]
    if unit not in ['s', 'm', 'h']:
        print("Invalid time unit. Use 's', 'm', or 'h'.")
        sys.exit(1)

    multiplier = {'s': 1, 'm': 60, 'h': 3600}
    sleep_t = int(t[:-1]) * multiplier[unit]

    # Uncomment if you want to include a sleep period
    time.sleep(sleep_t)

    url = f'http://localhost:9090/api/v1/query?query=container_cpu_usage_seconds_total{{namespace="socialnetwork", pod!~".*cadvisor.*|.*prometheus.*|.*jaeger.*"}}[{t}]' # evey 10s sample freq // but it still depends how freq promethus scrape the data
    # url = f'http://localhost:9090/api/v1/query?query=sum(rate(container_cpu_usage_seconds_total{{namespace="socialnetwork", pod!~".*cadvisor.*|.*prometheus.*|.*jaeger.*"}}[{t}])) by (namespace,pod)'


    try:
        r = requests.get(url)
        r.raise_for_status()
        j_obj = r.json()
    except requests.RequestException as e:
        print(f"Error occurred during the request: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        sys.exit(1)

    with open(f"/home/gw240/projects/deathstar-data/{sys.argv[2]}/cpu_usage.json", "w") as f:
        json.dump(j_obj, f)

    url = f'http://localhost:9090/api/v1/query?query=container_memory_rss{{namespace="socialnetwork", pod!~".*cadvisor.*|.*prometheus.*|.*jaeger.*"}}[{t}]' # evey 10s sample freq // but it still depends how freq promethus scrape the data
    # url = f'http://localhost:9090/api/v1/query?query=sum(rate(container_cpu_usage_seconds_total{{namespace="socialnetwork", pod!~".*cadvisor.*|.*prometheus.*|.*jaeger.*"}}[{t}])) by (namespace,pod)'


    try:
        r = requests.get(url)
        r.raise_for_status()
        j_obj = r.json()
    except requests.RequestException as e:
        print(f"Error occurred during the request: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        sys.exit(1)

    with open(f"/home/gw240/projects/deathstar-data/{sys.argv[2]}/mem_usage.json", "w") as f:
        json.dump(j_obj, f)

if __name__ == "__main__":
    main()
