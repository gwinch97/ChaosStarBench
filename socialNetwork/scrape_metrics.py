import requests
import json
import sys
import time

t = sys.argv[1]
fn = sys.argv[2]

time.sleep(int(t[:-1]))

r = requests.get(f'http://localhost:17160/api/v1/query?query=container_cpu_system_seconds_total{{name!~"|cadvisor|prometheus"}}[{t}]')
j_obj = json.dumps(r.json())

with open(f"data/{fn}","w") as f:
    f.write(j_obj)
